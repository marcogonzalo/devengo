from typing import Optional, List, Dict, Any
from pydantic import BaseModel, validator
from datetime import datetime, timezone
from src.api.accrual.models.accrual import AccrualStatus


class AccrualPeriodBase(BaseModel):
    """Base schema for accrual period data"""
    year: int
    month: int
    status: AccrualStatus = AccrualStatus.PENDING

    class Config:
        from_attributes = True


class AccrualPeriodCreate(AccrualPeriodBase):
    """Schema for creating a new accrual period"""
    pass


class AccrualPeriodRead(AccrualPeriodBase):
    """Schema for reading accrual period data"""
    id: int
    processed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class AccrualClassDistributionBase(BaseModel):
    """Base schema for accrual class distribution data"""
    year: int
    month: int
    num_classes: int
    percentage: float

    class Config:
        from_attributes = True


class AccrualClassDistributionCreate(AccrualClassDistributionBase):
    """Schema for creating a new accrual class distribution"""
    service_id: int


class AccrualClassDistributionRead(AccrualClassDistributionBase):
    """Schema for reading accrual class distribution data"""
    id: int
    service_id: int
    created_at: datetime
    updated_at: datetime
