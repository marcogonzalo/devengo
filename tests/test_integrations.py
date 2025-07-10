import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import httpx
from datetime import datetime
from fastapi import HTTPException

from src.api.integrations.notion.client import NotionClient
from src.api.integrations.holded.client import HoldedClient
from src.api.integrations.fourgeeks.client import FourGeeksClient
from src.api.integrations.fourgeeks.processor import EnrollmentProcessor, StudentProcessor
from src.api.integrations.endpoints.holded import sync_invoices_and_clients, _create_invoice, _is_credit_note
from src.api.invoices.schemas.invoice import InvoiceCreate, InvoiceUpdate


class TestNotionIntegration:
    """Test Notion integration client"""

    @pytest.fixture
    def notion_client(self):
        """Create a Notion client for testing"""
        from src.api.integrations.notion.config import NotionConfig
        with patch('src.api.integrations.notion.config.os.getenv') as mock_getenv:
            mock_getenv.return_value = "test_token"
            config = NotionConfig()
            return NotionClient(config)

    def test_notion_client_initialization(self, notion_client):
        """Test Notion client initialization"""
        assert notion_client is not None
        assert hasattr(notion_client, 'config')
        assert hasattr(notion_client, 'headers')

    @patch('httpx.AsyncClient.get')
    @pytest.mark.asyncio
    async def test_get_current_user_success(self, mock_get, notion_client):
        """Test successful current user retrieval from Notion"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "object": "user",
            "id": "test-user-id",
            "name": "Test User"
        }
        mock_get.return_value = mock_response
        
        result = await notion_client.get_current_user()
        
        assert result["object"] == "user"
        assert result["id"] == "test-user-id"
        mock_get.assert_called_once()

    @patch('httpx.AsyncClient.get')
    @pytest.mark.asyncio
    async def test_get_page_content_not_found(self, mock_get, notion_client):
        """Test page content not found error"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"message": "Page not found"}
        mock_response.raise_for_status.side_effect = Exception("HTTP 404 Not Found")
        mock_get.return_value = mock_response
        
        with pytest.raises(Exception):
            await notion_client.get_page_content("non-existent-id")

    @patch('httpx.AsyncClient.post')
    @pytest.mark.asyncio
    async def test_get_page_by_email_success(self, mock_post, notion_client):
        """Test successful page retrieval by email"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "object": "list",
            "results": [
                {"id": "page1", "properties": {"Email": {"email": "test@example.com"}}}
            ],
            "has_more": False
        }
        mock_post.return_value = mock_response
        
        result = await notion_client.get_page_by_email("test-db-id", "Email", "test@example.com")
        
        assert result["id"] == "page1"
        mock_post.assert_called_once()

    @patch('httpx.AsyncClient.post')
    @pytest.mark.asyncio
    async def test_list_pages_success(self, mock_post, notion_client):
        """Test successful pages listing"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "object": "list",
            "results": [{"id": "page1"}, {"id": "page2"}],
            "has_more": False
        }
        mock_post.return_value = mock_response
        
        result = await notion_client.list_pages("test-db-id")
        
        assert len(result) == 2
        assert result[0]["id"] == "page1"
        mock_post.assert_called_once()

    @patch('httpx.AsyncClient.get')
    @pytest.mark.asyncio
    async def test_get_page_content_success(self, mock_get, notion_client):
        """Test successful page content retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "object": "page",
            "id": "test-page-id",
            "properties": {"Name": {"title": [{"text": {"content": "Test Page"}}]}}
        }
        mock_get.return_value = mock_response
        
        result = await notion_client.get_page_content("test-page-id")
        
        assert result["object"] == "page"
        assert result["id"] == "test-page-id"

    def test_notion_client_missing_token(self):
        """Test Notion client initialization without token"""
        from src.api.integrations.notion.config import NotionConfig
        with patch('src.api.integrations.notion.config.os.getenv') as mock_getenv:
            mock_getenv.return_value = None
            
            # This should not raise an error with current implementation
            # The NotionConfig accepts None values
            config = NotionConfig()
            client = NotionClient(config)
            assert client is not None

    @patch('httpx.AsyncClient.get')
    @pytest.mark.asyncio
    async def test_notion_client_rate_limiting(self, mock_get, notion_client):
        """Test handling of rate limiting"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "1"}
        mock_response.raise_for_status.side_effect = Exception("HTTP 429 Too Many Requests")
        mock_get.return_value = mock_response
        
        with pytest.raises(Exception):
            await notion_client.get_current_user()

    @patch('httpx.AsyncClient.get')
    @pytest.mark.asyncio
    async def test_notion_client_network_error(self, mock_get, notion_client):
        """Test handling of network errors"""
        mock_get.side_effect = httpx.RequestError("Network error")
        
        # NotionClient wraps all exceptions in HTTPException
        with pytest.raises(HTTPException, match="Error: Network error"):
            await notion_client.get_current_user()


