from typing import Optional
from datetime import datetime, timezone
from enum import Enum
from sqlmodel import Field, UniqueConstraint
from src.api.common.models.base import BaseModel, TimestampMixin


class AccrualStatus(str, Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    CANCELLED = "cancelled"


class AccrualPeriod(BaseModel, TimestampMixin, table=True):
    """
    Model to represent an accrual period (typically a month)
    """
    id: Optional[int] = Field(default=None, primary_key=True)

    # Period information
    year: int
    month: int

    # Status
    status: AccrualStatus = AccrualStatus.PENDING

    # Processing dates
    processed_at: Optional[datetime] = None

    # Unique constraint on year and month
    __table_args__ = (
        UniqueConstraint("year", "month", name="year_month_unique"),
    )

    class Config:
        from_attributes = True


class AccrualClassDistribution(BaseModel, TimestampMixin, table=True):
    """
    Model to store the distribution of classes per month for a service
    """
    id: Optional[int] = Field(default=None, primary_key=True)

    # Service relationship
    service_id: int = Field(foreign_key="service.id")

    # Period information
    year: int
    month: int

    # Distribution details
    num_classes: int
    percentage: float  # Percentage of total classes in this month

    class Config:
        from_attributes = True
