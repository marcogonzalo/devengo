from typing import Optional, List, Dict, Any
from datetime import date
from sqlmodel import Field, Relationship, Column, JSON
from src.api.common.models.base import BaseModel, TimestampMixin
from src.api.clients.models import Client


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

    # Relationships
    accruals: List["InvoiceAccrual"] = Relationship(back_populates="invoice")

    class Config:
        from_attributes = True


class InvoiceAccrual(BaseModel, TimestampMixin, table=True):
    """
    Model to store accrual portions of invoices
    """
    id: Optional[int] = Field(default=None, primary_key=True)

    # Invoice relationship
    invoice_id: int = Field(foreign_key="invoice.id")
    invoice: Invoice = Relationship(back_populates="accruals")

    # Service relationship (optional)
    # service_id: Optional[int] = Field(default=None, foreign_key="service.id")

    # Accrual details
    accrual_date: date  # The month/year this accrual applies to
    amount: float  # The amount accrued for this period
    percentage: float  # The percentage of the total invoice this accrual represents

    # Status
    status: str = "pending"  # e.g., "pending", "processed", "cancelled"

    class Config:
        from_attributes = True
