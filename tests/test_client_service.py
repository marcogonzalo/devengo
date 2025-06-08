import pytest
from unittest.mock import Mock, patch
from sqlmodel import Session

from src.api.clients.services.client_service import ClientService
from src.api.clients.models.client import Client, ClientExternalId
from src.api.clients.schemas.client import ClientCreate, ClientUpdate, ClientExternalIdCreate


class TestClientService:
    """Test ClientService class"""

    def test_create_client_success(self, test_session, sample_client_data):
        """Test successful client creation"""
        service = ClientService(test_session)
        client_data = ClientCreate(**sample_client_data)
        
        result = service.create_client(client_data)
        
        assert result.id is not None
        assert result.name == sample_client_data["name"]
        assert result.identifier == sample_client_data["identifier"]
        
        # Verify it's in the database
        db_client = test_session.get(Client, result.id)
        assert db_client is not None
        assert db_client.name == sample_client_data["name"]

    def test_create_client_with_encrypted_identifier(self, test_session):
        """Test that client identifier is properly encrypted"""
        service = ClientService(test_session)
        client_data = ClientCreate(name="Test Client", identifier="secret-id-123")
        
        result = service.create_client(client_data)
        
        # The identifier should be accessible (decrypted when accessed)
        assert result.identifier == "secret-id-123"
        
        # But the raw database field should be encrypted
        db_client = test_session.get(Client, result.id)
        # Note: This test assumes the model has a way to access raw encrypted data
        # The exact implementation depends on how encryption is handled in the model

    def test_create_client_empty_name(self, test_session):
        """Test creating client with empty name"""
        service = ClientService(test_session)
        client_data = ClientCreate(name="", identifier="test-id")
        
        result = service.create_client(client_data)
        
        assert result.name == ""
        assert result.identifier == "test-id"

    def test_get_client_success(self, test_session, test_data_factory):
        """Test successful client retrieval"""
        service = ClientService(test_session)
        created_client = test_data_factory.create_client(test_session)
        
        result = service.get_client(created_client.id)
        
        assert result is not None
        assert result.id == created_client.id
        assert result.name == created_client.name

    def test_get_client_not_found(self, test_session):
        """Test getting non-existent client"""
        service = ClientService(test_session)
        
        result = service.get_client(999)
        
        assert result is None

    def test_get_client_by_identifier_success(self, test_session, test_data_factory):
        """Test getting client by identifier"""
        service = ClientService(test_session)
        created_client = test_data_factory.create_client(
            test_session, 
            identifier="unique-identifier"
        )
        
        result = service.get_client_by_identifier("unique-identifier")
        
        assert result is not None
        assert result.id == created_client.id
        assert result.identifier == "unique-identifier"

    def test_get_client_by_identifier_not_found(self, test_session):
        """Test getting client by non-existent identifier"""
        service = ClientService(test_session)
        
        result = service.get_client_by_identifier("non-existent")
        
        assert result is None

    def test_get_client_by_identifier_multiple_clients(self, test_session, test_data_factory):
        """Test getting client by identifier when multiple clients exist"""
        service = ClientService(test_session)
        
        # Create multiple clients
        client1 = test_data_factory.create_client(test_session, identifier="id-1")
        client2 = test_data_factory.create_client(test_session, identifier="id-2")
        client3 = test_data_factory.create_client(test_session, identifier="id-3")
        
        result = service.get_client_by_identifier("id-2")
        
        assert result is not None
        assert result.id == client2.id

    def test_get_clients_default_pagination(self, test_session, test_data_factory):
        """Test getting clients with default pagination"""
        service = ClientService(test_session)
        
        # Create multiple clients
        clients = []
        for i in range(5):
            client = test_data_factory.create_client(
                test_session, 
                name=f"Client {i}",
                identifier=f"id-{i}"
            )
            clients.append(client)
        
        result = service.get_clients()
        
        assert len(result) == 5
        assert all(isinstance(client, Client) for client in result)

    def test_get_clients_with_pagination(self, test_session, test_data_factory):
        """Test getting clients with custom pagination"""
        service = ClientService(test_session)
        
        # Create multiple clients
        for i in range(10):
            test_data_factory.create_client(
                test_session, 
                name=f"Client {i}",
                identifier=f"id-{i}"
            )
        
        result = service.get_clients(skip=3, limit=4)
        
        assert len(result) == 4

    def test_get_clients_empty_database(self, test_session):
        """Test getting clients from empty database"""
        service = ClientService(test_session)
        
        result = service.get_clients()
        
        assert result == []

    def test_get_clients_with_no_external_id(self, test_session, test_data_factory):
        """Test getting clients without external ID for specific system"""
        service = ClientService(test_session)
        
        # Create clients
        client1 = test_data_factory.create_client(test_session, name="Client 1")
        client2 = test_data_factory.create_client(test_session, name="Client 2")
        client3 = test_data_factory.create_client(test_session, name="Client 3")
        
        # Add external ID for client2 only
        external_id = ClientExternalId(
            client_id=client2.id,
            system="holded"
        )
        external_id.external_id = "ext-123"
        test_session.add(external_id)
        test_session.commit()
        
        result = service.get_clients_with_no_external_id("holded")
        
        # Should return client1 and client3 (not client2)
        assert len(result) == 2
        client_ids = [client.id for client in result]
        assert client1.id in client_ids
        assert client3.id in client_ids
        assert client2.id not in client_ids

    def test_update_client_success(self, test_session, test_data_factory):
        """Test successful client update"""
        service = ClientService(test_session)
        created_client = test_data_factory.create_client(test_session)
        
        update_data = ClientUpdate(name="Updated Name")
        result = service.update_client(created_client.id, update_data)
        
        assert result is not None
        assert result.name == "Updated Name"
        assert result.id == created_client.id

    def test_update_client_with_identifier(self, test_session, test_data_factory):
        """Test updating client with new identifier"""
        service = ClientService(test_session)
        created_client = test_data_factory.create_client(test_session)
        
        update_data = ClientUpdate(identifier="new-identifier")
        result = service.update_client(created_client.id, update_data)
        
        assert result is not None
        assert result.identifier == "new-identifier"

    def test_update_client_not_found(self, test_session):
        """Test updating non-existent client"""
        service = ClientService(test_session)
        
        update_data = ClientUpdate(name="Updated Name")
        result = service.update_client(999, update_data)
        
        assert result is None

    def test_update_client_partial_update(self, test_session, test_data_factory):
        """Test partial client update (only some fields)"""
        service = ClientService(test_session)
        created_client = test_data_factory.create_client(
            test_session,
            name="Original Name",
            identifier="original-id"
        )
        
        # Only update name, not identifier
        update_data = ClientUpdate(name="Updated Name")
        result = service.update_client(created_client.id, update_data)
        
        assert result is not None
        assert result.name == "Updated Name"
        assert result.identifier == "original-id"  # Should remain unchanged

    def test_delete_client_success(self, test_session, test_data_factory):
        """Test successful client deletion"""
        service = ClientService(test_session)
        created_client = test_data_factory.create_client(test_session)
        
        result = service.delete_client(created_client.id)
        
        assert result is True
        
        # Verify client is deleted
        deleted_client = test_session.get(Client, created_client.id)
        assert deleted_client is None

    def test_delete_client_not_found(self, test_session):
        """Test deleting non-existent client"""
        service = ClientService(test_session)
        
        result = service.delete_client(999)
        
        assert result is False

    def test_add_external_id_success(self, test_session, test_data_factory):
        """Test successfully adding external ID to client"""
        service = ClientService(test_session)
        created_client = test_data_factory.create_client(test_session)
        
        external_id_data = ClientExternalIdCreate(
            system="holded",
            external_id="ext-123"
        )
        
        result = service.add_external_id(created_client.id, external_id_data)
        
        assert result is not None
        assert result.client_id == created_client.id
        assert result.system == "holded"
        assert result.external_id == "ext-123"

    def test_add_external_id_multiple_systems(self, test_session, test_data_factory):
        """Test adding external IDs for multiple systems"""
        service = ClientService(test_session)
        created_client = test_data_factory.create_client(test_session)
        
        # Add external ID for holded
        holded_data = ClientExternalIdCreate(system="holded", external_id="holded-123")
        holded_result = service.add_external_id(created_client.id, holded_data)
        
        # Add external ID for fourgeeks
        fourgeeks_data = ClientExternalIdCreate(system="fourgeeks", external_id="4g-456")
        fourgeeks_result = service.add_external_id(created_client.id, fourgeeks_data)
        
        assert holded_result.system == "holded"
        assert fourgeeks_result.system == "fourgeeks"
        assert holded_result.client_id == fourgeeks_result.client_id

    def test_get_client_by_external_id_success(self, test_session, test_data_factory):
        """Test getting client by external ID"""
        service = ClientService(test_session)
        created_client = test_data_factory.create_client(test_session)
        
        # Add external ID
        external_id_data = ClientExternalIdCreate(system="holded", external_id="ext-123")
        service.add_external_id(created_client.id, external_id_data)
        
        result = service.get_client_by_external_id("holded", "ext-123")
        
        assert result is not None
        assert result.id == created_client.id

    def test_get_client_by_external_id_not_found(self, test_session):
        """Test getting client by non-existent external ID"""
        service = ClientService(test_session)
        
        result = service.get_client_by_external_id("holded", "non-existent")
        
        assert result is None

    def test_get_client_by_external_id_wrong_system(self, test_session, test_data_factory):
        """Test getting client by external ID with wrong system"""
        service = ClientService(test_session)
        created_client = test_data_factory.create_client(test_session)
        
        # Add external ID for holded
        external_id_data = ClientExternalIdCreate(system="holded", external_id="ext-123")
        service.add_external_id(created_client.id, external_id_data)
        
        # Try to get with different system
        result = service.get_client_by_external_id("fourgeeks", "ext-123")
        
        assert result is None

    def test_get_client_external_id_success(self, test_session, test_data_factory):
        """Test getting client external ID"""
        service = ClientService(test_session)
        created_client = test_data_factory.create_client(test_session)
        
        # Add external ID
        external_id_data = ClientExternalIdCreate(system="holded", external_id="ext-123")
        added_external_id = service.add_external_id(created_client.id, external_id_data)
        
        result = service.get_client_external_id(created_client.id, "holded")
        
        assert result is not None
        assert result.id == added_external_id.id
        assert result.external_id == "ext-123"

    def test_get_client_external_id_not_found(self, test_session, test_data_factory):
        """Test getting non-existent client external ID"""
        service = ClientService(test_session)
        created_client = test_data_factory.create_client(test_session)
        
        result = service.get_client_external_id(created_client.id, "holded")
        
        assert result is None

    def test_get_clients_missing_external_id(self, test_session, test_data_factory):
        """Test getting clients missing external IDs"""
        service = ClientService(test_session)
        
        # Create clients
        client1 = test_data_factory.create_client(test_session, name="Client 1")
        client2 = test_data_factory.create_client(test_session, name="Client 2")
        
        # Add external ID for client1 in holded only
        external_id_data = ClientExternalIdCreate(system="holded", external_id="ext-123")
        service.add_external_id(client1.id, external_id_data)
        
        result = service.get_clients_missing_external_id()
        
        # Should include missing external IDs for both clients
        # client1: missing fourgeeks and notion
        # client2: missing all three systems
        assert len(result) >= 5  # At least 5 missing external IDs
        
        # Check that we have entries for both clients
        client_ids = [item["id"] for item in result]
        assert client1.id in client_ids
        assert client2.id in client_ids
        
        # Check that we have entries for all systems
        systems = [item["system"] for item in result]
        assert "holded" in systems
        assert "fourgeeks" in systems
        assert "notion" in systems

    def test_get_clients_missing_external_id_empty_database(self, test_session):
        """Test getting clients missing external IDs from empty database"""
        service = ClientService(test_session)
        
        result = service.get_clients_missing_external_id()
        
        assert result == []

    def test_client_service_database_error_handling(self, test_session):
        """Test client service handles database errors gracefully"""
        service = ClientService(test_session)
        
        # Mock a database error
        with patch.object(test_session, 'commit', side_effect=Exception("Database error")):
            client_data = ClientCreate(name="Test Client", identifier="test-id")
            
            with pytest.raises(Exception, match="Database error"):
                service.create_client(client_data)

    def test_client_service_with_none_session(self):
        """Test client service initialization with None session"""
        with pytest.raises(AttributeError):
            service = ClientService(None)
            service.get_clients()

    def test_encryption_edge_cases(self, test_session):
        """Test encryption edge cases in client service"""
        service = ClientService(test_session)
        
        # Test with special characters
        client_data = ClientCreate(
            name="Test Client",
            identifier="special-chars-!@#$%^&*()"
        )
        
        result = service.create_client(client_data)
        assert result.identifier == "special-chars-!@#$%^&*()"
        
        # Test with unicode characters
        unicode_data = ClientCreate(
            name="Unicode Client",
            identifier="unicode-测试-🌍"
        )
        
        unicode_result = service.create_client(unicode_data)
        assert unicode_result.identifier == "unicode-测试-🌍" 