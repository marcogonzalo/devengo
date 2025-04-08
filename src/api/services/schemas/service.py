from typing import Optional, List, Dict, Any
from pydantic import BaseModel, validator
from datetime import datetime, date
from src.api.services.models.service import ServiceStatus


class ServiceBase(BaseModel):
    """Base schema for service data"""
    name: str
    description: Optional[str] = None
    start_date: date
    end_date: date
    total_classes: int
    classes_per_week: int
    class_days: str
    total_cost: float
    currency: str = "EUR"

    class Config:
        from_attributes = True


class ServiceCreate(ServiceBase):
    """Schema for creating a new service"""
    external_id: str


class ServiceRead(ServiceBase):
    """Schema for reading service data"""
    id: int
    external_id: str
    created_at: datetime
    updated_at: datetime


class ServiceUpdate(BaseModel):
    """Schema for updating service data"""
    name: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    total_classes: Optional[int] = None
    classes_per_week: Optional[int] = None
    class_days: Optional[str] = None
    total_cost: Optional[float] = None
    currency: Optional[str] = None


class ServiceEnrollmentBase(BaseModel):
    """Base schema for service enrollment data"""
    enrollment_date: date
    status: ServiceStatus = ServiceStatus.ACTIVE

    class Config:
        from_attributes = True


class ServiceEnrollmentCreate(ServiceEnrollmentBase):
    """Schema for creating a new service enrollment"""
    service_id: int
    client_id: int


class ServiceEnrollmentRead(ServiceEnrollmentBase):
    """Schema for reading service enrollment data"""
    id: int
    service_id: int
    client_id: int
    postponed_date: Optional[date] = None
    dropped_date: Optional[date] = None
    completed_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime


class ServiceEnrollmentUpdate(BaseModel):
    """Schema for updating service enrollment data"""
    status: Optional[ServiceStatus] = None
    postponed_date: Optional[date] = None
    dropped_date: Optional[date] = None
    completed_date: Optional[date] = None
