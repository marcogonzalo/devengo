# Docker Test Setup for Devengo API

This document explains how to run tests using Docker containers for the Devengo API project.

## Overview

The Docker test setup provides an isolated environment for running tests with:

- PostgreSQL test database
- All required dependencies
- Proper environment configuration
- Coverage reporting capabilities

## Files Involved

### `docker-compose.test.yml`

Main Docker Compose configuration for testing:

- **api-test**: Test container with all dependencies
- **db-test**: PostgreSQL test database
- **test-network**: Isolated network for test services

### `Dockerfile.api`

Multi-stage Dockerfile with dedicated test stage:

- **api-test**: Stage optimized for testing with dev dependencies

### `run_tests.sh`

Convenient test runner script with multiple options

## Quick Start

### 1. Build Test Container

```bash
docker compose -f docker-compose.test.yml build api-test
```

### 2. Run All Tests

```bash
./run_tests.sh
```

### 3. Run Specific Test File

```bash
./run_tests.sh --file test_common_utils.py
```

### 4. Run Tests with Coverage

```bash
./run_tests.sh --coverage
```

## Test Runner Options

The `run_tests.sh` script provides several options:

```bash
# Run all tests (default)
./run_tests.sh

# Run only unit tests
./run_tests.sh --unit

# Run only integration tests
./run_tests.sh --integration

# Run tests with coverage report
./run_tests.sh --coverage

# Run specific test file
./run_tests.sh --file test_invoice_service.py

# Run tests in parallel
./run_tests.sh --parallel

# Run with verbose output
./run_tests.sh --verbose

# Show help
./run_tests.sh --help
```

## Direct Docker Commands

You can also run tests directly with Docker Compose:

```bash
# Run all tests
docker compose -f docker-compose.test.yml run --rm api-test pytest

# Run specific test file
docker compose -f docker-compose.test.yml run --rm api-test pytest tests/test_common_utils.py -v

# Run with coverage
docker compose -f docker-compose.test.yml run --rm api-test pytest --cov=src/api --cov-report=html

# Run tests excluding specific files
docker compose -f docker-compose.test.yml run --rm api-test pytest tests/ --ignore=tests/test_integrations.py
```

## Test Structure

The test suite includes:

### Working Test Files

- **`tests/test_common_utils.py`** (34 tests) - ✅ All passing
- **`tests/test_client_service.py`** (30 tests) - ✅ All passing  
- **`tests/test_invoice_service.py`** (26 tests) - ✅ All passing
- **`tests/test_routes.py`** (8 tests) - ⚠️ Some async issues

### Test Files Needing Updates

- **`tests/test_services.py`** (583 lines) - ⚠️ Schema mismatches with actual implementation
- **`tests/test_integrations.py`** (529 lines) - ⚠️ Client initialization issues
- **`tests/test_accruals.py`** (573 lines) - ⚠️ Model import issues

### Test Infrastructure

- **`tests/conftest.py`** (215 lines) - Comprehensive test fixtures and data factories
- **`pytest.ini`** - Test configuration with markers and discovery settings

## Current Status

### ✅ Successfully Configured

- Docker Compose test environment
- PostgreSQL test database
- Test dependencies and environment variables
- Coverage reporting
- Test runner script
- Core utility and service tests

### ⚠️ Known Issues

1. **Integration Tests**: Client initialization parameters don't match actual implementation
2. **Service Tests**: Schema validation errors due to enum mismatches
3. **Accrual Tests**: Model import path issues
4. **Route Tests**: Async/await handling in mocked endpoints

### 🎯 Test Coverage

Current coverage: **38%** overall

- High coverage in: schemas, models, constants
- Lower coverage in: services, integrations, processors

## Environment Variables

The test environment uses these key variables:

- `DATABASE_URL`: Test database connection
- `ENCRYPTION_KEY`: Test encryption key for encrypted fields
- `ENV`: Set to "test" for test-specific behavior

## Database

Tests use an in-memory SQLite database for speed and isolation:

- Fresh database for each test session
- All tables created automatically
- No data persistence between test runs

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all source code imports use absolute paths (`src.api.module`)
2. **Database Errors**: Check that models match the actual database schema
3. **Schema Validation**: Verify that test data matches Pydantic schema requirements
4. **Container Build Issues**: Run `docker compose -f docker-compose.test.yml build --no-cache api-test`

### Debug Commands

```bash
# Check container logs
docker compose -f docker-compose.test.yml logs api-test

# Run interactive shell in test container
docker compose -f docker-compose.test.yml run --rm api-test bash

# Check test database connection
docker compose -f docker-compose.test.yml run --rm api-test python -c "from src.api.common.utils.database import get_database_url; print(get_database_url())"
```

## Next Steps

To complete the test setup:

1. **Fix Integration Tests**: Update client initialization to match actual API
2. **Update Service Tests**: Align schemas with actual model definitions
3. **Fix Accrual Tests**: Correct model import paths
4. **Add Test Markers**: Mark tests as unit/integration for better organization
5. **Increase Coverage**: Add tests for uncovered service methods

## Performance

Test execution times:

- **Unit tests**: ~0.1-0.3 seconds per test
- **Full test suite**: ~3-5 seconds (excluding problematic tests)
- **With coverage**: ~5-10 seconds

The Docker test environment provides consistent, reproducible test execution across different development environments.

## File Structure

```
devengo/
├── docker-compose.test.yml     # Test environment configuration
├── Dockerfile.api              # Multi-stage Dockerfile with test stage
├── run_tests.sh               # Test runner script
├── pytest.ini                # Pytest configuration
├── tests/                     # Test files
│   ├── conftest.py           # Test fixtures and configuration
│   ├── test_*.py             # Individual test files
│   └── README.md             # Test documentation
└── src/api/                   # Source code being tested
```

## Best Practices

1. **Always use the test runner script** for consistency
2. **Run tests with coverage** to ensure code quality
3. **Use specific test files** during development for faster feedback
4. **Run full test suite** before committing changes
5. **Check coverage reports** to identify untested code
6. **Use parallel execution** for faster test runs
7. **Clean up containers** after testing to save disk space

## Maintenance

### Update Dependencies

When adding new test dependencies:

1. Update `Pipfile` with new packages
2. Run `pipenv lock` to update `Pipfile.lock`
3. Rebuild test container: `docker compose -f docker-compose.test.yml build api-test`

### Clean Up

Remove test containers and volumes:

```bash
docker compose -f docker-compose.test.yml down -v
docker system prune -f
```
