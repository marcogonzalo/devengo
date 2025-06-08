# Test Suite Documentation

This directory contains comprehensive tests for all API modules in the Devengo project.

## Test Structure

The test suite is organized to mirror the API module structure:

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                 # Shared fixtures and configuration
├── test_common_utils.py        # Tests for common utilities
├── test_client_service.py      # Tests for client service
├── test_invoice_service.py     # Tests for invoice service
├── test_services.py            # Tests for services module
├── test_integrations.py        # Tests for integrations
├── test_accruals.py           # Tests for accruals module
├── test_routes.py             # Tests for API routes
└── README.md                  # This file
```

## Test Categories

### Unit Tests

- **Common Utils** (`test_common_utils.py`): Tests for datetime, encryption, and database utilities
- **Service Classes** (`test_*_service.py`): Tests for all service layer classes
- **Models**: Tests for data models and their relationships

### Integration Tests

- **API Routes** (`test_routes.py`): Tests for FastAPI endpoints
- **External Integrations** (`test_integrations.py`): Tests for Notion, Holded, and 4Geeks integrations
- **Database Operations**: Tests for complex database interactions

### Edge Case Tests

Each test module includes comprehensive edge case testing:

- Invalid input handling
- Boundary conditions
- Error scenarios
- Data validation
- Performance considerations

## Test Coverage

The test suite covers:

### ✅ Common Utilities

- **DateTime Utils**: Date parsing, month boundaries, timezone handling
- **Encryption Utils**: Data encryption/decryption, error handling
- **Database Utils**: Connection management, URL construction

### ✅ Client Service

- CRUD operations (Create, Read, Update, Delete)
- External ID management
- Encryption of sensitive data
- Pagination and filtering
- Error handling and edge cases

### ✅ Invoice Service

- Invoice lifecycle management
- External ID tracking
- Amount calculations (including negative amounts for credit notes)
- Date handling and validation
- Status management

### ✅ Services Module

- **Service Management**: Basic service CRUD operations
- **Service Periods**: Time-based service tracking
- **Service Contracts**: Client-service relationships and billing

### ✅ Integrations

- **Notion Integration**: Database queries, page retrieval, error handling
- **Holded Integration**: Contact and document management
- **4Geeks Integration**: Student and payment processing

### ✅ Accruals Module

- **Contract Accrual Processor**: Complex business logic for accrual calculations
- **Accrual Reports Service**: Reporting and analytics
- **Edge Cases**: Resignation detection, overlapping periods, credit notes

### ✅ API Routes

- Endpoint functionality
- Request/response validation
- Error handling
- Router integration

## Test Fixtures and Utilities

### Shared Fixtures (`conftest.py`)

- **Database Setup**: In-memory SQLite for fast testing
- **Test Data Factory**: Consistent test data creation
- **Mock Clients**: Mocked external service clients
- **Environment Setup**: Test environment configuration

### Test Data Patterns

- **Factories**: Reusable data creation methods
- **Fixtures**: Pre-configured test objects
- **Mocks**: External service simulation

## Running Tests

### Prerequisites

Install test dependencies:

```bash
pipenv install --dev
```

### Basic Test Execution

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_client_service.py

# Run specific test class
pytest tests/test_client_service.py::TestClientService

# Run specific test method
pytest tests/test_client_service.py::TestClientService::test_create_client_success
```

### Test Categories

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Run smoke tests
pytest -m smoke
```

### Coverage Reports

```bash
# Run tests with coverage
pytest --cov=src/api

# Generate HTML coverage report
pytest --cov=src/api --cov-report=html

# Generate coverage report with missing lines
pytest --cov=src/api --cov-report=term-missing
```

### Parallel Execution

```bash
# Run tests in parallel (faster execution)
pytest -n auto

