from typing import Optional, List, TYPE_CHECKING
from datetime import date, timedelta
from fastapi.logger import logger
from sqlmodel import Field, Relationship
from src.api.common.models.base import BaseModel, TimestampMixin
from src.api.common.constants.services import ServicePeriodStatus

if TYPE_CHECKING:
    from src.api.accruals.models.accrued_period import AccruedPeriod


class ServicePeriod(BaseModel, TimestampMixin, table=True):
    """
    Model to store periods when a service contract is active
    Allows tracking of pause/resume cycles for service delivery
    """
    id: int = Field(default=None, primary_key=True)
    external_id: Optional[str] = Field(default=None)

    # ServiceContract relationship
    # Note: must match the lowercase table name that SQLModel generates
    contract_id: int = Field(foreign_key="servicecontract.id")
    contract: "ServiceContract" = Relationship(back_populates="periods")

    # Period details
    name: Optional[str] = Field(default=None)
    start_date: date = Field(index=True)
    end_date: date = Field(index=True)
    status: ServicePeriodStatus = Field(
        default=ServicePeriodStatus.ACTIVE,
        index=True
    )
    status_change_date: Optional[date] = Field(
        default=None,
        description="Date when the status was last changed. Updated automatically when status changes."
    )

    # Relationship with AccruedPeriod
    accruals: List["AccruedPeriod"] = Relationship(
        back_populates="service_period")

    def __setattr__(self, name: str, value: any) -> None:
        """Override setattr to track status changes and update status_change_date."""
        if name == "status" and hasattr(self, "status"):
            old_status = getattr(self, "status")
            if old_status != value:
                # Status is changing, update status_change_date
                super().__setattr__("status_change_date", date.today())
                logger.info(
                    f"ServicePeriod {self.id}: Status changed from {old_status} to {value}")

        super().__setattr__(name, value)

    def get_sessions_between(self, start: date, end: date) -> int:
        """
        Calculate the number of sessions between two dates based on the service configuration.
        Takes into account the service's sessions_per_week setting.
        """
        if not self.contract or not self.contract.service:
            return 0

        # Ensure dates are within period bounds
        effective_start = max(self.start_date, start)
        effective_end = min(self.end_date, end)

        if effective_start > effective_end:
            return 0

        # Calculate weeks (including partial weeks)
        days = (effective_end - effective_start).days + 1
        weeks = days / 7.0

        # Calculate sessions based on service configuration
        sessions = round(weeks * self.contract.service.sessions_per_week)

        # Ensure we don't exceed the service's total sessions
        total_period_days = (self.end_date - self.start_date).days + 1
        total_period_weeks = total_period_days / 7.0
        max_period_sessions = round(
            total_period_weeks * self.contract.service.sessions_per_week)
        max_period_sessions = min(
            max_period_sessions, self.contract.service.total_sessions)

        # Calculate the proportion of sessions for this date range
        if max_period_sessions > 0:
            proportion = days / total_period_days
            sessions = round(max_period_sessions * proportion)

        return sessions

    def get_total_sessions(self) -> int:
        """
        Get the total number of sessions for this period based on service configuration.
        """
        if not self.contract or not self.contract.service:
            return 0

        # Calculate total weeks in period
        total_days = (self.end_date - self.start_date).days + 1
        total_weeks = total_days / 7.0

        # Calculate total sessions based on service configuration
        total_sessions = round(
            total_weeks * self.contract.service.sessions_per_week)

        # Don't exceed service's total sessions
        return min(total_sessions, self.contract.service.total_sessions)

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True
