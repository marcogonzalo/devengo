# Contract Accrual Processing System

## Overview

This document describes the contract accrual processing system that implements the business logic for processing ServiceContracts based on their status and associated ServicePeriods to generate appropriate accrual records.

**Key Principles:**

- Monthly portions are calculated based on **remaining sessions**, not total sessions
- Accrued amounts are calculated from **remaining_amount_to_accrue**, not total contract amount
- This ensures proper accrual distribution in final periods where only a percentage of the remaining amount should be accrued

## Architecture

The system follows a clean architecture pattern with clear separation of concerns:

### Service Layer

- **`ContractAccrualProcessor`**: Main service class that orchestrates the accrual processing
- Located in: `src/api/accruals/services/contract_accrual_processor.py`
- **Async Support**: Full async/await support for Notion integration

### Endpoint Layer

- **`/accruals/process-contracts`**: Main endpoint for processing contract accruals (async)
- **`/accruals/process-contracts/schema`**: Documentation endpoint for the processing schema
- Located in: `src/api/accruals/endpoints/contract_accrual_process.py`

### Models

- **`ContractAccrual`**: Tracks contract-level accrual data
- **`AccruedPeriod`**: Records individual accrual transactions
- **`ServiceContract`**: Contract information
- **`ServicePeriod`**: Service delivery periods

### Database Relationships

- One-to-one: ServiceContract ↔ ContractAccrual
- One-to-many: ContractAccrual → AccruedPeriod
- One-to-many: ServiceContract → ServicePeriod

## Contract Processing Cases

### Case 1: Active Contracts (`ServiceContractStatus.ACTIVE`)

#### 1.1 Active Contracts with Completed Accruals

- Update ServiceContract status based on total amount to accrue
- Skip further processing

#### 1.2 Active Contracts Without Service Periods

**When client is found in Notion:**

- Check educational status
- If not ended: Send notification or ignore if recent
- If ended: Accrue fully and update status accordingly

**When client is NOT found in Notion:**

- Recent contract (≤15 days): Send notification about missing CRM data
- Older contract: Process as resignation - accrue fully and mark as CANCELED

#### 1.3 Active Contracts With Service Periods

Process based on overlapping period status:

- **ACTIVE**: Accrue proportional amount for the month **based on remaining sessions and amounts**
- **POSTPONED**: Accrue until status change date, set accrual to PAUSED
- **DROPPED**: Accrue fully and mark contract as CANCELED
- **ENDED**: Accrue remaining amount and mark contract as CLOSED

### Case 2: Canceled Contracts (`ServiceContractStatus.CANCELED`)

#### 2.1 Canceled Contracts with Completed Accruals

- Skip processing

#### 2.2 Canceled Contracts Without Service Periods

- Check Notion integration
- Validate consistency with educational status
- Accrue fully if conditions are met
- For contracts not found in CRM and >15 days old: Process as resignation

#### 2.3 Canceled Contracts With Service Periods

- Validate that periods are DROPPED or POSTPONED
- Send notification if inconsistent statuses found
- Accrue fully if validation passes

### Case 3: Closed Contracts (`ServiceContractStatus.CLOSED`)

#### 3.1 Closed Contracts with Completed Accruals

- Skip processing

#### 3.2 Closed Contracts Without Service Periods

- Validate with Notion integration
- Ensure educational status is ENDED
- Accrue fully if validation passes
- **Critical Fix**: Apply same resignation logic as ACTIVE contracts for clients not found in CRM

#### 3.3 Closed Contracts With Service Periods

- Validate all periods are ENDED
- Send notification if inconsistent statuses found  
- Accrue fully if validation passes
- **Critical Fix**: Handle ENDED periods from previous years that need completion

### Case 4: Zero-Amount Contracts

**Scenario**: Contract amount is zero, typically for free courses, trials, or promotional offerings.

**Business Logic**: Zero-amount contracts still need proper CRM tracking and resignation processing.

**Processing Flow**:

1. **Recent contracts (≤15 days)**: Send notification about missing CRM data
2. **Older contracts (>15 days) without Notion profile**: Process as contract resignation
3. **Contracts with Notion profile and ended educational status**: Mark as completed
4. **Other cases**: Send notifications for manual review

**AccruedPeriod Creation**: Creates proper `AccruedPeriod` records for audit trail with amount 0.0.

### Case 5: Negative Contract Amounts