# Run tests in parallel with specific number of workers
pytest -n 4
```

## Test Best Practices

### Test Structure

Each test follows the **Arrange-Act-Assert** pattern:

```python
def test_example(self, test_session, test_data_factory):
    # Arrange: Set up test data
    client = test_data_factory.create_client(test_session)
    
    # Act: Execute the functionality
    result = service.get_client(client.id)
    
    # Assert: Verify the results
    assert result is not None
    assert result.id == client.id
```

### Test Naming

- Descriptive test names that explain what is being tested
- Format: `test_[functionality]_[scenario]_[expected_result]`
- Examples:
  - `test_create_client_success`
  - `test_get_client_not_found`
  - `test_update_client_with_invalid_data`

### Test Categories

Tests are categorized for different scenarios:

- **Success Cases**: Normal operation with valid data
- **Error Cases**: Invalid input, missing data, constraint violations
- **Edge Cases**: Boundary conditions, special characters, large datasets
- **Integration Cases**: Multi-component interactions

### Mocking Strategy

- **External Services**: Always mocked to avoid external dependencies
- **Database**: In-memory SQLite for fast, isolated tests
- **Time-dependent Code**: Mocked for consistent results

## Continuous Integration

### Docker Test Environment

Tests can be run in Docker using the test configuration:

```bash
# Run all tests in Docker
docker compose -f docker-compose.test.yml up --build

# Run specific tests
docker compose -f docker-compose.test.yml run --rm api-test pytest tests/test_client_service.py -v

# Run with coverage
docker compose -f docker-compose.test.yml run --rm api-test pytest --cov=src/api tests/
```

### Test Database

- Uses PostgreSQL in Docker for integration testing
- Automatically creates and tears down test database
- Isolated from development and production databases

## Adding New Tests

### For New Services

1. Create test file: `tests/test_[module_name].py`
2. Import the service class and dependencies
3. Create test class: `class Test[ServiceName]:`
4. Add fixtures for test data setup
5. Write tests for all public methods
6. Include edge cases and error scenarios

### For New Endpoints

1. Add tests to `tests/test_routes.py`
2. Use FastAPI TestClient for endpoint testing
3. Test all HTTP methods and status codes
4. Validate request/response formats

### Test Template

```python
import pytest
from unittest.mock import Mock, patch
from sqlmodel import Session

from src.api.module.service import ServiceClass


class TestServiceClass:
    """Test ServiceClass functionality"""

    @pytest.fixture
    def service(self, test_session):
        """Create service instance for testing"""
        return ServiceClass(test_session)

    def test_method_success(self, service, test_data_factory):
        """Test successful method execution"""
        # Arrange
        test_data = test_data_factory.create_test_data()
        
        # Act
        result = service.method(test_data)
        
        # Assert
        assert result is not None
        assert result.expected_property == expected_value

    def test_method_error_case(self, service):
        """Test method with invalid input"""
        with pytest.raises(ExpectedException):
            service.method(invalid_input)
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed and PYTHONPATH is correct
2. **Database Errors**: Check that test database is properly configured
3. **Fixture Errors**: Verify fixture dependencies and scope
4. **Mock Errors**: Ensure mocks are properly configured and reset between tests

### Debug Mode

```bash
# Run tests with debug output
pytest -s -vv

# Run single test with debugging
pytest -s tests/test_client_service.py::TestClientService::test_create_client_success

# Use pytest debugger
pytest --pdb
```

### Performance Issues

```bash
# Show slowest tests
pytest --durations=10

# Profile test execution
pytest --profile

# Run tests in parallel for speed
pytest -n auto
```

## Maintenance

### Regular Tasks

- Update test data when models change
- Add tests for new functionality
- Review and update mocks when external APIs change
- Monitor test coverage and add tests for uncovered code
- Update documentation when test structure changes

### Test Data Management

- Keep test data minimal and focused
- Use factories for consistent data creation
- Clean up test data between tests
- Avoid hard-coded values that may become outdated

This comprehensive test suite ensures the reliability, maintainability, and correctness of the Devengo API.
