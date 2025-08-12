import pytest
from datetime import datetime
from sqlmodel import Session, create_engine
from sqlalchemy.pool import StaticPool
from src.api.integrations.models.integration_error import IntegrationError
from src.api.integrations.services.integration_error_service import IntegrationErrorService
from src.api.integrations.schemas.integration_error import (
    IntegrationErrorCreate,
    IntegrationErrorUpdate,
    IntegrationErrorFilter,
    IntegrationErrorSummary
)
from src.api.clients.models.client import Client
from src.api.services.models.service_contract import ServiceContract
from src.api.services.models.service import Service


@pytest.fixture
def service(test_session):
    """Create an integration error service for testing"""
    return IntegrationErrorService(test_session)


@pytest.fixture
def sample_client(test_session):
    """Create a sample client for testing"""
    client = Client(
        name="Test Client",
        encrypted_identifier="test@example.com"
    )
    test_session.add(client)
    test_session.commit()
    test_session.refresh(client)
    return client


@pytest.fixture
def sample_service(test_session):
    """Create a sample service for testing"""
    service = Service(
        name="Test Service",
        description="Test service description"
    )
    test_session.add(service)
    test_session.commit()
    test_session.refresh(service)
    return service


@pytest.fixture
def sample_contract(test_session, sample_client, sample_service):
    """Create a sample service contract for testing"""
    contract = ServiceContract(
        service_id=sample_service.id,
        client_id=sample_client.id,
        contract_date=datetime.now().date(),
        contract_amount=1000.0
    )
    test_session.add(contract)
    test_session.commit()
    test_session.refresh(contract)
    return contract


@pytest.fixture
def sample_error_data():
    """Sample error data for testing"""
    return {
        "integration_name": "test_integration",
        "operation_type": "test_operation",
        "external_id": "test_external_id",
        "entity_type": "test_entity",
        "error_message": "Test error message",
        "error_details": {"test": "details"},
        "client_id": None,
        "contract_id": None
    }


