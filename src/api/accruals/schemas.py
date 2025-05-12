from datetime import date
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

from src.api.common.constants.services import ServicePeriodStatus


class ProcessingStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class AccruedPeriodBase(BaseModel):
    contract_accrual_id: int
    service_period_id: Optional[int] = None
    accrual_date: date
    accrued_amount: float = Field(ge=0)
    accrual_portion: float = Field(ge=0, le=1)
    status: ServicePeriodStatus = ServicePeriodStatus.ACTIVE
    sessions_in_period: int = Field(ge=0)
    total_contract_amount: float = Field(ge=0)
    status_change_date: Optional[date] = None


class AccruedPeriodCreate(AccruedPeriodBase):
    pass


class AccruedPeriodUpdate(BaseModel):
    accrued_amount: Optional[float] = Field(ge=0)
    accrual_portion: Optional[float] = Field(ge=0, le=1)
    status: Optional[ServicePeriodStatus]
    status_change_date: Optional[date]


class AccruedPeriodInDB(AccruedPeriodBase):
    id: int
    # Optionally, include total_amount_accrued if you want to expose it here
    # total_amount_accrued: float
    class Config:
        from_attributes = True


class AccruedPeriodResponse(AccruedPeriodInDB):
    pass


class ProcessPeriodRequest(BaseModel):
    period_start_date: date = Field(...,
                                    description="First day of the month to be processed")


class ContractProcessingResult(BaseModel):
    contract_id: int
    service_period_id: Optional[int] = None
    status: ProcessingStatus
    message: Optional[str] = None
    accrued_period: Optional[AccruedPeriodResponse] = None


class ProcessPeriodResponse(BaseModel):
    period_start_date: date
    total_periods_processed: int
    successful_accruals: int
    failed_accruals: int
    existing_accruals: int
    results: List[ContractProcessingResult]


# Add a ContractAccrualBase schema for completeness
class ContractAccrualBase(BaseModel):
    id: int
    contract_id: int
    total_amount_to_accrue: float
    remaining_amount_to_accrue: float
    total_amount_accrued: float
    total_sessions_to_accrue: int
    total_sessions_accrued: int
    sessions_remaining_to_accrue: int
    accrual_status: str
    class Config:
        from_attributes = True
