from datetime import date
from typing import Optional
from sqlmodel import Field, Relationship
from src.api.common.constants.services import ServicePeriodStatus
from src.api.common.models.base import BaseModel, TimestampMixin


class AccruedPeriod(BaseModel, TimestampMixin, table=True):
    """Model to store accrued periods for service contracts."""
    id: int = Field(default=None, primary_key=True)
    accrual_date: date = Field(nullable=False, index=True)
    accrued_amount: float = Field(nullable=False)
    # Percentage of total contract amount accrued (0.0 to 1.0)
    accrual_portion: float = Field(nullable=False)
    status: ServicePeriodStatus  = Field(nullable=False, index=True,
                                          default=ServicePeriodStatus.ACTIVE.value)
    sessions_in_period: int = Field(nullable=False)
    total_contract_amount: float = Field(nullable=False)
    status_change_date: Optional[date] = Field(nullable=True)

    # Foreign key to the associated contract accrual
    contract_accrual_id: int = Field(foreign_key="contractaccrual.id", nullable=False)
    contract_accrual: "ContractAccrual" = Relationship(back_populates="accrued_periods")

    # Foreign key to the associated service period
    service_period_id: Optional[int] = Field(
        default=None, foreign_key="serviceperiod.id", nullable=True)
    service_period: Optional["ServicePeriod"] = Relationship(
        back_populates="accruals")

    class Config:
        from_attributes = True
