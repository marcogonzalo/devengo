# Devengo Project Architecture

## Overview

Devengo is a full-stack application for managing income and expenses following the accrual accounting principle. The system applies accrual accounting to invoicing (not payments), ensuring transactions are recorded when they occur, not when payment is received.

## Technology Stack

### Backend

- **Framework**: FastAPI (Python 3.13)
- **ORM**: SQLModel (built on SQLAlchemy)
- **Database**: PostgreSQL 15
- **Migrations**: Alembic
- **HTTP Client**: httpx (for external API calls)
- **Encryption**: cryptography library
- **Testing**: pytest, pytest-asyncio, pytest-cov, pytest-mock

### Frontend

- **Framework**: React 19 with TypeScript
- **Build Tool**: Vite 6
- **UI Library**: HeroUI (NextUI) 2.7.10
- **Routing**: React Router DOM 6.22.3
- **Charts**: Recharts 2.15.0
- **Icons**: @iconify/react
- **Animations**: framer-motion 11.18.2
- **Styling**: Tailwind CSS 3.4.17

### Infrastructure

- **Containerization**: Docker with docker-compose
- **Development**: Hot reload for both frontend and backend
- **Debugging**: debugpy for Python debugging (port 5678)

## Project Structure

```text
devengo/
├── src/
│   ├── api/                    # Backend API
│   │   ├── clients/           # Client management module
│   │   ├── invoices/          # Invoice management module
│   │   ├── services/         # Service and contract management
│   │   ├── accruals/         # Accrual processing system
│   │   ├── integrations/     # External system integrations
│   │   ├── sync/             # Synchronization management
│   │   ├── common/           # Shared utilities and models
│   │   ├── routes.py         # Main API router
│   │   └── scripts/          # Utility scripts
│   ├── client/                # Frontend React application
│   │   ├── components/       # React components
│   │   ├── utils/           # Utilities (API client, etc.)
│   │   └── App.tsx          # Main app component
│   └── main.py              # FastAPI application entry point
├── migrations/               # Alembic database migrations
├── tests/                    # Test suite
├── memory-bank/             # Project documentation
├── docker-compose.yml       # Docker development environment
├── Dockerfile.api          # Backend Docker image
├── Dockerfile.client        # Frontend Docker image
├── Pipfile                  # Python dependencies
└── package.json             # Node.js dependencies
```

## Architecture Patterns

### Backend Architecture

#### Modular Structure

- **Domain-Driven Design**: Each domain (clients, invoices, services, accruals) has its own module
- **Service Layer**: Business logic separated into service classes
- **Repository Pattern**: SQLModel models act as repositories
- **Dependency Injection**: FastAPI's dependency system for database sessions

#### Module Organization

Each module follows this structure:

```text
module_name/
├── models/          # SQLModel data models
├── schemas/         # Pydantic schemas for API
├── services/        # Business logic
├── endpoints/       # FastAPI route handlers
└── utils/          # Module-specific utilities
```

#### Key Services

- `ClientService`: Client CRUD and external ID management
- `InvoiceService`: Invoice management and matching
- `ServiceContractService`: Contract lifecycle management
- `ContractAccrualProcessor`: Core accrual processing logic
- `AccrualReportsService`: CSV report generation
- `SyncManagementService`: Synchronization orchestration

### Frontend Architecture

#### Component Structure

- **Page Components**: Main views (Dashboard, AccrualOverview, etc.)
- **Feature Components**: Reusable UI components
- **API Client**: Centralized API communication (`src/client/utils/api.ts`)
- **Routing**: React Router with protected routes

#### State Management

- **Local State**: React hooks (useState, useEffect)
- **Server State**: Direct API calls with error handling
- **Theme Management**: HeroUI theme provider (dark mode default)

#### Key Components

- `Login`: Passwordless authentication
- `Dashboard`: Main navigation and overview
- `ClientManagement`: External ID management
- `AccrualOverview`: Yearly accrual summaries
- `AccrualReports`: Visual reports and CSV export
- `SyncManagement`: Synchronization execution UI
- `IntegrationErrors`: Error tracking and management

## Database Architecture

### Core Models

#### Client Management

- **Client**: Encrypted client information with identifier (email)
- **ClientExternalId**: External system IDs (Holded, 4Geeks, Notion)

#### Invoice Management

- **Invoice**: Invoice data from external systems (Holded)
- Links to Client and ServiceContract

#### Service Management

- **Service**: Educational services (courses) with session information
- **ServiceContract**: Client contracts for services
- **ServicePeriod**: Active periods with status tracking (ACTIVE, POSTPONED, DROPPED, ENDED)

#### Accrual System

