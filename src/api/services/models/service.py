from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum
from sqlmodel import Field, SQLModel, Relationship, Column, JSON
from src.api.common.models.base import BaseModel, TimestampMixin
from src.api.clients.models.client import Client


class ServiceStatus(str, Enum):
    ACTIVE = "active"
    POSTPONED = "postponed"
    DROPPED = "dropped"
    ENDED = "ended"


class Service(BaseModel, TimestampMixin, table=True):
    """
    Service model to store educational services (courses, cohorts, etc.)
    """
    id: Optional[int] = Field(default=None, primary_key=True)

    # External service ID (from 4Geeks)
    external_id: str = Field(index=True)

    # Service details
    name: str
    description: Optional[str] = None
    start_date: date
    end_date: date

    # Class schedule information
    total_classes: int
    classes_per_week: int
    class_days: str  # Stored as comma-separated values, e.g., "Mon,Wed"

    # Cost information
    total_cost: float
    currency: str = "EUR"

    # Relationships
    enrollments: List["ServiceEnrollment"] = Relationship(
        back_populates="service")

    class Config:
        from_attributes = True


class ServiceEnrollment(BaseModel, TimestampMixin, table=True):
    """
    Model to store client enrollments in services
    """
    id: Optional[int] = Field(default=None, primary_key=True)

    # Service relationship
    service_id: int = Field(foreign_key="service.id")
    service: Service = Relationship(back_populates="enrollments")

    # Client relationship
    client_id: int = Field(foreign_key="client.id")
    client: Client = Relationship()

    # Enrollment details
    enrollment_date: date
    status: ServiceStatus = ServiceStatus.ACTIVE

    # Status change dates
    postponed_date: Optional[date] = None
    dropped_date: Optional[date] = None
    completed_date: Optional[date] = None

    class Config:
        from_attributes = True
