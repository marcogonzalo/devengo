from datetime import date
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

from src.api.common.constants.services import ServiceContractStatus


class ProcessingStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class AccruedPeriodBase(BaseModel):
    contract_id: int
    service_period_id: Optional[int] = None
    accrual_date: date
    accrued_amount: float = Field(ge=0)
    accrual_portion: float = Field(ge=0, le=1)
    status: ServiceContractStatus = ServiceContractStatus.ACTIVE
    classes_in_period: int = Field(ge=0)
    total_contract_amount: float = Field(ge=0)
    status_change_date: Optional[date] = None


class AccruedPeriodCreate(AccruedPeriodBase):
    pass


class AccruedPeriodUpdate(BaseModel):
    accrued_amount: Optional[float] = Field(ge=0)
    accrual_portion: Optional[float] = Field(ge=0, le=1)
    status: Optional[ServiceContractStatus]
    status_change_date: Optional[date]


class AccruedPeriodInDB(AccruedPeriodBase):
    id: int

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
    successful_periods: int
    failed_periods: int
    results: List[ContractProcessingResult]