- **ContractAccrual**: Contract-level accrual tracking (1:1 with ServiceContract)
- **AccruedPeriod**: Monthly accrual records (1:N from ContractAccrual)

#### System Management

- **SyncExecution**: Synchronization execution tracking
- **IntegrationError**: Integration error logging

### Relationships

```text
Client (1) ──< (N) ClientExternalId
Client (1) ──< (N) ServiceContract
ServiceContract (1) ──< (N) Invoice
ServiceContract (1) ──< (N) ServicePeriod
ServiceContract (1) ── (1) ContractAccrual
ContractAccrual (1) ──< (N) AccruedPeriod
ServicePeriod (1) ──< (N) AccruedPeriod
Service (1) ──< (N) ServiceContract
```

## API Architecture

### Endpoint Organization

#### Domain Endpoints

- `/api/clients/*` - Client management
- `/api/invoices/*` - Invoice management
- `/api/services/*` - Service and contract management
- `/api/accruals/*` - Accrual processing and reports

#### Integration Endpoints

- `/api/integrations/holded/*` - Holded (invoicing) integration
- `/api/integrations/fourgeeks/*` - 4Geeks CRM integration
- `/api/integrations/notion/*` - Notion integration
- `/api/integrations/errors/*` - Integration error management

#### Sync Management

- `/api/sync/*` - Synchronization orchestration

### API Patterns

#### Request/Response

- **Request Validation**: Pydantic schemas
- **Response Models**: Typed response models
- **Error Handling**: HTTPException with proper status codes
- **Logging**: Structured logging for all operations

#### Authentication

- **Passwordless**: Email-based magic link authentication
- **Session Management**: Token-based (to be implemented)

## External Integrations

### Holded (Invoicing System)

- **Purpose**: Import services, invoices, and clients
- **Endpoints**:
  - `/api/integrations/holded/sync-services`
  - `/api/integrations/holded/sync-invoices-and-clients`
- **Data**: Services, invoices, client external IDs

### 4Geeks CRM

- **Purpose**: Import student data and enrollments
- **Endpoints**:
  - `/api/integrations/fourgeeks/sync-students-from-clients`
  - `/api/integrations/fourgeeks/sync-enrollments-from-clients`
- **Data**: Client information, service periods (enrollments)

### Notion

- **Purpose**: Sync client page IDs
- **Endpoints**: `/api/integrations/notion/sync-page-ids`
- **Data**: Client external IDs (Notion page_id)

## Development Environment

### Docker Setup

- **API Container**: Python FastAPI server (port 3001)
- **Client Container**: Vite dev server (port 3000)
- **Database Container**: PostgreSQL 15 (port 5432)
- **Volume Mounts**: Hot reload for code changes
- **Networks**: Bridge network for inter-container communication

### Environment Variables

- `DATABASE_URL`: PostgreSQL connection string
- `VITE_API_URL`: Frontend API base URL (default: http://localhost:3001)
- Integration API keys and secrets (in `.env` file)

### Debugging

- **Backend**: debugpy on port 5678
- **Frontend**: Browser DevTools + Vite HMR
- **Database**: Direct PostgreSQL access on port 5432

## Testing Strategy

### Test Structure

- **Unit Tests**: Service layer and utilities
- **Integration Tests**: API endpoints and database operations
- **Edge Cases**: Comprehensive edge case coverage
- **Coverage Target**: >80% code coverage

### Test Organization

```text
tests/
├── conftest.py           # Shared fixtures
├── test_common_utils.py  # Utility tests
├── test_client_service.py
├── test_invoice_service.py
├── test_services.py
├── test_integrations.py
├── test_accruals.py
└── test_routes.py
```

## Security Considerations

### Data Encryption

- **Client Identifiers**: Encrypted at rest using cryptography library
- **Sensitive Data**: Encryption/decryption utilities in `common/utils/encryption.py`

### API Security

- **CORS**: Configured for development (should be restricted in production)
- **Input Validation**: Pydantic schemas for all inputs
- **SQL Injection**: Prevented by SQLModel/SQLAlchemy ORM

## Performance Optimizations

### Database

- **Eager Loading**: `selectinload` for relationships
- **Indexes**: Strategic indexes on foreign keys and date fields
- **Query Optimization**: Single queries with joins instead of N+1

### API

- **Response Caching**: Opportunities for dashboard summaries
- **Pagination**: Ready for large datasets
- **Streaming**: CSV exports use streaming for large files

## Deployment Considerations

### Production Readiness

- Environment-specific configuration
- Database migrations via Alembic
- Static file serving for frontend
- Health check endpoint (`/health`)
- Proper CORS configuration
- Error logging and monitoring

### Scalability

- Stateless API design
- Database connection pooling
- Horizontal scaling ready
- Caching strategies for reports
