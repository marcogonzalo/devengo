# Memory Bank - Devengo Project Documentation

This directory contains comprehensive documentation for the Devengo project, covering architecture, features, integrations, and implementation details.

## Documentation Index

### Core Documentation

- **[PROJECT_ARCHITECTURE.md](./PROJECT_ARCHITECTURE.md)**
  - Complete project architecture overview
  - Technology stack (Backend: FastAPI/Python, Frontend: React/TypeScript)
  - Project structure and organization
  - Development environment setup
  - Security and performance considerations

- **[DATABASE_MODELS.md](./DATABASE_MODELS.md)**
  - Complete database schema documentation
  - All models and their relationships
  - Field descriptions and constraints
  - Encryption and data integrity rules
  - Migration management

### Feature Documentation

- **[ACCRUAL_PROCESS_DOCUMENTATION.md](./ACCRUAL_PROCESS_DOCUMENTATION.md)**
  - Contract accrual processing system
  - Processing flow and business logic
  - Status handling (ACTIVE, CANCELED, CLOSED)
  - Special cases and edge case handling
  - Accrual calculation algorithms
  - API usage and examples

- **[accrual-reports-documentation.md](./accrual-reports-documentation.md)**
  - Accrual reports and CSV generation system
  - Report algorithm and data organization
  - Monthly breakdown and hierarchical grouping
  - Edge case handling (NULL periods, zero amounts)
  - CSV output format and performance considerations

- **[frontend-features.md](./frontend-features.md)**
  - Frontend functionalities overview
  - Authentication (passwordless with magic link)
  - Client External ID management
  - Accrual year overview and visual reports
  - Report downloads and user experience features

### Integration Documentation

- **[EXTERNAL_INTEGRATIONS.md](./EXTERNAL_INTEGRATIONS.md)**
  - Holded integration (invoicing system)
  - 4Geeks CRM integration (student management)
  - Notion integration (client page IDs)
  - Integration error management
  - API authentication and data consistency

- **[SYNC_MANAGEMENT_SYSTEM.md](./SYNC_MANAGEMENT_SYSTEM.md)**
  - Sync orchestration system
  - Sync steps and execution order
  - API endpoints and script usage
  - Execution tracking and monitoring
  - Date range processing and best practices

## Quick Reference

### Main API Endpoints

- **Accruals**: `/api/accruals/process-contracts` - Process contract accruals
- **Reports**: `/api/accruals/export/csv` - Export accrual reports
- **Sync**: `/api/sync/execute-step` - Execute sync steps
- **Integrations**:
  - `/api/integrations/holded/sync-services` - Sync services
  - `/api/integrations/holded/sync-invoices-and-clients` - Sync invoices
  - `/api/integrations/fourgeeks/sync-students-from-clients` - Sync students
  - `/api/integrations/fourgeeks/sync-enrollments-from-clients` - Sync enrollments
  - `/api/integrations/notion/sync-page-ids` - Sync Notion IDs

### Sync Steps Order

1. `services` - Import services from Holded
2. `invoices` - Import invoices and clients from Holded
3. `crm-clients` - Import students from 4Geeks CRM
4. `service-periods` - Import enrollments from 4Geeks CRM
5. `notion-external-id` - Sync Notion page IDs
6. `accruals` - Process contract accruals (separate step)

### Key Models

- **Client**: Client information with encrypted identifiers
- **ServiceContract**: Client contracts for services
- **ServicePeriod**: Active periods with status tracking
- **ContractAccrual**: Contract-level accrual tracking
- **AccruedPeriod**: Monthly accrual records
- **Invoice**: Invoice data from external systems
- **Service**: Educational services (courses)

### Business Rules

- Months past cannot be altered
- Holidays are not counted in class count
- Credits must be accrued in the corresponding month
- Total invoiced minus credits must match all money accrued
- Cancellation: remaining amount accrued that month
- Pause: accrue from start until last active moment
- Resume: remaining amount applied in new course period

## Documentation Updates

This memory bank is maintained to reflect the current state of the project. When making significant changes:

1. Update relevant documentation files
2. Update this README if structure changes
3. Keep examples and code snippets current
4. Document new features and integrations

## Related Files

- **Main README**: `/README.md` - Project overview and usage
- **Test Documentation**: `/tests/README.md` - Test suite documentation
- **Docker Setup**: `/DOCKER_TEST_SETUP.md` - Docker testing setup
