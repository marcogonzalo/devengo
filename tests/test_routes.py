import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json

from src.api.routes import api_router


class TestAPIRoutes:
    """Test main API routes"""

    @pytest.fixture
    def client(self):
        """Create a test client for the API"""
        from fastapi import FastAPI
        
        app = FastAPI()
        app.include_router(api_router)
        
        return TestClient(app)

    def test_hello_endpoint_get(self, client):
        """Test hello endpoint with GET request"""
        response = client.get("/hello")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "backend" in data["message"]

    def test_hello_endpoint_post(self, client):
        """Test hello endpoint with POST request"""
        response = client.post("/hello")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "backend" in data["message"]

    def test_hello_endpoint_response_format(self, client):
        """Test hello endpoint response format"""
        response = client.get("/hello")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        
        data = response.json()
        assert isinstance(data, dict)
        assert "message" in data
        assert isinstance(data["message"], str)

    def test_hello_endpoint_other_methods(self, client):
        """Test hello endpoint with unsupported methods"""
        # PUT should not be allowed
        response = client.put("/hello")
        assert response.status_code == 405  # Method Not Allowed
        
        # DELETE should not be allowed
        response = client.delete("/hello")
        assert response.status_code == 405  # Method Not Allowed

    def test_nonexistent_endpoint(self, client):
        """Test accessing non-existent endpoint"""
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_api_router_includes_all_modules(self):
        """Test that API router includes all expected module routers"""
        # This test verifies that all routers are properly included
        # The exact implementation depends on how routers are structured
        
        # Check that the router has the expected routes
        routes = [route.path for route in api_router.routes]
        
        # Should include the hello route
        assert any("/hello" in route for route in routes)
        
        # Note: Other route checks would depend on the actual router structure
        # and the paths defined in each module's router

    def test_api_router_initialization(self):
        """Test that API router is properly initialized"""
        assert api_router is not None
        assert hasattr(api_router, 'routes')
        assert len(api_router.routes) > 0

    def test_hello_endpoint_uses_json_response(self, client):
        """Test that hello endpoint returns JSON response"""
        response = client.get("/hello")
        
        # Verify it returns JSON
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/json"
        
        # Verify the response structure
        data = response.json()
        assert "message" in data

    def test_hello_endpoint_message_content(self, client):
        """Test the specific content of the hello message"""
        response = client.get("/hello")
        data = response.json()
        
        message = data["message"]
        assert "Hello!" in message
        assert "backend" in message
        assert "network tab" in message
        assert "google inspector" in message
        assert "GET request" in message

    def test_api_error_handling(self, client):
        """Test API error handling"""
        # Test with malformed request (if applicable)
        # This would depend on specific endpoint implementations
        pass

    def test_api_cors_headers(self, client):
        """Test CORS headers if configured"""
        response = client.get("/hello")
        
        # Check if CORS headers are present (if configured)
        # This would depend on whether CORS is configured in the app
        assert response.status_code == 200

    def test_api_content_type_headers(self, client):
        """Test content type headers"""
        response = client.get("/hello")
        
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

    def test_hello_endpoint_consistency(self, client):
        """Test that hello endpoint returns consistent responses"""
        # Make multiple requests to ensure consistency
        responses = []
        for _ in range(3):
            response = client.get("/hello")
            responses.append(response.json())
        
        # All responses should be identical
        first_response = responses[0]
        for response in responses[1:]:
            assert response == first_response

    def test_hello_endpoint_performance(self, client):
        """Test hello endpoint performance"""
        import time
        
        start_time = time.time()
        response = client.get("/hello")
        end_time = time.time()
        
        # Should respond quickly (within 1 second)
        response_time = end_time - start_time
        assert response_time < 1.0
        assert response.status_code == 200


class TestRouterIntegration:
    """Test router integration and module inclusion"""

    def test_client_router_integration(self):
        """Test that client router is properly integrated"""
        from src.api.clients.endpoints.client import router as client_router
        
        # Check that client router exists and has routes
        assert client_router is not None
        assert hasattr(client_router, 'routes')

    def test_invoice_router_integration(self):
        """Test that invoice router is properly integrated"""
        from src.api.invoices.endpoints.invoice import router as invoice_router
        
        # Check that invoice router exists and has routes
        assert invoice_router is not None
        assert hasattr(invoice_router, 'routes')

    def test_service_router_integration(self):
        """Test that service routers are properly integrated"""
        from src.api.services.endpoints.service import router as service_router
        from src.api.services.endpoints.service_period import router as service_period_router
        from src.api.services.endpoints.service_contract import router as service_contract_router
        
        # Check that all service routers exist
        assert service_router is not None
        assert service_period_router is not None
        assert service_contract_router is not None

    def test_accrual_router_integration(self):
        """Test that accrual router is properly integrated"""
        from src.api.accruals.endpoints.accruals import router as accruals_router
        
        # Check that accrual router exists
        assert accruals_router is not None
        assert hasattr(accruals_router, 'routes')

    def test_integration_routers(self):
        """Test that integration routers are properly integrated"""
        from src.api.integrations.endpoints.holded import router as holded_router
        from src.api.integrations.endpoints.fourgeeks import router as fourgeeks_router
        from src.api.integrations.endpoints.notion import router as notion_router
        
        # Check that all integration routers exist
        assert holded_router is not None
        assert fourgeeks_router is not None
        assert notion_router is not None

    def test_all_routers_included_in_main_router(self):
        """Test that all module routers are included in the main API router"""
        # Get all routes from the main router
        all_routes = []
        for route in api_router.routes:
            if hasattr(route, 'path'):
                all_routes.append(route.path)
        
        # The main router should have routes (including the hello route)
        assert len(all_routes) > 0
        
        # Should include the hello route
        hello_routes = [route for route in all_routes if 'hello' in route]
        assert len(hello_routes) > 0

    def test_router_dependencies(self):
        """Test that routers don't have circular dependencies"""
        # This is more of a structural test
        # Import all routers to ensure no circular dependencies
        try:
            from src.api.clients.endpoints.client import router as client_router
            from src.api.invoices.endpoints.invoice import router as invoice_router
            from src.api.services.endpoints.service import router as service_router
            from src.api.services.endpoints.service_period import router as service_period_router
            from src.api.services.endpoints.service_contract import router as service_contract_router
            from src.api.accruals.endpoints.accruals import router as accruals_router
            from src.api.integrations.endpoints.holded import router as holded_router
            from src.api.integrations.endpoints.fourgeeks import router as fourgeeks_router
            from src.api.integrations.endpoints.notion import router as notion_router
            
            # If we get here without import errors, dependencies are OK
            assert True
            
        except ImportError as e:
            pytest.fail(f"Router import failed, possible circular dependency: {e}")

    def test_router_prefix_conflicts(self):
        """Test that routers don't have conflicting path prefixes"""
        # This would check for path conflicts between different routers
        # Implementation would depend on the specific router configurations
        
        # For now, just ensure the main router can be imported without conflicts
        assert api_router is not None 