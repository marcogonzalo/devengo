from typing import Optional, List
from sqlmodel import Field, Relationship
from src.api.common.models.base import BaseModel, TimestampMixin


class Service(BaseModel, TimestampMixin, table=True):
    """
    Service model to store educational services (course programs)
    """
    id: int = Field(default=None, primary_key=True)

    # External service ID (from 4Geeks)
    external_id: Optional[str] = Field(default=None, index=True)

    # Service details
    account_identifier: Optional[str] = Field(default=None, index=True)
    name: str
    description: Optional[str] = None

    # Class schedule information
    total_sessions: int = 60
    sessions_per_week: int = 3

    # Relationships
    contracts: List["ServiceContract"] = Relationship(back_populates="service")

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True