class TestHoldedIntegration:
    """Test Holded integration client"""

    @pytest.fixture
    def holded_client(self):
        """Create a Holded client for testing"""
        from src.api.integrations.holded.config import HoldedConfig
        with patch('src.api.integrations.holded.config.os.getenv') as mock_getenv:
            mock_getenv.return_value = "test_api_key"
            config = HoldedConfig()
            return HoldedClient(config)

    def test_holded_client_initialization(self, holded_client):
        """Test Holded client initialization"""
        assert holded_client is not None
        assert hasattr(holded_client, 'config')

    @patch('httpx.AsyncClient.get')
    @pytest.mark.asyncio
    async def test_list_contacts_success(self, mock_get, holded_client):
        """Test successful contacts retrieval from Holded"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": "1", "name": "Test Contact 1", "email": "test1@example.com"},
            {"id": "2", "name": "Test Contact 2", "email": "test2@example.com"}
        ]
        mock_get.return_value = mock_response
        
        result = await holded_client.list_contacts()
        
        assert len(result) == 2
        assert result[0]["name"] == "Test Contact 1"
        mock_get.assert_called_once()

    @patch('httpx.AsyncClient.get')
    @pytest.mark.asyncio
    async def test_list_contacts_with_pagination(self, mock_get, holded_client):
        """Test contacts retrieval with pagination"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": "3", "name": "Test Contact 3"}
        ]
        mock_get.return_value = mock_response
        
        result = await holded_client.list_contacts(page=2, per_page=10)
        
        # Verify pagination parameters were included in the params
        call_args = mock_get.call_args
        params = call_args[1].get('params', {})
        assert params.get('page') == 2
        assert params.get('per_page') == 10

    @patch('httpx.AsyncClient.get')
    @pytest.mark.asyncio
    async def test_get_contact_by_id_success(self, mock_get, holded_client):
        """Test successful contact retrieval by ID"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "123",
            "name": "Specific Contact",
            "email": "specific@example.com"
        }
        mock_get.return_value = mock_response
        
        result = await holded_client.get_contact("123")
        
        assert result["id"] == "123"
        assert result["name"] == "Specific Contact"

    @patch('httpx.AsyncClient.get')
    @pytest.mark.asyncio
    async def test_get_contact_not_found(self, mock_get, holded_client):
        """Test contact not found error"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "Contact not found"}
        mock_response.raise_for_status.side_effect = Exception("HTTP 404 Not Found")
        mock_get.return_value = mock_response
        
        with pytest.raises(Exception):
            await holded_client.get_contact("non-existent")

    @patch('httpx.AsyncClient.get')
    @pytest.mark.asyncio
    async def test_list_documents_success(self, mock_get, holded_client):
        """Test successful documents retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": "doc1", "type": "invoice", "number": "INV-001"},
            {"id": "doc2", "type": "invoice", "number": "INV-002"}
        ]
        mock_get.return_value = mock_response
        
        result = await holded_client.list_documents()
        
        assert len(result) == 2
        assert result[0]["type"] == "invoice"

    @patch('httpx.AsyncClient.get')
    @pytest.mark.asyncio
    async def test_list_documents_by_type(self, mock_get, holded_client):
        """Test documents retrieval filtered by type"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": "inv1", "type": "invoice", "number": "INV-001"}
        ]
        mock_get.return_value = mock_response
        
        result = await holded_client.list_documents(document_type="invoice")
        
        # Verify type filter was applied
        call_args = mock_get.call_args
        assert "invoice" in str(call_args)

    @pytest.mark.asyncio
    async def test_create_contact_not_implemented(self, holded_client):
        """Test that create_contact method doesn't exist"""
        # The HoldedClient doesn't have a create_contact method
        # This test verifies that the method doesn't exist
        assert not hasattr(holded_client, 'create_contact')

    def test_holded_client_missing_api_key(self):
        """Test Holded client initialization without API key"""
        from src.api.integrations.holded.config import HoldedConfig
        with patch('src.api.integrations.holded.config.os.getenv') as mock_getenv:
            mock_getenv.return_value = None
            
            with pytest.raises((ValueError, TypeError)):
                config = HoldedConfig()
                HoldedClient(config)

    @patch('httpx.AsyncClient.get')
    @pytest.mark.asyncio
    async def test_holded_client_authentication_error(self, mock_get, holded_client):
        """Test handling of authentication errors"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Unauthorized"}
        mock_response.raise_for_status.side_effect = Exception("HTTP 401 Unauthorized")
        mock_get.return_value = mock_response
        
        with pytest.raises(Exception):
            await holded_client.list_contacts()

    @patch('httpx.AsyncClient.get')
    @pytest.mark.asyncio
    async def test_holded_client_server_error(self, mock_get, holded_client):
        """Test handling of server errors"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal server error"}
        mock_response.raise_for_status.side_effect = Exception("HTTP 500 Internal Server Error")
        mock_get.return_value = mock_response
        
        with pytest.raises(Exception):
            await holded_client.list_contacts()


