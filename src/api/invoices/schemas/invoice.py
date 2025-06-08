from typing import Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, date


class InvoiceBase(BaseModel):
    """Base schema for invoice data"""
    invoice_number: str
    invoice_date: date
    due_date: Optional[date] = None
    total_amount: float
    currency: str = "EUR"
    status: int

    class Config:
        from_attributes = True


class InvoiceCreate(InvoiceBase):
    """Schema for creating a new invoice"""
    external_id: str
    client_id: Optional[int] = None
    original_data: Dict[str, Any] = {}


class InvoiceRead(InvoiceBase):
    """Schema for reading invoice data"""
    id: int
    external_id: str
    client_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class InvoiceUpdate(BaseModel):
    """Schema for updating invoice data"""
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = None
    status: Optional[int] = None
    client_id: Optional[int] = None
    service_contract_id: Optional[int] = None
    original_data: Optional[Dict[str, Any]] = None
