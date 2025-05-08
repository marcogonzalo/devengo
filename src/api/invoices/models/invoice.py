from typing import TYPE_CHECKING, Optional, List, Dict, Any
from datetime import date
from sqlmodel import Field, Relationship, Column, JSON
from src.api.common.models.base import BaseModel, TimestampMixin
from src.api.clients.models import Client

if TYPE_CHECKING:
    from src.api.services.models.service_contract import ServiceContract


class Invoice(BaseModel, TimestampMixin, table=True):
    """
    Invoice model to store invoice data from external systems
    """
    id: Optional[int] = Field(default=None, primary_key=True)

    # External invoice ID (from Holded)
    external_id: str = Field(index=True, unique=True)

    # Client relationship
    client_id: Optional[int] = Field(default=None, foreign_key="client.id")
    client: Optional[Client] = Relationship()

    # Invoice details
    invoice_number: str
    invoice_date: date
    due_date: Optional[date] = None
    total_amount: float
    currency: str = "EUR"
    status: int  # e.g., "paid", "pending", "cancelled"

    # Store original invoice data as JSON
    original_data: Dict[str, Any] = Field(default={}, sa_column=Column(JSON))

    # Service contract relationship
    service_contract_id: Optional[int] = Field(
        default=None, foreign_key="servicecontract.id")
    service_contract: Optional["ServiceContract"] = Relationship(
        back_populates="invoices")

    class Config:
        from_attributes = True
