from datetime import date
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

from src.api.common.constants.services import ServicePeriodStatus


class ProcessingStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    HALTED = "HALTED"
    SKIPPED = "SKIPPED"


class AccruedPeriodBase(BaseModel):
    contract_accrual_id: int
    service_period_id: Optional[int] = None
    accrual_date: date
    accrued_amount: float = Field(default=0)
    accrual_portion: float = Field(ge=0, le=1)
    status: ServicePeriodStatus = ServicePeriodStatus.ACTIVE
    sessions_in_period: int = Field(ge=0, default=60)
    total_contract_amount: float = Field(default=0)
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
    skipped_accruals: int
    results: List[ContractProcessingResult]
    notifications: List[dict] = []


class ContractAccrualProcessingResponse(BaseModel):
    """Response schema for contract accrual processing."""
    period_start_date: date
    summary: dict = Field(description="Processing summary with counts")
    processing_results: List[ContractProcessingResult] = Field(
        description="Detailed results for each contract")
    notifications: List[dict] = Field(
        default=[], description="System notifications and alerts")


class NotificationSchema(BaseModel):
    """Schema for processing notifications."""
    type: str = Field(
        description="Notification type (e.g., 'not_congruent_status')")
    message: str = Field(description="Notification message")
    timestamp: str = Field(description="ISO timestamp of notification")
    contract_id: Optional[int] = Field(
        None, description="Related contract ID if applicable")


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


class SyncActionSummary(BaseModel):
    """Schema for sync-actions integration summary."""
    action_type: str = Field(
        default="contract_accrual_processing", description="Type of sync action")
    target_period: date = Field(description="Processing period (month)")
    status: str = Field(
        description="Overall processing status: SUCCESS, PARTIAL, FAILED")
    execution_timestamp: str = Field(
        description="ISO timestamp when processing completed")

    # Summary statistics
    total_contracts: int = Field(description="Total contracts processed")
    successful_count: int = Field(
        description="Successfully processed contracts")
    failed_count: int = Field(description="Failed contract processing")
    skipped_count: int = Field(description="Skipped contracts")

    # Financial summary
    total_amount_accrued: float = Field(
        default=0.0, description="Total amount accrued this period")
    contracts_completed: int = Field(
        default=0, description="Contracts that reached completion")
    contracts_auto_closed: int = Field(
        default=0, description="Contracts automatically closed")
    contracts_auto_canceled: int = Field(
        default=0, description="Contracts automatically canceled")

    # Error and notification summary
    critical_notifications: int = Field(
        default=0, description="Number of critical notifications")
    warning_notifications: int = Field(
        default=0, description="Number of warning notifications")

    # Performance metrics
    processing_duration_seconds: Optional[float] = Field(
        None, description="Total processing time")
    contracts_per_second: Optional[float] = Field(
        None, description="Processing rate")

    # Detailed breakdown (optional for deeper analysis)
    breakdown_by_status: dict = Field(
        default={}, description="Detailed breakdown by processing status")
    failed_contract_ids: List[int] = Field(
        default=[], description="List of contract IDs that failed processing")

    # Compliance and audit
    data_consistency_check: bool = Field(
        default=True, description="Whether data consistency checks passed")
    manual_review_required: bool = Field(
        default=False, description="Whether manual review is needed")


class SyncActionDetail(BaseModel):
    """Schema for detailed sync-action logging."""
    contract_id: int
    client_identifier: Optional[str] = None
    contract_amount: Optional[float] = None
    processing_status: ProcessingStatus
    accrued_amount: Optional[float] = None
    final_contract_status: Optional[str] = None
    error_message: Optional[str] = None
    processing_notes: Optional[str] = None
