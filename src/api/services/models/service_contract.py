from typing import Optional, List
from datetime import date
from sqlmodel import Field, Relationship
from src.api.common.models.base import BaseModel, TimestampMixin
from api.common.constants.services import ServiceContractStatus
from src.api.clients.models.client import Client


class ServiceContract(BaseModel, TimestampMixin, table=True):
    """
    Model to store client contracts for services
    """
    id: int = Field(default=None, primary_key=True)

    # Service relationship
    service_id: int = Field(foreign_key="service.id")
    service: "Service" = Relationship(back_populates="contracts")

    # Client relationship
    client_id: int = Field(foreign_key="client.id")
    client: Client = Relationship()

    # contract details
    contract_date: date
    contract_amount: float
    contract_currency: str = "EUR"
    accrued_amount: float = 0
    status: ServiceContractStatus = ServiceContractStatus.ACTIVE

    # Invoices relationship
    invoices: List["Invoice"] = Relationship(back_populates="service_contract")

    # Periods relationship
    periods: List["ServicePeriod"] = Relationship(back_populates="contract")

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True
