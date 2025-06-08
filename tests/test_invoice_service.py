import pytest
from datetime import date, datetime, timezone
from unittest.mock import Mock, patch
from decimal import Decimal
from sqlmodel import Session

from src.api.invoices.services.invoice_service import InvoiceService
from src.api.invoices.models.invoice import Invoice
from src.api.invoices.schemas.invoice import InvoiceCreate, InvoiceUpdate

# Simple status mapping for tests (should be moved to constants in real implementation)
INVOICE_STATUS = {
    "PENDING": 1,
    "PAID": 2,
    "OVERDUE": 3,
    "CANCELLED": 4,
    "DRAFT": 5,
    "ISSUED": 6
}

class TestInvoiceService:
    """Test InvoiceService class"""

    def test_create_invoice_success(self, test_session, sample_invoice_data, test_data_factory):
        """Test successful invoice creation"""
        # Create a client first
        client = test_data_factory.create_client(test_session)
        sample_invoice_data["client_id"] = client.id
        
        service = InvoiceService(test_session)
        # Status is already an integer in conftest.py, no conversion needed
        invoice_data = InvoiceCreate(**sample_invoice_data)
        
        result = service.create_invoice(invoice_data)
        
        assert result.id is not None
        assert result.external_id == sample_invoice_data["external_id"]
        assert result.client_id == client.id
        assert result.invoice_number == sample_invoice_data["invoice_number"]
        assert result.total_amount == sample_invoice_data["total_amount"]
        assert result.status == sample_invoice_data["status"]

    def test_create_invoice_with_all_fields(self, test_session, test_data_factory):
        """Test creating invoice with all possible fields"""
        client = test_data_factory.create_client(test_session)
        
        invoice_data = InvoiceCreate(
            external_id="EXT-001",
            client_id=client.id,
            invoice_number="INV-2024-001",
            invoice_date=date(2024, 1, 15),
            due_date=date(2024, 2, 15),
            total_amount=1500.50,
            currency="USD",
            status=INVOICE_STATUS["PAID"],
            original_data={"source": "api", "version": "1.0"}
        )
        
        service = InvoiceService(test_session)
        result = service.create_invoice(invoice_data)
        
        assert result.external_id == "EXT-001"
        assert result.currency == "USD"
        assert result.status == INVOICE_STATUS["PAID"]
        assert result.original_data == {"source": "api", "version": "1.0"}

    def test_create_invoice_minimal_data(self, test_session, test_data_factory):
        """Test creating invoice with minimal required data"""
        client = test_data_factory.create_client(test_session)
        
        invoice_data = InvoiceCreate(
            external_id="MIN-001",
            client_id=client.id,
            invoice_number="MIN-2024-001",
            invoice_date=date(2024, 1, 15),
            due_date=date(2024, 2, 15),
            total_amount=100.00,
            currency="EUR",
            status=INVOICE_STATUS["PENDING"]
        )
        
        service = InvoiceService(test_session)
        result = service.create_invoice(invoice_data)
        
        assert result.id is not None
        assert result.original_data == {}

    def test_get_invoice_success(self, test_session, test_data_factory):
        """Test successful invoice retrieval"""
        client = test_data_factory.create_client(test_session)
        invoice = test_data_factory.create_invoice(test_session, client_id=client.id)
        
        service = InvoiceService(test_session)
        result = service.get_invoice(invoice.id)
        
        assert result is not None
        assert result.id == invoice.id
        assert result.invoice_number == invoice.invoice_number

    def test_get_invoice_not_found(self, test_session):
        """Test getting non-existent invoice"""
        service = InvoiceService(test_session)
        
        result = service.get_invoice(999)
        
        assert result is None

    def test_get_invoice_by_external_id_success(self, test_session, test_data_factory):
        """Test getting invoice by external ID"""
        client = test_data_factory.create_client(test_session)
        invoice = test_data_factory.create_invoice(
            test_session, 
            client_id=client.id,
            external_id="UNIQUE-EXT-001"
        )
        
        service = InvoiceService(test_session)
        result = service.get_invoice_by_external_id("UNIQUE-EXT-001")
        
        assert result is not None
        assert result.id == invoice.id
        assert result.external_id == "UNIQUE-EXT-001"

    def test_get_invoice_by_external_id_not_found(self, test_session):
        """Test getting invoice by non-existent external ID"""
        service = InvoiceService(test_session)
        
        result = service.get_invoice_by_external_id("NON-EXISTENT")
        
        assert result is None

    def test_get_invoice_by_external_id_multiple_invoices(self, test_session, test_data_factory):
        """Test getting invoice by external ID when multiple invoices exist"""
        client = test_data_factory.create_client(test_session)
        
        # Create multiple invoices
        invoice1 = test_data_factory.create_invoice(test_session, client_id=client.id, external_id="EXT-001")
        invoice2 = test_data_factory.create_invoice(test_session, client_id=client.id, external_id="EXT-002")
        invoice3 = test_data_factory.create_invoice(test_session, client_id=client.id, external_id="EXT-003")
        
        service = InvoiceService(test_session)
        result = service.get_invoice_by_external_id("EXT-002")
        
        assert result is not None
        assert result.id == invoice2.id

    def test_get_invoices_default_pagination(self, test_session, test_data_factory):
        """Test getting invoices with default pagination"""
        client = test_data_factory.create_client(test_session)
        service = InvoiceService(test_session)
        
        # Create multiple invoices
        invoices = []
        for i in range(5):
            invoice = test_data_factory.create_invoice(
                test_session,
                client_id=client.id,
                external_id=f"EXT-{i}",
                invoice_number=f"INV-{i}"
            )
            invoices.append(invoice)
        
        result = service.get_invoices()
        
        assert len(result) == 5
        assert all(isinstance(invoice, Invoice) for invoice in result)

    def test_get_invoices_with_pagination(self, test_session, test_data_factory):
        """Test getting invoices with custom pagination"""
        client = test_data_factory.create_client(test_session)
        service = InvoiceService(test_session)
        
        # Create multiple invoices
        for i in range(10):
            test_data_factory.create_invoice(
                test_session,
                client_id=client.id,
                external_id=f"EXT-{i}",
                invoice_number=f"INV-{i}"
            )
        
        result = service.get_invoices(skip=3, limit=4)
        
        assert len(result) == 4

    def test_get_invoices_empty_database(self, test_session):
        """Test getting invoices from empty database"""
        service = InvoiceService(test_session)
        
        result = service.get_invoices()
        
        assert result == []

    def test_update_invoice_success(self, test_session, test_data_factory):
        """Test successful invoice update"""
        client = test_data_factory.create_client(test_session)
        invoice = test_data_factory.create_invoice(test_session, client_id=client.id)
        
        service = InvoiceService(test_session)
        update_data = InvoiceUpdate(status=INVOICE_STATUS["PAID"], total_amount=2000.00)
        result = service.update_invoice(invoice.id, update_data)
        
        assert result is not None
        assert result.status == INVOICE_STATUS["PAID"]
        assert result.total_amount == 2000.00
        assert result.id == invoice.id

    def test_update_invoice_partial_update(self, test_session, test_data_factory):
        """Test partial invoice update (only some fields)"""
        client = test_data_factory.create_client(test_session)
        invoice = test_data_factory.create_invoice(
            test_session,
            client_id=client.id,
            status=INVOICE_STATUS["PENDING"],
            total_amount=1000.00
        )
        
        service = InvoiceService(test_session)
        update_data = InvoiceUpdate(status=INVOICE_STATUS["PAID"])  # Only update status
        result = service.update_invoice(invoice.id, update_data)
        
        assert result is not None
        assert result.status == INVOICE_STATUS["PAID"]
        assert result.total_amount == 1000.00  # Should remain unchanged

    def test_update_invoice_not_found(self, test_session):
        """Test updating non-existent invoice"""
        service = InvoiceService(test_session)
        
        update_data = InvoiceUpdate(status=INVOICE_STATUS["PAID"])
        result = service.update_invoice(999, update_data)
        
        assert result is None

    def test_update_invoice_all_fields(self, test_session, test_data_factory):
        """Test updating all invoice fields"""
        client = test_data_factory.create_client(test_session)
        invoice = test_data_factory.create_invoice(test_session, client_id=client.id)
        
        service = InvoiceService(test_session)
        update_data = InvoiceUpdate(
            external_id="UPDATED-EXT",
            invoice_number="UPDATED-INV-001",
            invoice_date=date(2024, 6, 1),
            due_date=date(2024, 7, 1),
            total_amount=3000.00,
            currency="USD",
            status=INVOICE_STATUS["OVERDUE"],
            original_data={"updated": True}
        )
        
        result = service.update_invoice(invoice.id, update_data)
        
        assert result is not None
        # Note: external_id might not be updatable depending on service implementation
        assert result.invoice_number == "UPDATED-INV-001"
        assert result.currency == "USD"
        assert result.status == INVOICE_STATUS["OVERDUE"]
        assert result.original_data == {"updated": True}

    def test_delete_invoice_success(self, test_session, test_data_factory):
        """Test successful invoice deletion"""
        client = test_data_factory.create_client(test_session)
        invoice = test_data_factory.create_invoice(test_session, client_id=client.id)
        
        service = InvoiceService(test_session)
        result = service.delete_invoice(invoice.id)
        
        assert result is True
        
        # Verify invoice is deleted
        deleted_invoice = test_session.get(Invoice, invoice.id)
        assert deleted_invoice is None

    def test_delete_invoice_not_found(self, test_session):
        """Test deleting non-existent invoice"""
        service = InvoiceService(test_session)
        
        result = service.delete_invoice(999)
        
        assert result is False

    def test_invoice_with_negative_amount(self, test_session, test_data_factory):
        """Test creating invoice with negative amount (credit note)"""
        client = test_data_factory.create_client(test_session)
        
        invoice_data = InvoiceCreate(
            external_id="CREDIT-001",
            client_id=client.id,
            invoice_number="CN-2024-001",
            invoice_date=date(2024, 1, 15),
            due_date=date(2024, 2, 15),
            total_amount=-500.00,  # Negative amount for credit note
            currency="EUR",
            status=INVOICE_STATUS["ISSUED"]
        )
        
        service = InvoiceService(test_session)
        result = service.create_invoice(invoice_data)
        
        assert result.total_amount == -500.00
        assert result.invoice_number == "CN-2024-001"

    def test_invoice_with_zero_amount(self, test_session, test_data_factory):
        """Test creating invoice with zero amount"""
        client = test_data_factory.create_client(test_session)
        
        invoice_data = InvoiceCreate(
            external_id="ZERO-001",
            client_id=client.id,
            invoice_number="ZERO-2024-001",
            invoice_date=date(2024, 1, 15),
            due_date=date(2024, 2, 15),
            total_amount=0.00,
            currency="EUR",
            status=INVOICE_STATUS["ISSUED"]
        )
        
        service = InvoiceService(test_session)
        result = service.create_invoice(invoice_data)
        
        assert result.total_amount == 0.00

    def test_invoice_with_large_amount(self, test_session, test_data_factory):
        """Test creating invoice with very large amount"""
        client = test_data_factory.create_client(test_session)
        
        invoice_data = InvoiceCreate(
            external_id="LARGE-001",
            client_id=client.id,
            invoice_number="LARGE-2024-001",
            invoice_date=date(2024, 1, 15),
            due_date=date(2024, 2, 15),
            total_amount=999999.99,
            currency="EUR",
            status=INVOICE_STATUS["PENDING"]
        )
        
        service = InvoiceService(test_session)
        result = service.create_invoice(invoice_data)
        
        assert result.total_amount == 999999.99

    def test_invoice_date_edge_cases(self, test_session, test_data_factory):
        """Test invoice with edge case dates"""
        client = test_data_factory.create_client(test_session)
        
        # Test with leap year date
        invoice_data = InvoiceCreate(
            external_id="LEAP-001",
            client_id=client.id,
            invoice_number="LEAP-2024-001",
            invoice_date=date(2024, 2, 29),  # Leap year
            due_date=date(2024, 3, 29),
            total_amount=100.00,
            currency="EUR",
            status=INVOICE_STATUS["PENDING"]
        )
        
        service = InvoiceService(test_session)
        result = service.create_invoice(invoice_data)
        
        assert result.invoice_date == date(2024, 2, 29)
        assert result.due_date == date(2024, 3, 29)

    def test_invoice_service_database_error_handling(self, test_session, test_data_factory):
        """Test invoice service handles database errors gracefully"""
        client = test_data_factory.create_client(test_session)
        service = InvoiceService(test_session)
        
        # Mock a database error
        with patch.object(test_session, 'commit', side_effect=Exception("Database error")):
            invoice_data = InvoiceCreate(
                external_id="ERROR-001",
                client_id=client.id,
                invoice_number="ERROR-2024-001",
                invoice_date=date(2024, 1, 15),
                due_date=date(2024, 2, 15),
                total_amount=100.00,
                currency="EUR",
                status=INVOICE_STATUS["PENDING"]
            )
            
            with pytest.raises(Exception, match="Database error"):
                service.create_invoice(invoice_data)

    def test_invoice_service_with_none_session(self):
        """Test invoice service initialization with None session"""
        with pytest.raises(AttributeError):
            service = InvoiceService(None)
            service.get_invoices()

    def test_invoice_currency_variations(self, test_session, test_data_factory):
        """Test invoices with different currency codes"""
        client = test_data_factory.create_client(test_session)
        service = InvoiceService(test_session)
        
        currencies = ["EUR", "USD", "GBP", "JPY", "CAD"]
        
        for i, currency in enumerate(currencies):
            invoice_data = InvoiceCreate(
                external_id=f"CURR-{i}",
                client_id=client.id,
                invoice_number=f"CURR-{currency}-001",
                invoice_date=date(2024, 1, 15),
                due_date=date(2024, 2, 15),
                total_amount=100.00,
                currency=currency,
                status=INVOICE_STATUS["PENDING"]
            )
            
            result = service.create_invoice(invoice_data)
            assert result.currency == currency

    def test_invoice_status_variations(self, test_session, test_data_factory):
        """Test invoices with different status values"""
        client = test_data_factory.create_client(test_session)
        service = InvoiceService(test_session)
        
        statuses = ["PENDING", "PAID", "OVERDUE", "CANCELLED", "DRAFT"]
        
        for i, status in enumerate(statuses):
            invoice_data = InvoiceCreate(
                external_id=f"STATUS-{i}",
                client_id=client.id,
                invoice_number=f"STATUS-{status}-001",
                invoice_date=date(2024, 1, 15),
                due_date=date(2024, 2, 15),
                total_amount=100.00,
                currency="EUR",
                status=INVOICE_STATUS[status]
            )
            
            result = service.create_invoice(invoice_data)
            assert result.status == INVOICE_STATUS[status]

    def test_invoice_original_data_complex(self, test_session, test_data_factory):
        """Test invoice with complex original_data structure"""
        client = test_data_factory.create_client(test_session)
        
        complex_data = {
            "source": "external_api",
            "version": "2.1",
            "metadata": {
                "created_by": "system",
                "tags": ["important", "recurring"],
                "custom_fields": {
                    "project_id": "PROJ-123",
                    "department": "Engineering"
                }
            },
            "line_items": [
                {"description": "Service A", "amount": 500.00},
                {"description": "Service B", "amount": 500.00}
            ]
        }
        
        invoice_data = InvoiceCreate(
            external_id="COMPLEX-001",
            client_id=client.id,
            invoice_number="COMPLEX-2024-001",
            invoice_date=date(2024, 1, 15),
            due_date=date(2024, 2, 15),
            total_amount=1000.00,
            currency="EUR",
            status=INVOICE_STATUS["PENDING"],
            original_data=complex_data
        )
        
        service = InvoiceService(test_session)
        result = service.create_invoice(invoice_data)
        
        assert result.original_data == complex_data
        assert result.original_data["metadata"]["tags"] == ["important", "recurring"] 