#### 5.1 Dropped Service Period Before Accrual

**Scenario**: Contract amount is negative and service period was dropped before any accrual occurred.

**Handling**: Full negative amount is accrued in one period, contract status set to CANCELED.

#### 5.2 Negative Contract Resignation

**Scenario**: Contract amount is negative, no service periods, profile not found in Notion, contract >15 days old.

**Handling**: Full negative amount accrued as resignation, contract status set to CANCELED.

## Critical Fixes for Historical Processing

### 1. Historical Processing Consistency Fix

**Problem**: The `_is_contract_recent` method was using `date.today()` instead of the target processing month, causing inconsistent behavior when processing historical data.

**Solution**: Updated to accept optional `target_month` parameter:

```python
def _is_contract_recent(self, contract_date: date, target_month: Optional[date] = None) -> bool:
    """Check if contract date is within 15 days of the target month end."""
    if target_month is None:
        reference_date = date.today()
    else:
        reference_date = get_month_end(target_month)
    
    return (reference_date - contract_date).days <= 15
```

### 2. CLOSED Contracts Without Service Periods - Resignation Detection

**Problem**: CLOSED contracts without service periods were missing resignation detection logic.

**Solution**: Enhanced `_process_closed_without_service_period` method to include the same resignation logic as ACTIVE contracts.

### 3. ENDED Service Periods from Previous Years

**Problem**: CLOSED contracts with ENDED service periods from previous years with incomplete accruals were being skipped.

**Solution**: Added special handling to process the most recent ENDED period when no overlapping periods exist but accrual is incomplete.

**Cases Resolved**:

- Multiple clients with contracts not found in CRM (resignation processing)
- Contracts with ENDED service periods from previous years (natural completion)

## Accrual Calculation Logic

### Key Principles

1. **Remaining-Based Calculations**: All calculations use remaining amounts and sessions
2. **Progressive Accrual**: Each period accrues from what's left, not the total
3. **Session-Based Proportions**: Monthly portions calculated based on session distribution

### Example Scenario

**Contract Details:**

- Total Amount: €10,000
- Total Sessions: 100
- Already Accrued: €7,000 (70 sessions)
- Remaining: €3,000 (30 sessions)

**Month Processing:**

- Sessions in Month: 15
- Portion: 15/30 = 50% (of remaining)
- Accrued Amount: €3,000 × 50% = €1,500

### Updated Methods

#### `_calculate_monthly_portion()`

```python
def _calculate_monthly_portion(self, contract_accrual: ContractAccrual, period: ServicePeriod, target_month: date) -> float:
    """Calculate portion based on remaining sessions."""
    sessions_in_overlap = period.get_sessions_between(overlap_start, overlap_end)
    remaining_sessions = contract_accrual.sessions_remaining_to_accrue
    
    if remaining_sessions <= 0:
        return 0.0
    
    return min(1.0, sessions_in_overlap / remaining_sessions)
```

#### `_accrue_portion()`

```python
def _accrue_portion(self, contract: ServiceContract, contract_accrual: ContractAccrual, portion: float, target_month: date, period: ServicePeriod) -> float:
    """Accrue from remaining amount, not total."""
    accrued_amount = contract_accrual.remaining_amount_to_accrue * portion
    
    # Update remaining amounts and sessions
    contract_accrual.total_amount_accrued += accrued_amount
    contract_accrual.remaining_amount_to_accrue -= accrued_amount
    contract_accrual.total_sessions_accrued += sessions_accrued
    contract_accrual.sessions_remaining_to_accrue -= sessions_accrued
```

## API Usage

### Process Contract Accruals

```http
POST /accruals/process-contracts
Content-Type: application/json

{
  "period_start_date": "2024-01-01"
}
```

**Response:**

```json
{
  "period_start_date": "2024-01-01",
  "summary": {
    "total_contracts_processed": 150,
    "successful_accruals": 120,
    "failed_accruals": 5,
    "skipped_accruals": 25
  },
  "processing_results": [
    {
      "contract_id": 1,
      "service_period_id": 10,
      "status": "SUCCESS",
      "message": "Accrued portion 50.00% - Amount: 1500.00"
    }
  ],
  "notifications": [
    {
      "type": "not_congruent_status",
      "message": "Contract 123 - Client without service period in CRM",
      "timestamp": "2024-01-15"
    }
  ]
}
```

