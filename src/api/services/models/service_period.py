from typing import Optional
from datetime import date
from sqlmodel import Field, Relationship
from src.api.common.models.base import BaseModel, TimestampMixin
from api.common.constants.services import ServiceStatus


class ServicePeriod(BaseModel, TimestampMixin, table=True):
    """
    Model to store periods when a service contract is active
    Allows tracking of pause/resume cycles for service delivery
    """
    id: int = Field(default=None, primary_key=True)
    external_id: Optional[str] = Field(default=None)

    # ServiceContract relationship
    # Note: must match the lowercase table name that SQLModel generates
    contract_id: int = Field(foreign_key="servicecontract.id")
    contract: "ServiceContract" = Relationship(back_populates="periods")

    # Period details
    name: Optional[str] = Field(default=None)
    start_date: date = Field(index=True)
    end_date: date = Field(index=True)
    # Using ServiceStatus (active, postponed, dropped, ended)
    status: ServiceStatus = Field(default=ServiceStatus.ACTIVE, index=True)

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True
        
# Import at the end to avoid circular imports
from src.api.services.models.service_contract import ServiceContract  # noqa 