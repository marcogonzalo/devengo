from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel

from src.api.sync.models.sync_execution import SyncExecutionStatus


class SyncExecutionBase(BaseModel):
    process_id: str
    step_name: str
    status: SyncExecutionStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class SyncExecutionCreate(SyncExecutionBase):
    pass


class SyncExecutionUpdate(BaseModel):
    status: Optional[SyncExecutionStatus] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class SyncExecutionRead(SyncExecutionBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
