from typing import TYPE_CHECKING, List
from datetime import date
from sqlmodel import Field, Relationship
from src.api.common.models.base import BaseModel, TimestampMixin
from api.common.constants.services import ServiceContractStatus
from src.api.services.models.service_period import ServicePeriod
from src.api.invoices.models.invoice import Invoice
from src.api.clients.models.client import Client

if TYPE_CHECKING:
    from src.api.services.models.service import Service


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
    status: ServiceContractStatus = Field(
        default=ServiceContractStatus.ACTIVE,
        index=True
    )

    # Relationships
    invoices: List[Invoice] = Relationship(back_populates="service_contract")
    periods: List[ServicePeriod] = Relationship(back_populates="contract")

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True