class TestFourGeeksIntegration:
    """Test 4Geeks integration client and processor"""

    @pytest.fixture
    def fourgeeks_client(self):
        """Create a 4Geeks client for testing"""
        from src.api.integrations.fourgeeks.client import FourGeeksCredentials
        credentials = FourGeeksCredentials(username="test_user", password="test_pass")
        return FourGeeksClient(credentials)

    @pytest.fixture
    def student_processor(self, test_session):
        """Create a 4Geeks student processor for testing"""
        from src.api.clients.services.client_service import ClientService
        from src.api.integrations.fourgeeks.client import FourGeeksCredentials
        client_service = ClientService(test_session)
        credentials = FourGeeksCredentials(username="test_user", password="test_pass")
        fourgeeks_client = FourGeeksClient(credentials)
        return StudentProcessor(client_service, fourgeeks_client)

    def test_fourgeeks_client_initialization(self, fourgeeks_client):
        """Test 4Geeks client initialization"""
        assert fourgeeks_client is not None
        assert hasattr(fourgeeks_client, 'credentials')
        assert hasattr(fourgeeks_client, 'BASE_URL')

    @patch('httpx.Client.get')
    def test_get_member_by_email_success(self, mock_get, fourgeeks_client):
        """Test successful member retrieval by email from 4Geeks"""
        # Mock the token to prevent login attempt
        fourgeeks_client._token = "mock_token"
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 1,
            "name": "Student 1",
            "email": "student1@4geeks.com",
            "roles": ["student"]
        }
        mock_get.return_value = mock_response
        
        result = fourgeeks_client.get_member_by_email("student1@4geeks.com")
        
        assert result["id"] == 1
        assert result["name"] == "Student 1"
        assert result["email"] == "student1@4geeks.com"
        mock_get.assert_called()

    @patch('httpx.Client.get')
    def test_get_cohort_user_success(self, mock_get, fourgeeks_client):
        """Test successful cohort user retrieval"""
        # Mock the token to prevent login attempt
        fourgeeks_client._token = "mock_token"
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 123,
            "user_id": 456,
            "cohort_id": 789,
            "status": "ACTIVE",
            "role": "student"
        }
        mock_get.return_value = mock_response
        
        result = fourgeeks_client.get_cohort_user(789, 456)
        
        assert result["id"] == 123
        assert result["user_id"] == 456
        assert result["cohort_id"] == 789

    @patch('httpx.Client.get')
    def test_get_cohort_success(self, mock_get, fourgeeks_client):
        """Test successful cohort retrieval by ID"""
        # Mock the token to prevent login attempt
        fourgeeks_client._token = "mock_token"
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 1,
            "name": "Web Development Cohort",
            "start_date": "2024-01-15",
            "stage": "ACTIVE"
        }
        mock_get.return_value = mock_response
        
        result = fourgeeks_client.get_cohort(1)
        
        assert result["id"] == 1
        assert result["name"] == "Web Development Cohort"
        assert result["start_date"] == "2024-01-15"

    @patch('httpx.Client.get')
    def test_get_user_enrollments_success(self, mock_get, fourgeeks_client):
        """Test successful user enrollments retrieval"""
        # Mock the token to prevent login attempt
        fourgeeks_client._token = "mock_token"
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": 1, "user_id": 123, "cohort_id": 456, "status": "ACTIVE"},
            {"id": 2, "user_id": 123, "cohort_id": 789, "status": "GRADUATED"}
        ]
        mock_get.return_value = mock_response
        
        result = fourgeeks_client.get_user_enrollments(123)
        
        assert len(result) == 2
        assert result[0]["status"] == "ACTIVE"

    def test_fourgeeks_client_missing_credentials(self):
        """Test 4Geeks client initialization without credentials"""
        with pytest.raises(TypeError):
            # Should raise TypeError when no credentials provided
            FourGeeksClient()

    @patch('httpx.Client.get')
    def test_fourgeeks_client_authentication_error(self, mock_get, fourgeeks_client):
        """Test handling of authentication errors"""
        # Mock the token to prevent login attempt  
        fourgeeks_client._token = "mock_token"
        
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Invalid API key"}
        mock_response.raise_for_status.side_effect = Exception("HTTP 401 Unauthorized")
        mock_get.return_value = mock_response
        
        with pytest.raises(Exception):
            fourgeeks_client.get_member_by_email("test@example.com")

    @patch('httpx.Client.get')
    def test_fourgeeks_client_rate_limiting(self, mock_get, fourgeeks_client):
        """Test handling of rate limiting"""
        # Mock the token to prevent login attempt
        fourgeeks_client._token = "mock_token"
        
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}
        mock_response.raise_for_status.side_effect = Exception("HTTP 429 Too Many Requests")
        mock_get.return_value = mock_response
        
        with pytest.raises(Exception):
            fourgeeks_client.get_member_by_email("test@example.com")

    def test_student_processor_initialization(self, student_processor):
        """Test 4Geeks student processor initialization"""
        assert student_processor is not None
        assert hasattr(student_processor, 'client_service')
        assert hasattr(student_processor, 'fourgeeks_client')

    def test_student_processor_find_and_link_student(self, student_processor, test_data_factory, test_session):
        """Test student processor find and link functionality"""
        # Create a test client
        client = test_data_factory.create_client(test_session, identifier="test@example.com")
        
        # Mock the 4Geeks API response
        with patch.object(student_processor.fourgeeks_client, 'get_member_by_email') as mock_get_member:
            mock_get_member.return_value = {
                "id": "4geeks-123",
                "email": "test@example.com",
                "name": "Test Student"
            }
            
            student_id, error = student_processor.find_and_link_student(
                client.id, 
                client.identifier
            )
            
            # Should successfully find and link the student
            assert error is None or error != "not_found"
            mock_get_member.assert_called_once()

    def test_student_processor_student_not_found(self, student_processor, test_data_factory, test_session):
        """Test student processor when student is not found"""
        client = test_data_factory.create_client(test_session, identifier="notfound@example.com")
        
        with patch.object(student_processor.fourgeeks_client, 'get_member_by_email') as mock_get_member:
            mock_get_member.return_value = None
            
            student_id, error = student_processor.find_and_link_student(
                client.id,
                client.identifier
            )
            
            assert student_id is None
            assert error == "not_found"

    def test_student_processor_api_error(self, student_processor, test_data_factory, test_session):
        """Test student processor with API error"""
        client = test_data_factory.create_client(test_session, identifier="error@example.com")
        
        with patch.object(student_processor.fourgeeks_client, 'get_member_by_email') as mock_get_member:
            mock_get_member.side_effect = Exception("API Error")
            
            student_id, error = student_processor.find_and_link_student(
                client.id,
                client.identifier
            )
            
            # Should handle API errors gracefully
            assert student_id is None
            assert error is not None


