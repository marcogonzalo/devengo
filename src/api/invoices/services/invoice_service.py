from typing import List, Optional
from sqlmodel import Session, select
from src.api.invoices.models.invoice import Invoice
from src.api.invoices.schemas.invoice import InvoiceCreate, InvoiceUpdate


class InvoiceService:
    def __init__(self, db: Session):
        self.db = db

    def create_invoice(self, invoice_data: InvoiceCreate) -> Invoice:
        """Create a new invoice"""
        invoice = Invoice(
            external_id=invoice_data.external_id,
            client_id=invoice_data.client_id,
            invoice_number=invoice_data.invoice_number,
            invoice_date=invoice_data.invoice_date,
            due_date=invoice_data.due_date,
            total_amount=invoice_data.total_amount,
            currency=invoice_data.currency,
            status=invoice_data.status,
            original_data=invoice_data.original_data
        )

        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(invoice)
        return invoice

    def get_invoice(self, invoice_id: int) -> Optional[Invoice]:
        """Get an invoice by ID"""
        return self.db.get(Invoice, invoice_id)

    def get_invoice_by_external_id(self, external_id: str) -> Optional[Invoice]:
        """Get an invoice by external ID"""
        return self.db.exec(select(Invoice).where(Invoice.external_id == external_id)).first()

    def get_invoices(self, skip: int = 0, limit: int = 100) -> List[Invoice]:
        """Get a list of invoices"""
        return self.db.exec(select(Invoice).offset(skip).limit(limit)).all()

    # def get_invoices_by_client(self, client_id: int) -> List[Invoice]:
    #     """Get all invoices for a client"""
    #     return self.db.exec(select(Invoice).where(Invoice.client_id == client_id)).all()

    def update_invoice(self, invoice_id: int, invoice_data: InvoiceUpdate) -> Optional[Invoice]:
        """Update an invoice"""
        invoice = self.db.get(Invoice, invoice_id)
        if not invoice:
            return None

        invoice_data_dict = invoice_data.model_dump(exclude_unset=True)
        for key, value in invoice_data_dict.items():
            setattr(invoice, key, value)

        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(invoice)
        return invoice

    def delete_invoice(self, invoice_id: int) -> bool:
        """Delete an invoice"""
        invoice = self.db.get(Invoice, invoice_id)
        if not invoice:
            return False

        self.db.delete(invoice)
        self.db.commit()
        return True