class TestIntegrationErrorService:
    """Test the IntegrationErrorService class"""

    def test_create_error_success(self, service, sample_error_data):
        """Test creating a new integration error"""
        error_data = IntegrationErrorCreate(**sample_error_data)
        error = service.create_error(error_data)
        
        assert error.id is not None
        assert error.integration_name == sample_error_data["integration_name"]
        assert error.operation_type == sample_error_data["operation_type"]
        assert error.external_id == sample_error_data["external_id"]
        assert error.entity_type == sample_error_data["entity_type"]
        assert error.error_message == sample_error_data["error_message"]
        assert error.error_details == sample_error_data["error_details"]
        assert error.is_resolved is False
        assert error.created_at is not None
        assert error.updated_at is not None

    def test_create_error_with_relationships(self, service, sample_client, sample_contract):
        """Test creating an error with client and contract relationships"""
        error_data = IntegrationErrorCreate(
            integration_name="test_integration",
            operation_type="test_operation",
            external_id="test_external_id",
            entity_type="test_entity",
            error_message="Test error message",
            client_id=sample_client.id,
            contract_id=sample_contract.id
        )
        
        error = service.create_error(error_data)
        
        assert error.client_id == sample_client.id
        assert error.contract_id == sample_contract.id

    def test_create_error_duplicate_prevention(self, service, sample_error_data):
        """Test that duplicate errors are prevented"""
        error_data = IntegrationErrorCreate(**sample_error_data)
        
        # Create first error
        error1 = service.create_error(error_data)
        assert error1.id is not None
        
        # Try to create duplicate
        error2 = service.create_error(error_data)
        
        # Should return the existing error
        assert error2.id == error1.id
        assert error2.integration_name == error1.integration_name

    def test_create_error_update_existing_unresolved(self, service, sample_error_data):
        """Test that existing unresolved errors are updated"""
        error_data = IntegrationErrorCreate(**sample_error_data)
        
        # Create first error
        error1 = service.create_error(error_data)
        original_id = error1.id
        
        # Update error data
        updated_error_data = IntegrationErrorCreate(
            **{**sample_error_data, "error_message": "Updated error message"}
        )
        
        # Create/update error
        error2 = service.create_error(updated_error_data)
        
        # Should be the same error with updated message
        assert error2.id == original_id
        assert error2.error_message == "Updated error message"
        assert error2.updated_at >= error1.updated_at

    def test_get_error_success(self, service, sample_error_data):
        """Test getting an error by ID"""
        error_data = IntegrationErrorCreate(**sample_error_data)
        created_error = service.create_error(error_data)
        
        retrieved_error = service.get_error(created_error.id)
        
        assert retrieved_error is not None
        assert retrieved_error.id == created_error.id
        assert retrieved_error.integration_name == created_error.integration_name

    def test_get_error_not_found(self, service):
        """Test getting a non-existent error"""
        error = service.get_error(999)
        assert error is None

    def test_get_errors_with_filters(self, service, sample_error_data):
        """Test getting errors with filters"""
        # Create multiple errors
        error1_data = IntegrationErrorCreate(**sample_error_data)
        error2_data = IntegrationErrorCreate(
            **{**sample_error_data, "integration_name": "other_integration"}
        )
        
        service.create_error(error1_data)
        service.create_error(error2_data)
        
        # Filter by integration name
        filters = IntegrationErrorFilter(integration_name="test_integration")
        errors = service.get_errors(filters)
        
        assert len(errors) == 1
        assert errors[0].integration_name == "test_integration"

    def test_get_errors_pagination(self, service, sample_error_data):
        """Test pagination for getting errors"""
        # Create multiple errors
        for i in range(5):
            error_data = IntegrationErrorCreate(
                **{**sample_error_data, "external_id": f"test_id_{i}"}
            )
            service.create_error(error_data)
        
        # Test pagination
        filters = IntegrationErrorFilter(limit=3, offset=0)
        errors = service.get_errors(filters)
        
        assert len(errors) == 3
        
        filters = IntegrationErrorFilter(limit=3, offset=3)
        errors = service.get_errors(filters)
        
        assert len(errors) == 2

    def test_update_error_success(self, service, sample_error_data):
        """Test updating an error"""
        error_data = IntegrationErrorCreate(**sample_error_data)
        error = service.create_error(error_data)
        
        update_data = IntegrationErrorUpdate(
            is_resolved=True,
            resolution_notes="Error was resolved"
        )
        
        updated_error = service.update_error(error.id, update_data)
        
        assert updated_error is not None
        assert updated_error.is_resolved is True
        assert updated_error.resolution_notes == "Error was resolved"
        assert updated_error.resolved_at is not None
        assert updated_error.updated_at >= error.updated_at

    def test_update_error_not_found(self, service):
        """Test updating a non-existent error"""
        update_data = IntegrationErrorUpdate(is_resolved=True)
        result = service.update_error(999, update_data)
        assert result is None

    def test_delete_error_success(self, service, sample_error_data):
        """Test deleting an error"""
        error_data = IntegrationErrorCreate(**sample_error_data)
        error = service.create_error(error_data)
        
        success = service.delete_error(error.id)
        assert success is True
        
        # Verify error is deleted
        retrieved_error = service.get_error(error.id)
        assert retrieved_error is None

    def test_delete_error_not_found(self, service):
        """Test deleting a non-existent error"""
        success = service.delete_error(999)
        assert success is False

    def test_resolve_error_success(self, service, sample_error_data):
        """Test resolving an error"""
        error_data = IntegrationErrorCreate(**sample_error_data)
        error = service.create_error(error_data)
        
        resolved_error = service.resolve_error(error.id, "Error resolved")
        
        assert resolved_error is not None
        assert resolved_error.is_resolved is True
        assert resolved_error.resolution_notes == "Error resolved"
        assert resolved_error.resolved_at is not None

    def test_bulk_resolve_errors(self, service, sample_error_data):
        """Test bulk resolving errors"""
        # Create multiple errors
        errors = []
        for i in range(3):
            error_data = IntegrationErrorCreate(
                **{**sample_error_data, "external_id": f"test_id_{i}"}
            )
            error = service.create_error(error_data)
            errors.append(error)
        
        error_ids = [error.id for error in errors]
        resolved_count = service.bulk_resolve_errors(error_ids, "Bulk resolved")
        
        assert resolved_count == 3
        
        # Verify all errors are resolved
        for error_id in error_ids:
            error = service.get_error(error_id)
            assert error.is_resolved is True
            assert error.resolution_notes == "Bulk resolved"

    def test_get_summary(self, service, sample_error_data):
        """Test getting error summary"""
        # Create errors with different statuses
        error1_data = IntegrationErrorCreate(**sample_error_data)
        error2_data = IntegrationErrorCreate(
            **{**sample_error_data, "external_id": "test_id_2"}
        )
        error3_data = IntegrationErrorCreate(
            **{**sample_error_data, "external_id": "test_id_3", "integration_name": "other_integration"}
        )
        
        service.create_error(error1_data)
        service.create_error(error2_data)
        service.create_error(error3_data)
        
        # Resolve one error
        service.resolve_error(1, "Resolved")
        
        summary = service.get_summary()
        
        assert summary.total_errors == 3
        assert summary.resolved_errors == 1
        assert summary.unresolved_errors == 2
        assert summary.errors_by_integration["test_integration"] == 2
        assert summary.errors_by_integration["other_integration"] == 1
        assert summary.errors_by_operation["test_operation"] == 3
        assert summary.errors_by_entity_type["test_entity"] == 3


class TestIntegrationErrorUniqueness:
    """Test the uniqueness constraints of integration errors"""

    def test_unique_constraint_same_entity(self, service, sample_error_data):
        """Test that errors for the same entity are unique"""
        error_data = IntegrationErrorCreate(**sample_error_data)
        
        # Create first error
        error1 = service.create_error(error_data)
        
        # Try to create error with same entity details
        error2 = service.create_error(error_data)
        
        # Should return existing error
        assert error2.id == error1.id

    def test_unique_constraint_different_entities(self, service, sample_error_data):
        """Test that errors for different entities can coexist"""
        error1_data = IntegrationErrorCreate(**sample_error_data)
        error2_data = IntegrationErrorCreate(
            **{**sample_error_data, "external_id": "different_id"}
        )
        
        error1 = service.create_error(error1_data)
        error2 = service.create_error(error2_data)
        
        assert error1.id != error2.id

    def test_unique_constraint_with_relationships(self, service, sample_client, sample_contract):
        """Test uniqueness with client and contract relationships"""
        error1_data = IntegrationErrorCreate(
            integration_name="test_integration",
            operation_type="test_operation",
            external_id="test_external_id",
            entity_type="test_entity",
            error_message="Test error message",
            client_id=sample_client.id,
            contract_id=sample_contract.id
        )
        
        error2_data = IntegrationErrorCreate(
            integration_name="test_integration",
            operation_type="test_operation",
            external_id="test_external_id",
            entity_type="test_entity",
            error_message="Test error message",
            client_id=sample_client.id,
            contract_id=sample_contract.id
        )
        
        error1 = service.create_error(error1_data)
        error2 = service.create_error(error2_data)
        
        # Should return existing error
        assert error2.id == error1.id
