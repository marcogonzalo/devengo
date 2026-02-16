from sqlmodel import Field, SQLModel, Column, String, Integer, Text, DateTime
from sqlalchemy import Enum
from src.api.common.models.base import BaseModel, TimestampMixin
import enum

class SyncExecutionStatus(str, enum.Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class SyncExecution(BaseModel, TimestampMixin, table=True):
    __tablename__ = "sync_executions"
    
    id: int = Field(primary_key=True, index=True)
    process_id: str = Field(unique=True, index=True)
    process_type: str = Field()  # "import" or "accrual"
    status: SyncExecutionStatus = Field(default=SyncExecutionStatus.RUNNING)
    steps: str = Field()  # JSON string of steps
    year: int = Field(default=None)
    month: int = Field(default=None)
    start_date: str = Field(default=None)
    end_date: str = Field(default=None)
    result: str = Field(default=None)  # JSON string of results
    error_message: str = Field(default=None)