from typing import TYPE_CHECKING, List
from sqlmodel import Field, Relationship
from src.api.common.models.base import BaseModel, TimestampMixin
from src.api.accruals.constants.accruals import ContractAccrualStatus
from src.api.accruals.models.accrued_period import AccruedPeriod

if TYPE_CHECKING:
    from src.api.services.models.service_contract import ServiceContract

class ContractAccrual(BaseModel, TimestampMixin, table=True):
    """Model to store contract-level accrual data."""
    id: int = Field(default=None, primary_key=True)
    contract_id: int = Field(foreign_key="servicecontract.id", nullable=False, unique=True)

    # Accrual data
    total_amount_to_accrue: float = Field(nullable=False)
    total_amount_accrued: float = Field(nullable=False, default=0.0)
    remaining_amount_to_accrue: float = Field(nullable=False)
    total_sessions_to_accrue: int = Field(nullable=False)
    total_sessions_accrued: int = Field(nullable=False)
    sessions_remaining_to_accrue: int = Field(nullable=False)
    accrual_status: ContractAccrualStatus = Field(default=ContractAccrualStatus.ACTIVE, nullable=False)

    # Relationship to ServiceContract
    contract: "ServiceContract" = Relationship()
    # Relationship to AccruedPeriods
    accrued_periods: List["AccruedPeriod"] = Relationship(back_populates="contract_accrual")

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True 