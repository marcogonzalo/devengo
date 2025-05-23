import calendar
from fastapi.logger import logger
from datetime import date, timedelta
from typing import List, Tuple, TYPE_CHECKING
from sqlalchemy.orm import Session, joinedload
from sqlmodel import func, or_, and_
from src.api.accruals.constants.accruals import ContractAccrualStatus
from src.api.common.constants.services import ServiceContractStatus, ServicePeriodStatus
from src.api.accruals.models import AccruedPeriod, ContractAccrual
from src.api.accruals.schemas import (
    AccruedPeriodCreate,
    ContractProcessingResult,
    ProcessingStatus
)

# Use TYPE_CHECKING for type hints to avoid runtime import if ServicePeriod is complex
if TYPE_CHECKING:
    from src.api.services.models import ServicePeriod
    from src.api.services.models.service_contract import ServiceContract


def get_month_range(year: int, month: int) -> Tuple[date, date]:
    """Returns the first and last day of a given month and year."""
    _, last_day = calendar.monthrange(year, month)
    first_day_date = date(year, month, 1)
    last_day_date = date(year, month, last_day)
    return first_day_date, last_day_date


class PeriodProcessor:
    def __init__(self, db: Session):
        self.db = db

    def _calculate_accrual_for_period(
        self,
        service_period: "ServicePeriod",
        target_month_start: date,
        contract_accrual: ContractAccrual
    ) -> Tuple[float, float, int]:
        """
        Calculate accrual amount, portion, and sessions for a service period within a target month.
        Returns (accrual_amount, accrual_portion, sessions_in_month_overlap)
        """
        default_return_value = (0.0, 0.0, 0)
        month_start, month_end = get_month_range(
            target_month_start.year, target_month_start.month)
        # Determine the overlap of the service period with the target month
        overlap_start = max(service_period.start_date, month_start)
        overlap_end = min(service_period.end_date, month_end)
        effective_end_date = overlap_end

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

        # Ensure sessions in month overlap is not greater than sessions remaining
        # This can happen if there were some sessions that matched with holidays in previous months
        if overlap_end < month_end:
            sessions_in_month_overlap = contract_accrual.sessions_remaining_to_accrue
        else:
            sessions_in_month_overlap = service_period.get_sessions_between(
                overlap_start, effective_end_date)

        # Get accrued totals up to this month
        total_accrued_amount, total_accrued_sessions = contract_accrual.total_amount_accrued, contract_accrual.total_sessions_accrued
        # self._get_accrued_totals_before_month(
        # contract_accrual.id, target_month_start.year, target_month_start.month)

        # Get the remaining sessions and amount for the contract after accruals up to this month
        sessions_remaining, amount_remaining = contract_accrual.sessions_remaining_to_accrue, contract_accrual.remaining_amount_to_accrue
        # self._get_sessions_and_amount_remaining(
        #     contract_accrual, total_accrued_sessions, total_accrued_amount)

        # Calculate the accrual portion and amount for the contract for this month
        portion_to_accrue, amount_to_accrue = self._get_accrual_portion_and_amount(
            sessions_in_month_overlap, sessions_remaining, amount_remaining)

        # If period is DROPPED, remaining accrual is completed at drop date
        if service_period.status == ServicePeriodStatus.DROPPED:
            if not service_period.status_change_date:
                return default_return_value

            if service_period.status_change_date and month_start <= service_period.status_change_date <= month_end:
                effective_end_date = service_period.end_date

                # Accrue the remaining contract amount in this period
                sessions_in_month_overlap = sessions_remaining
                portion_to_accrue, amount_to_accrue = self._get_accrual_portion_and_amount(
                    sessions_in_month_overlap, sessions_remaining, amount_remaining)
                return amount_to_accrue, portion_to_accrue, sessions_in_month_overlap
            elif service_period.status_change_date < month_start:
                # Dropped before this month
                return default_return_value

        total_contract_sessions = contract_accrual.total_sessions_to_accrue

        if sessions_in_month_overlap <= 0 or total_contract_sessions <= 0:
            return default_return_value

        # Ensure start is not after end
        if overlap_start > effective_end_date:
            return default_return_value

        # if sessions_remaining <= 0 or amount_remaining <= 0:
        #     return default_return_value

        return amount_to_accrue, portion_to_accrue, sessions_in_month_overlap

    def _get_accrual_portion_and_amount(self, sessions_in_month_overlap: int, sessions_remaining: int, amount_remaining: float) -> Tuple[float, float]:
        """
        Calculate the accrual portion and amount for a contract based on the sessions in month overlap.
        """
        portion_to_accrue = round(
            sessions_in_month_overlap / sessions_remaining, 2)
        amount_to_accrue = round(amount_remaining * portion_to_accrue, 2)
        return portion_to_accrue, amount_to_accrue

    def _get_accrued_totals_before_month(self, contract_accrual_id: int, year: int, month: int) -> Tuple[float, int]:
        """
        Returns the total accrued amount and sessions for a contract up to (but not including) the given year and month.
        """

        # Get total accrued amount and sessions from accrued periods
        total_accrued_amount = self.db.query(func.coalesce(func.sum(AccruedPeriod.accrued_amount), 0.0)).filter(
            AccruedPeriod.contract_accrual_id == contract_accrual_id,
            or_(
                func.extract('year', AccruedPeriod.accrual_date) < year,
                and_(
                    func.extract('year', AccruedPeriod.accrual_date) == year,
                    func.extract('month', AccruedPeriod.accrual_date) < month
                )
            )
        ).scalar() or 0.0
        total_accrued_sessions = self.db.query(func.coalesce(func.sum(AccruedPeriod.sessions_in_period), 0)).filter(
            AccruedPeriod.contract_accrual_id == contract_accrual_id,
            or_(
                func.extract('year', AccruedPeriod.accrual_date) < year,
                and_(
                    func.extract('year', AccruedPeriod.accrual_date) == year,
                    func.extract('month', AccruedPeriod.accrual_date) < month
                )
            )
        ).scalar() or 0
        return total_accrued_amount, total_accrued_sessions

    def _get_contract_accrual(self, contract: "ServiceContract") -> ContractAccrual:
        accrual = contract.contract_accrual
        if not accrual:
            # Create ContractAccrual if it does not exist
            if not contract.service:
                raise ValueError(
                    f"No Service found for id={contract.id}")
            total_sessions = contract.service.total_sessions
            accrual = ContractAccrual(
                contract_id=contract.id,
                total_amount_to_accrue=contract.contract_amount,
                remaining_amount_to_accrue=contract.contract_amount,
                total_sessions_to_accrue=total_sessions,
                total_sessions_accrued=0,
                sessions_remaining_to_accrue=total_sessions,
                accrual_status="ACTIVE"
            )
            self.db.add(accrual)
            self.db.commit()
            self.db.refresh(accrual)
        return accrual

    def _get_sessions_and_amount_remaining(self, contract_accrual: ContractAccrual, total_accrued_sessions: int, total_accrued_amount: float) -> Tuple[int, float]:
        """
        Calculate the new remaining sessions and amount for a contract based on the total accrued sessions and amount.
        """
        sessions_remaining = contract_accrual.total_sessions_to_accrue - total_accrued_sessions
        amount_remaining = contract_accrual.total_amount_to_accrue - total_accrued_amount
        return sessions_remaining, amount_remaining

    def _update_contract_accrual(self, contract_accrual, sessions_in_month, accrued_amount):
        contract_accrual.total_amount_accrued += accrued_amount
        contract_accrual.remaining_amount_to_accrue -= accrued_amount
        contract_accrual.total_sessions_accrued += sessions_in_month
        contract_accrual.sessions_remaining_to_accrue -= sessions_in_month
        if contract_accrual.accrual_status == ContractAccrualStatus.ACTIVE and contract_accrual.remaining_amount_to_accrue < 1 and contract_accrual.sessions_remaining_to_accrue == 0:
            contract_accrual.accrual_status = ContractAccrualStatus.COMPLETED.value
        return contract_accrual

    def get_contract_ids_with_accruals_in_month(self, target_month_start: date) -> List[int]:
        """
        Get all existing accruals for a target month.
        """
        from sqlalchemy import extract
        # Query AccruedPeriod with joined ContractAccrual data
        # Query to get service_period_id and contract_id from accrued periods in the target month
        results = self.db.query(
            ContractAccrual.contract_id
        ).select_from(AccruedPeriod).join(
            ContractAccrual,
            AccruedPeriod.contract_accrual_id == ContractAccrual.id
        ).filter(
            extract('year', AccruedPeriod.accrual_date) == target_month_start.year,
            extract('month', AccruedPeriod.accrual_date) == target_month_start.month
        ).all()

        # Return a list of service period IDs that already have accruals for this month
        return [result[0] for result in results]  # Return only contract_id

    def get_service_periods_in_month(self, target_month_start: date) -> List["ServicePeriod"]:
        """Get all service periods active or changing status within the given month."""
        from src.api.services.models import ServicePeriod, ServiceContract

        month_start, month_end = get_month_range(
            target_month_start.year, target_month_start.month)

        return (
            self.db.query(ServicePeriod)
            .options(
                joinedload(ServicePeriod.contract),  # Eager load contract
                joinedload(ServicePeriod.contract).joinedload(
                    ServiceContract.contract_accrual)  # Eager load contract accrual
            )
            .filter(
                # Period overlaps with the month
                (ServicePeriod.start_date <= month_end) &
                (ServicePeriod.end_date >= month_start)
            )
            # Consider only active or paused periods, or periods ending this month
            .filter(or_(
                ServicePeriod.status == ServicePeriodStatus.ACTIVE,
                # Postponed or Dropped periods must be accrued (partially or entirely) if they happen in the current accrual period
                and_(ServicePeriod.status.in_(
                    [
                        ServicePeriodStatus.POSTPONED,
                        ServicePeriodStatus.DROPPED
                    ]
                ),
                    (ServicePeriod.status_change_date.is_(None) |
                     ((ServicePeriod.status_change_date >= month_start)  # &
                      # (ServicePeriod.status_change_date <= month_end)
                      ))
                )))
            .all()
        )

    def accrue_service_period(
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
            # Fetch or create ContractAccrual once
            contract_accrual = self._get_contract_accrual(contract)
        except Exception as e:
            return ContractProcessingResult(
                **result_args,
                status=ProcessingStatus.FAILED,
                message=f"Error generating ContractAccrual for contract {contract.id}: {str(e)}"
            )
        

        # Check if the accrual is completed
        if contract_accrual.accrual_status == ContractAccrualStatus.COMPLETED:
            return ContractProcessingResult(
                **result_args,
                status=ProcessingStatus.SUCCESS,
                message="Accrual is completed, skipping accrual."
            )

        # Check if the accrual was paused and resume it
        if contract_accrual.accrual_status == ContractAccrualStatus.PAUSED:
            # restore the total sessions to accrue to the new total sessions accrued after the pause
            sessions_to_accrue = service_period.get_sessions_between(
                max(service_period.start_date, target_month_start), service_period.end_date)
            contract_accrual.total_sessions_to_accrue = contract_accrual.total_sessions_accrued + sessions_to_accrue
            contract_accrual.sessions_remaining_to_accrue = contract_accrual.total_sessions_to_accrue - contract_accrual.total_sessions_accrued
            contract_accrual.accrual_status = ContractAccrualStatus.ACTIVE
            self.db.add(contract_accrual)
            self.db.commit()
            self.db.refresh(contract_accrual)
        
        # Calculate standard accrual for the overlapping period/month
        amount_to_accrue, portion_to_accrue, sessions_in_month = self._calculate_accrual_for_period(
            service_period, target_month_start, contract_accrual
        )

        # Special handling if period was DROPPED or POSTPONED this month
        if (
            service_period.status_change_date and
            service_period.status_change_date.year == target_month_start.year and
            service_period.status_change_date.month == target_month_start.month
        ):
            if service_period.status == ServicePeriodStatus.DROPPED and contract.status == ServiceContractStatus.ACTIVE:
                # Change the status of the contract to CANCELED
                try:
                    contract.status = ServiceContractStatus.CANCELED
                    self.db.add(contract)
                    self.db.commit()
                    self.db.refresh(contract)
                except Exception as e:
                    self.db.rollback()  # Rollback on error
                    logger.error(
                        f"Error changing contract status to CANCELED: {e}")
            elif service_period.status == ServicePeriodStatus.POSTPONED and contract_accrual.accrual_status == ContractAccrualStatus.ACTIVE:
                # Change the status of the contract to POSTPONED
                try:
                    contract_accrual.accrual_status = ContractAccrualStatus.PAUSED
                    self.db.add(contract_accrual)
                    self.db.commit()
                    self.db.refresh(contract_accrual)
                except Exception as e:
                    self.db.rollback()  # Rollback on error
                    logger.error(
                        f"Error pausing contract accrual: {e}")

        # Only create a record if there's something to accrue
        if amount_to_accrue <= 0:
            return ContractProcessingResult(
                **result_args,
                status=ProcessingStatus.SUCCESS,
                message="No accrual needed for this period/month."
            )
        try:
            # Get the status of the service period during the month's overlap
            accrued_period_status = ServicePeriodStatus.ACTIVE
            accrued_period_status_change_date = None
            if service_period.status_change_date and (
                (service_period.status_change_date.year == target_month_start.year and service_period.status_change_date.month <= target_month_start.month) or
                service_period.status_change_date.year < target_month_start.year
            ):
                accrued_period_status = service_period.status
                accrued_period_status_change_date = service_period.status_change_date

            # Create accrued period record
            accrued_period_data = AccruedPeriodCreate(
                contract_accrual_id=contract_accrual.id,
                service_period_id=service_period.id,
                accrual_date=target_month_start,  # Use the first day of the month
                accrued_amount=amount_to_accrue,  # Round to cents
                accrual_portion=portion_to_accrue,
                # sessions calculated for the month overlap
                sessions_in_period=sessions_in_month,
                total_contract_amount=contract.contract_amount,
                # Status reflects the period's status during the month's overlap
                status=accrued_period_status,
                # Use contract status change date if relevant this month
                status_change_date=accrued_period_status_change_date
            )
        except Exception as e:
            return ContractProcessingResult(
                **result_args,
                status=ProcessingStatus.FAILED,
                message=f"Error generating AccruedPeriod for Contract Accrual {contract_accrual.id}: {str(e)}"
            )

        try:
            # Save to database
            accrued_period = AccruedPeriod(**accrued_period_data.model_dump())
            self.db.add(accrued_period)

            # Update ContractAccrual
            contract_accrual = self._update_contract_accrual(
                contract_accrual, sessions_in_month, amount_to_accrue)
            self.db.add(contract_accrual)

            self.db.commit()
            self.db.refresh(accrued_period)
            self.db.refresh(contract_accrual)
        except Exception as e:
            self.db.rollback()  # Rollback on error
            return ContractProcessingResult(
                **result_args,
                status=ProcessingStatus.FAILED,
                message=f"Error processing period {service_period.id}: {str(e)}"
            )

        return ContractProcessingResult(
            **result_args,
            status=ProcessingStatus.SUCCESS,
            accrued_period=accrued_period  # Pass the created object
        )
