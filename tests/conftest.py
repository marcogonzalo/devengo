import pytest
import os
from datetime import date, datetime, timezone
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool
from unittest.mock import Mock, patch
from cryptography.fernet import Fernet

# Import all models to ensure they're registered with SQLModel
from src.api.clients.models.client import Client, ClientExternalId
from src.api.invoices.models.invoice import Invoice
from src.api.services.models.service import Service
from src.api.services.models.service_period import ServicePeriod
from src.api.services.models.service_contract import ServiceContract
from src.api.accruals.models.accrued_period import AccruedPeriod


@pytest.fixture(scope="session")
def test_encryption_key():
    """Provide a test encryption key for testing encrypted fields"""
    return Fernet.generate_key().decode()


@pytest.fixture(scope="session", autouse=True)
def setup_test_env(test_encryption_key):
    """Setup test environment variables"""
    os.environ["ENCRYPTION_KEY"] = test_encryption_key
    os.environ["ENV"] = "test"
    yield
    # Cleanup
    if "ENCRYPTION_KEY" in os.environ:
        del os.environ["ENCRYPTION_KEY"]
    if "ENV" in os.environ:
        del os.environ["ENV"]


@pytest.fixture
def test_engine():
    """Create an in-memory SQLite database for testing"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def test_session(test_engine):
    """Create a test database session"""
    with Session(test_engine) as session:
        yield session


@pytest.fixture
def sample_client_data():
    """Sample client data for testing"""
    return {
        "name": "Test Client",
        "identifier": "test-client-123"
    }


@pytest.fixture
def sample_invoice_data():
    """Sample invoice data for testing"""
    return {
        "external_id": "INV-001",
        "client_id": 1,
        "invoice_number": "2024-001",
        "invoice_date": date(2024, 1, 15),
        "due_date": date(2024, 2, 15),
        "total_amount": 1000.00,
        "currency": "EUR",
        "status": 1,  # PENDING
        "original_data": {"source": "test"}
    }


@pytest.fixture
def sample_service_data():
    """Sample service data for testing"""
    return {
        "name": "Development Service",
        "description": "Software development services",
        "external_id": "DEV-001",
        "total_sessions": 60,
        "sessions_per_week": 3
    }


@pytest.fixture
def sample_service_period_data():
    """Sample service period data for testing"""
    return {
        "contract_id": 1,  # Will be overridden in tests
        "start_date": date(2024, 1, 1),
        "end_date": date(2024, 1, 31),
        "status": "ENDED"
    }


@pytest.fixture
def sample_service_contract_data():
    """Sample service contract data for testing"""
    return {
        "client_id": 1,
        "service_id": 1,
        "contract_date": date(2024, 1, 1),
        "contract_amount": 5000.00,
        "status": "ACTIVE"
    }


@pytest.fixture
def mock_datetime():
    """Mock datetime for consistent testing"""
    fixed_datetime = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    with patch('src.api.common.utils.datetime.datetime') as mock_dt:
        mock_dt.now.return_value = fixed_datetime
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        yield mock_dt


@pytest.fixture
def mock_notion_client():
    """Mock Notion client for testing integrations"""
    with patch('src.api.integrations.notion.client.NotionClient') as mock_client:
        mock_instance = Mock()
        mock_client.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_holded_client():
    """Mock Holded client for testing integrations"""
    with patch('src.api.integrations.holded.client.HoldedClient') as mock_client:
        mock_instance = Mock()
        mock_client.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_fourgeeks_client():
    """Mock 4Geeks client for testing integrations"""
    with patch('src.api.integrations.fourgeeks.client.FourGeeksClient') as mock_client:
        mock_instance = Mock()
        mock_client.return_value = mock_instance
        yield mock_instance


# Test data factories
class TestDataFactory:
    @staticmethod
    def create_client(session: Session, **kwargs) -> Client:
        """Create a test client"""
        data = {
            "name": "Test Client",
            "identifier": "test-client-123"
        }
        data.update(kwargs)
        
        client = Client(name=data["name"])
        client.identifier = data["identifier"]
        session.add(client)
        session.commit()
        session.refresh(client)
        return client

    @staticmethod
    def create_invoice(session: Session, client_id: int = None, service_contract_id: int = None, **kwargs) -> Invoice:
        """Create a test invoice"""
        if client_id is None:
            client = TestDataFactory.create_client(session)
            client_id = client.id
            
        data = {
            "external_id": "INV-001",
            "client_id": client_id,
            "service_contract_id": service_contract_id,
            "invoice_number": "2024-001",
            "invoice_date": date(2024, 1, 15),
            "due_date": date(2024, 2, 15),
            "total_amount": 1000.00,
            "currency": "EUR",
            "status": 1,  # PENDING
            "original_data": {"source": "test"}
        }
        data.update(kwargs)
        
        invoice = Invoice(**data)
        session.add(invoice)
        session.commit()
        session.refresh(invoice)
        return invoice

    @staticmethod
    def create_service(session: Session, **kwargs) -> Service:
        """Create a test service"""
        data = {
            "name": "Development Service",
            "description": "Software development services",
            "external_id": "DEV-001",
            "total_sessions": 60,
            "sessions_per_week": 3
        }
        data.update(kwargs)
        
        service = Service(**data)
        session.add(service)
        session.commit()
        session.refresh(service)
        return service


@pytest.fixture
def test_data_factory():
    """Provide test data factory"""
    return TestDataFactory 