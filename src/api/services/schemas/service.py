from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict
from datetime import datetime


class ServiceBase(BaseModel):
    """Base schema for service data"""
    name: str
    description: Optional[str] = None
    external_id: Optional[str] = None
    account_identifier: Optional[str] = None
    total_sessions: Optional[int] = 60
    sessions_per_week: Optional[int] = 3
    
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)


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
    total_sessions: Optional[int] = None
    sessions_per_week: Optional[int] = None
    account_identifier: Optional[str] = None
    external_id: Optional[str] = None
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