### Get Processing Schema

```http
GET /accruals/process-contracts/schema
```

Returns the complete business logic schema documentation.

## Configuration

### Business Rules

- Contract recency threshold: 15 days
- Educational status mapping for ended states: `['GRADUATED', 'NOT_COMPLETING', 'ENDED']`

### Accrual Tracking Fields

- `total_amount_accrued`: Total amount accrued so far
- `remaining_amount_to_accrue`: Amount still to be accrued
- `total_sessions_accrued`: Sessions accrued so far
- `sessions_remaining_to_accrue`: Sessions still to be accrued

## Technical Implementation Details

### Performance Optimizations

#### Smart Contract Filtering

The system includes intelligent contract filtering to process only relevant contracts:

**Excluded Contracts:**

1. **Completed Contracts**: `CLOSED` or `CANCELED` contracts with `COMPLETED` accruals
2. **Non-Overlapping Periods**: Contracts with ServicePeriods that don't overlap with target month

**Critical Fix for Zero-Amount Contracts**: Modified filtering logic to include zero-amount contracts only if they haven't been processed yet:

```python
exclude_completed = and_(
    ServiceContract.status.in_([ServiceContractStatus.CLOSED, ServiceContractStatus.CANCELED]),
    exists().where(...accrual_status == ContractAccrualStatus.COMPLETED...),
    or_(
        ServiceContract.contract_amount != 0,  # Non-zero contracts: exclude when completed
        exists().where(  # Zero-amount contracts: exclude only if they have AccruedPeriod records
            AccruedPeriod.contract_accrual_id == ContractAccrualAlias.id
        )
    )
)
```

#### Query Optimization Features

- **Eager Loading**: All related entities loaded in single query
- **Selective Loading**: Only contracts needing processing are retrieved
- **Efficient Joins**: Optimized relationship loading with `selectinload`

### Code Quality Improvements - DRY Principle

The system has been refactored to follow the DRY (Don't Repeat Yourself) principle by extracting common patterns into reusable helper methods:

#### New Helper Methods

1. **`_handle_negative_amount_accrual()`** - Handles negative contract amounts with consistent logging
2. **`_handle_zero_amount_completion()`** - Handles zero remaining amount completion
3. **`_handle_contract_resignation()`** - Handles contract resignation scenarios
4. **`_handle_educational_status_accrual()`** - Handles accrual for ended educational status
5. **`_handle_full_accrual_with_status_update()`** - Handles full accrual with status updates
6. **`_handle_zero_amount_contract_resignation()`** - Handles zero-amount contract resignations

**Benefits:**

- Reduced ~200 lines of repetitive code
- Improved maintainability and consistency
- Better testability and readability
- Uniform error handling and logging

### Key Features

1. **Comprehensive Status Handling** - All ServiceContract and ServicePeriod statuses
2. **Integration Support** - Async Notion integration with proper error handling
3. **Robust Error Handling** - Comprehensive exception handling and logging
4. **Notification System** - Categorized notifications for manual review
5. **Audit Trail** - Complete AccruedPeriod records for all transactions

### Monitoring and Observability

#### Logging

- Structured logging with contract IDs and processing stages
- Error logging with full exception details
- Performance metrics for processing times
- Debug output for variable inspection (following user rule)

#### Metrics

- Processing statistics in response
- Success/failure rates
- Notification counts by type

#### Debugging

- Print statements for variable inspection
- Accrual calculation debug output
- Session and amount tracking logs

### Best Practices

#### Service Layer

- Single responsibility principle
- Dependency injection for database sessions
- Clear method naming and documentation
- Proper async handling for external integrations

#### Endpoint Layer

- Proper HTTP status codes
- Comprehensive error handling
- Input validation with Pydantic schemas
- Full async support

#### Data Layer

- Proper foreign key relationships
- Enum types for status fields
- Timestamp tracking for audit trails
- Incremental updates for remaining amounts and sessions

## Future Enhancements

1. **Batch Processing**: Support for processing specific contract sets
2. **Dry Run Mode**: Preview processing results without committing changes
3. **Retry Mechanism**: Automatic retry for failed contract processing
4. **Performance Optimization**: Bulk database operations for large datasets
5. **Advanced Notifications**: Email/Slack integration for critical notifications
6. **Accrual Validation**: Cross-check calculations against expected totals
7. **Historical Reporting**: Track accrual progression over time
