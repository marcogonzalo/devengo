import calendar
from fastapi.logger import logger
from datetime import date, timedelta
from typing import List, Tuple, TYPE_CHECKING
from sqlalchemy.orm import Session, joinedload
from sqlmodel import func, or_, and_
from src.api.common.constants.services import ServiceContractStatus, ServicePeriodStatus
from src.api.accruals.models.accrued_period import AccruedPeriod
from src.api.accruals.schemas import (
    AccruedPeriodCreate,
    ContractProcessingResult,
    ProcessingStatus
)

# Use TYPE_CHECKING for type hints to avoid runtime import if ServicePeriod is complex
if TYPE_CHECKING:
    from src.api.services.models import ServicePeriod


def get_month_range(year: int, month: int) -> Tuple[date, date]:
    """Returns the first and last day of a given month and year."""
    _, last_day = calendar.monthrange(year, month)
    first_day_date = date(year, month, 1)
    last_day_date = date(year, month, last_day)
    return first_day_date, last_day_date


class PeriodProcessor:
    def __init__(self, db: Session):
        self.db = db

    def get_service_periods_for_month(self, target_month_start: date) -> List["ServicePeriod"]:
        """Get all service periods active or changing status within the given month."""
        from src.api.services.models import ServicePeriod

        month_start, month_end = get_month_range(
            target_month_start.year, target_month_start.month)

        return (
            self.db.query(ServicePeriod)
            .options(joinedload(ServicePeriod.contract))  # Eager load contract
            .filter(
                # Period overlaps with the month
                (ServicePeriod.start_date <= month_end) &
                (ServicePeriod.end_date >= month_start)
            )
            # Consider only active or paused periods, or periods ending this month
            .filter(or_(
                ServicePeriod.status == ServicePeriodStatus.ACTIVE,
                #  Postponed or Dropped periods must be accrued (partially or entirely) if they happen in the current accrual period
                and_(ServicePeriod.status.in_(
                    [
                        ServicePeriodStatus.POSTPONED,
                        ServicePeriodStatus.DROPPED
                    ]
                ),
                    (ServicePeriod.status_change_date.is_(None) |
                     ((ServicePeriod.status_change_date >= month_start) &
                      (ServicePeriod.status_change_date <= month_end)))
                )))
            .all()
        )

    def calculate_accrual_for_period(
        self,
        service_period: "ServicePeriod",
        target_month_start: date
    ) -> Tuple[float, float, int]:
        """
        Calculate accrual amount, portion, and sessions for a service period within a target month.
        Returns (accrued_amount, accrual_portion, sessions_in_month_overlap)
        """
        default_return_value = (0.0, 0.0, 0)
        month_start, month_end = get_month_range(
            target_month_start.year, target_month_start.month)
        contract = service_period.contract
        # Determine the overlap of the service period with the target month
        overlap_start = max(service_period.start_date, month_start)
        overlap_end = min(service_period.end_date, month_end)
        effective_end_date = overlap_end

        # If period is DROPPED, remaining accrual is completed at drop date
        if service_period.status == ServicePeriodStatus.DROPPED:
            if not service_period.status_change_date:
                return default_return_value

            if month_start <= service_period.status_change_date <= month_end:
                effective_end_date = service_period.end_date
                # Get total accrued for the *contract* so far
                total_accrued_result = self.db.query(func.sum(AccruedPeriod.accrued_amount)) \
                    .filter(AccruedPeriod.contract_id == contract.id) \
                    .scalar()
                total_accrued = total_accrued_result or 0.0

                # Accrue the remaining contract amount in this period
                remaining_amount = contract.contract_amount - total_accrued
                if remaining_amount > accrued_amount:  # Avoid double counting if calculated accrual is part of remaining
                    # Recalculate portion based on remaining amount
                    new_remaining = remaining_amount - accrued_amount
                    accrued_amount += new_remaining
                    if contract.contract_amount > 0:
                        accrual_portion = accrued_amount / contract.contract_amount
                    else:
                        accrual_portion = 0.0
                return accrued_amount, accrual_portion, sessions_in_month_overlap
            elif service_period.status_change_date < month_start:
                # Dropped before this month
                return default_return_value

        # If the period is POSTPONED, accrual stops at the beginning of the postponement
        if service_period.status == ServicePeriodStatus.POSTPONED:
            if not service_period.status_change_date:
                return default_return_value

            if service_period.status_change_date and month_start <= service_period.status_change_date <= month_end:
                effective_end_date = min(
                    overlap_end, service_period.status_change_date - timedelta(days=1))
            elif service_period.status_change_date and service_period.status_change_date < month_start:
                # Postponed before this month started
                return default_return_value

        # Ensure start is not after end
        if overlap_start > effective_end_date:
            return default_return_value

        # Calculate sessions for the overlapping period
        sessions_in_month_overlap = service_period.get_sessions_between(
            overlap_start, effective_end_date)
        if sessions_in_month_overlap <= 0:
            return default_return_value

        total_contract_sessions = contract.service.total_sessions
        if total_contract_sessions <= 0:
            return 0.0, 0.0, sessions_in_month_overlap  # Avoid division by zero

        accrual_portion = sessions_in_month_overlap / total_contract_sessions
        accrued_amount = contract.contract_amount * accrual_portion

        return accrued_amount, accrual_portion, sessions_in_month_overlap

    def process_service_period(
        self,
        service_period: "ServicePeriod",
        target_month_start: date
    ) -> ContractProcessingResult:
        """Process a single service period for the given target month."""
        contract = service_period.contract
        result_args = {
            "contract_id": contract.id,
            "service_period_id": service_period.id
        }
        try:
            # Calculate standard accrual for the overlapping period/month
            accrued_amount, accrual_portion, sessions_in_month = self.calculate_accrual_for_period(
                service_period, target_month_start
            )

            # Special handling if period was DROPPED this month
            if service_period.status == ServicePeriodStatus.DROPPED and contract.status == ServiceContractStatus.ACTIVE:
                try:
                    # Change the status of the contract to CANCELED
                    contract.status = ServiceContractStatus.CANCELED
                except Exception as e:
                    logger.error(
                        f"Error changing contract status to CANCELED: {e}")

            # Only create a record if there's something to accrue
            if accrued_amount <= 0:
                return ContractProcessingResult(
                    **result_args,
                    status=ProcessingStatus.SUCCESS,
                    message="No accrual needed for this period/month."
                )

            # Create accrued period record
            accrued_period_data = AccruedPeriodCreate(
                contract_id=contract.id,
                service_period_id=service_period.id,
                accrual_date=target_month_start,  # Use the first day of the month
                accrued_amount=round(accrued_amount, 2),  # Round to cents
                accrual_portion=accrual_portion,
                # Status reflects the period's status during the month's overlap
                status=service_period.status,
                # sessions calculated for the month overlap
                sessions_in_period=sessions_in_month,
                total_contract_amount=contract.contract_amount,
                # Use contract status change date if relevant this month
                status_change_date=service_period.status_change_date if (
                    service_period.status_change_date and
                    service_period.status_change_date.year == target_month_start.year and
                    service_period.status_change_date.month == target_month_start.month
                ) else None
            )

            # Save to database
            accrued_period = AccruedPeriod(**accrued_period_data.model_dump())
            contract.accrued_amount += accrued_amount
            self.db.add(contract)
            self.db.add(accrued_period)
            self.db.commit()
            self.db.refresh(accrued_period)

            return ContractProcessingResult(
                **result_args,
                status=ProcessingStatus.SUCCESS,
                accrued_period=accrued_period  # Pass the created object
            )

        except Exception as e:
            self.db.rollback()  # Rollback on error
            return ContractProcessingResult(
                **result_args,
                status=ProcessingStatus.FAILED,
                message=f"Error processing period {service_period.id}: {str(e)}"
            )
