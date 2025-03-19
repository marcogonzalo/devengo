from typing import List, Optional, Dict, Any
from sqlmodel import Session, select
from datetime import date
from src.api.invoices.models.invoice import Invoice, InvoiceAccrual
from src.api.invoices.schemas.invoice import InvoiceCreate, InvoiceUpdate, InvoiceAccrualCreate


class InvoiceService:
    def __init__(self, db: Session):
        self.db = db

    def create_invoice(self, invoice_data: InvoiceCreate) -> Invoice:
        """Create a new invoice"""
        invoice = Invoice(
            external_id=invoice_data.external_id,
            # client_id=invoice_data.client_id,
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

        invoice_data_dict = invoice_data.dict(exclude_unset=True)
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

    def create_invoice_accrual(self, accrual_data: InvoiceAccrualCreate) -> InvoiceAccrual:
        """Create a new invoice accrual"""
        accrual = InvoiceAccrual(
            invoice_id=accrual_data.invoice_id,
            # service_id=accrual_data.service_id,
            accrual_date=accrual_data.accrual_date,
            amount=accrual_data.amount,
            percentage=accrual_data.percentage,
            status=accrual_data.status
        )

        self.db.add(accrual)
        self.db.commit()
        self.db.refresh(accrual)
        return accrual

    def get_invoice_accruals(self, invoice_id: int) -> List[InvoiceAccrual]:
        """Get all accruals for an invoice"""
        return self.db.exec(select(InvoiceAccrual).where(InvoiceAccrual.invoice_id == invoice_id)).all()

    def get_accruals_by_date_range(self, start_date: date, end_date: date) -> List[InvoiceAccrual]:
        """Get all accruals within a date range"""
        return self.db.exec(
            select(InvoiceAccrual)
            .where(InvoiceAccrual.accrual_date >= start_date)
            .where(InvoiceAccrual.accrual_date <= end_date)
        ).all()

    def get_accruals_by_month_year(self, year: int, month: int) -> List[InvoiceAccrual]:
        """Get all accruals for a specific month and year"""
        # This assumes accrual_date is always the first day of the month
        # In a real implementation, you might want to check the month and year components
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)

        return self.db.exec(
            select(InvoiceAccrual)
            .where(InvoiceAccrual.accrual_date >= start_date)
            .where(InvoiceAccrual.accrual_date < end_date)
        ).all()
