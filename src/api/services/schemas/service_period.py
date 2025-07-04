from typing import Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime, date
from src.api.common.constants.services import ServicePeriodStatus


class ServicePeriodBase(BaseModel):
    """Base schema for service period data"""
    name: Optional[str] = None
    external_id: Optional[str] = None
    start_date: date
    end_date: date
    status: ServicePeriodStatus = ServicePeriodStatus.ACTIVE
    status_change_date: Optional[date] = None
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)


class ServicePeriodCreate(ServicePeriodBase):
    """Schema for creating a new service period"""
    contract_id: int


class ServicePeriodRead(ServicePeriodBase):
    """Schema for reading service period data"""
    id: int
    contract_id: int
    created_at: datetime
    updated_at: datetime


class ServicePeriodUpdate(BaseModel):
    """Schema for updating service period data"""
    name: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[ServicePeriodStatus] = None
    
    model_config = ConfigDict(arbitrary_types_allowed=True) 