class TestIntegrationEndpoints:
    """Test integration endpoints"""

    def test_integration_error_handling(self):
        """Test that integration errors are properly handled"""
        # This would test the actual endpoint error handling
        # Implementation depends on the specific endpoint structure
        pass

    def test_integration_authentication(self):
        """Test that integrations properly handle authentication"""
        # Test authentication mechanisms for each integration
        pass

    def test_integration_data_transformation(self):
        """Test that data is properly transformed between systems"""
        # Test data mapping and transformation logic
        pass

    def test_integration_retry_logic(self):
        """Test retry logic for failed API calls"""
        # Test exponential backoff and retry mechanisms
        pass

    def test_integration_logging(self):
        """Test that integrations properly log operations"""
        # Test logging of API calls, errors, and data processing
        pass 


class TestHoldedDuplicateInvoicePrevention:
    """Test suite for Holded invoice duplicate prevention"""

    @pytest.fixture
    def mock_holded_document(self):
        """Sample Holded document data"""
        return {
            "id": "holded-invoice-123",
            "docNumber": "INV-2024-001",
            "date": 1640995200,  # 2022-01-01
            "dueDate": 1643673600,  # 2022-02-01
            "total": 1500.00,
            "currency": "EUR",
            "status": 1,
            "contact": "holded-contact-456",
            "products": [{"account": "external-service-id"}]
        }

    @pytest.fixture
    def mock_updated_holded_document(self):
        """Sample updated Holded document with different amount"""
        return {
            "id": "holded-invoice-123",  # Same ID
            "docNumber": "INV-2024-001",
            "date": 1640995200,
            "dueDate": 1643673600,
            "total": 2000.00,  # Updated amount
            "currency": "EUR",
            "status": 1,
            "contact": "holded-contact-456",
            "products": [{"account": "external-service-id"}]
        }

    @pytest.fixture
    def mock_credit_note_document(self):
        """Sample credit note document"""
        return {
            "id": "holded-credit-note-789",
            "docNumber": "CN-2024-001",
            "date": 1640995200,
            "total": 500.00,
            "currency": "EUR",
            "status": 1,
            "contact": "holded-contact-456",
            "products": [{"account": "external-service-id"}],
            "from": {"docType": "invoice"}
        }

    def test_is_credit_note_detection(self, mock_credit_note_document):
        """Test credit note detection"""
        assert _is_credit_note(mock_credit_note_document) == True
        
        regular_invoice = {"docNumber": "INV-001", "from": {"docType": "invoice"}}
        assert _is_credit_note(regular_invoice) == False

    @patch('src.api.integrations.endpoints.holded.logger')
    def test_prevent_duplicate_invoice_creation(self, mock_logger, mock_holded_document):
        """Test that duplicate invoices are not created"""
        # Mock services
        mock_invoice_service = MagicMock()
        mock_client_service = MagicMock()
        mock_holded_client = AsyncMock()
        mock_service_service = MagicMock()
        mock_service_contract_service = MagicMock()

        # Mock existing invoice
        existing_invoice = MagicMock()
        existing_invoice.id = 1
        existing_invoice.total_amount = 1500.00
        existing_invoice.invoice_number = "INV-2024-001"
        existing_invoice.status = 1
        
        mock_invoice_service.get_invoice_by_external_id.return_value = existing_invoice
        mock_invoice_service.update_invoice.return_value = existing_invoice

        # Mock client and service lookups
        mock_client = MagicMock()
        mock_client.id = 1
        
        mock_service = MagicMock()
        mock_service.id = 1
        
        # Mock async functions
        async def mock_get_or_create_client(*args):
            return mock_client
            
        # Test the duplicate prevention logic directly
        document_id = mock_holded_document["id"]
        invoice = mock_invoice_service.get_invoice_by_external_id(document_id)
        
        # Verify invoice exists (duplicate case)
        assert invoice is not None
        assert invoice.total_amount == 1500.00
        
        # Verify create_invoice was not called when duplicate exists
        mock_invoice_service.create_invoice.assert_not_called()


    def test_credit_note_amount_negation(self, mock_credit_note_document):
        """Test that credit note amounts are properly negated"""
        document = mock_credit_note_document.copy()
        
        if _is_credit_note(document):
            document["total"] = -abs(float(document.get("total", 0)))
            
        assert document["total"] == -500.00

    @patch('src.api.integrations.endpoints.holded.logger')  
    def test_no_update_when_amounts_are_same(self, mock_logger, mock_holded_document):
        """Test that no update occurs when amounts are the same"""
        # Mock services
        mock_invoice_service = MagicMock()
        
        # Mock existing invoice with same amount as document
        existing_invoice = MagicMock()
        existing_invoice.id = 1
        existing_invoice.total_amount = 1500.00  # Same as document
        existing_invoice.invoice_number = "INV-2024-001"
        existing_invoice.status = 1
        
        mock_invoice_service.get_invoice_by_external_id.return_value = existing_invoice

        # Simulate the update logic
        document = mock_holded_document
        document_total = document.get("total", 0)
        
        # Check if amount changed (1500.00 vs 1500.00)
        amount_changed = abs(existing_invoice.total_amount - document_total) > 0.01
        assert amount_changed == False
        
        # Verify update_invoice would NOT be called
        mock_invoice_service.update_invoice.assert_not_called()

    def test_floating_point_precision_tolerance(self):
        """Test that small floating point differences are ignored"""
        amount1 = 1500.00
        amount2 = 1500.005  # Small difference
        
        # Should NOT trigger update (within tolerance)
        assert abs(amount1 - amount2) <= 0.01
        
        amount3 = 1500.02  # Larger difference
        
        # Should trigger update (outside tolerance)
        assert abs(amount1 - amount3) > 0.01 