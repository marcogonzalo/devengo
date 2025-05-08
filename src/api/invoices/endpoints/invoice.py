from api.common.utils.database import get_db
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from datetime import date
from src.api.invoices.schemas.invoice import InvoiceCreate, InvoiceRead, InvoiceUpdate
from src.api.invoices.services.invoice_service import InvoiceService

router = APIRouter(prefix="/invoices", tags=["invoices"])


def get_invoice_service(db: Session = Depends(get_db)):
    return InvoiceService(db)


@router.post("", response_model=InvoiceRead)
def create_invoice(
    invoice_data: InvoiceCreate,
    invoice_service: InvoiceService = Depends(get_invoice_service)
):
    """Create a new invoice"""
    return invoice_service.create_invoice(invoice_data)


@router.get("/{invoice_id}", response_model=InvoiceRead)
def get_invoice(
    invoice_id: int,
    invoice_service: InvoiceService = Depends(get_invoice_service)
):
    """Get an invoice by ID"""
    invoice = invoice_service.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.get("/external/{external_id}", response_model=InvoiceRead)
def get_invoice_by_external_id(
    external_id: str,
    invoice_service: InvoiceService = Depends(get_invoice_service)
):
    """Get an invoice by external ID"""
    invoice = invoice_service.get_invoice_by_external_id(external_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.get("", response_model=List[InvoiceRead])
def get_invoices(
    skip: int = 0,
    limit: int = 100,
    client_id: Optional[int] = None,
    invoice_service: InvoiceService = Depends(get_invoice_service)
):
    """Get a list of invoices"""
    if client_id:
        return invoice_service.get_invoices_by_client(client_id)
    return invoice_service.get_invoices(skip, limit)


@router.put("/{invoice_id}", response_model=InvoiceRead)
def update_invoice(
    invoice_id: int,
    invoice_data: InvoiceUpdate,
    invoice_service: InvoiceService = Depends(get_invoice_service)
):
    """Update an invoice"""
    invoice = invoice_service.update_invoice(invoice_id, invoice_data)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.delete("/{invoice_id}")
def delete_invoice(
    invoice_id: int,
    invoice_service: InvoiceService = Depends(get_invoice_service)
):
    """Delete an invoice"""
    success = invoice_service.delete_invoice(invoice_id)
    if not success:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {"message": "Invoice deleted successfully"}
