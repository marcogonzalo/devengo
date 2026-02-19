# Contract Accrual Processing System

## Overview

The accrual processing system handles ServiceContract processing based on status and ServicePeriods to generate accrual records.

**Core Principles:**

- Monthly portions calculated from **remaining sessions/amounts**, not totals
- Progressive accrual: each period accrues from what's left
- Session-based proportions for accurate distribution

## Architecture

```text
ContractAccrualProcessor (Service Layer)
├── process_all_contracts() - Main orchestrator
├── _process_contract() - Route by contract status
├── _process_*_contract() - Status-specific handlers
└── _process_*_service_period() - Period-specific handlers

Endpoints:
├── POST /accruals/process-contracts - Process accruals
└── GET /accruals/process-contracts/schema - Documentation

Models:
├── ServiceContract ↔ ContractAccrual (1:1)
├── ContractAccrual → AccruedPeriod (1:N)
└── ServiceContract → ServicePeriod (1:N)
```

## Processing Flow

### 1. Contract Filtering

```text
All Contracts
├── ❌ Not started (contract_date > month_end)
├── ❌ Completed (CLOSED/CANCELED + COMPLETED accrual)
└── ✅ Processable Contracts
    ├── Has overlapping periods
    ├── Recent contracts (≤15 days)
    ├── Has DROPPED periods in target month
    ├── ISA Full-Time contracts
    └── Has POSTPONED periods (time limit check)
```

### 2. Contract Status Routing

```text
ServiceContract Status
├── ACTIVE → _process_active_contract()
├── CANCELED → _process_canceled_contract()
└── CLOSED → _process_closed_contract()
```

## Processing Cases

### Case 1: ACTIVE Contracts

#### 1.1 Completed Accruals

```text
Condition: contract_accrual.accrual_status == COMPLETED
Action: Update ServiceContract status
├── total_to_accrue > 0 → CLOSED
└── total_to_accrue ≤ 0 → CANCELED
```

#### 1.2 Without Service Periods

```text
Client in Notion?
├── YES → Check educational status
│   ├── ENDED → Accrue fully + update status
│   └── NOT ENDED → Skip (recent) or notify
└── NO → Resignation processing
    ├── Recent (≤15 days) → Notify missing CRM
    └── Old (>15 days) → Accrue fully + CANCELED
```

#### 1.3 With Service Periods

```text
Overlapping Period Status:
├── ACTIVE → Accrue proportional amount
├── POSTPONED → Accrue until status_change_date + PAUSED
├── DROPPED → Accrue fully + CANCELED
└── ENDED → Accrue full remaining + CLOSED
```

### Case 2: CANCELED Contracts

#### 2.1 Completed Accruals

```text
Condition: contract_accrual.accrual_status == COMPLETED
Action: Skip processing
```

#### 2.2 Without Service Periods

```text
Client in Notion?
├── YES → Validate educational status
│   ├── ENDED/DROPPED → Accrue fully + CLOSED
│   └── NOT ENDED → Notify + skip
└── NO → Resignation processing
    └── Accrue fully + CANCELED
```

#### 2.3 With Service Periods

```text
Period Status Check:
├── DROPPED/POSTPONED → Accrue fully + CANCELED
└── ACTIVE/ENDED → Notify + skip
```

### Case 3: CLOSED Contracts

#### 3.1 Completed Accruals

```text
Condition: contract_accrual.accrual_status == COMPLETED
Action: Skip processing
```

#### 3.2 Without Service Periods

```text
Client in Notion?
├── YES → Validate educational status
│   ├── ENDED → Accrue fully + CLOSED
│   └── NOT ENDED → Notify + skip
└── NO → Resignation processing
    ├── Recent (≤15 days) → Notify missing CRM
    └── Old (>15 days) → Accrue fully + CANCELED
```

#### 3.3 With Service Periods

```text
Period Status Check:
├── ENDED → Accrue fully + CLOSED
└── ACTIVE/POSTPONED/DROPPED → Notify + skip
```

## Special Cases

### Zero-Amount Contracts

```text
Condition: contract.contract_amount == 0
Processing:
├── Recent (≤15 days) → Notify missing CRM
├── Old (>15 days) + No Notion → Resignation processing
├── Has Notion + ENDED → Mark completed
└── Other cases → Notify for manual review
```

### Negative Amount Contracts

```text
Condition: contract_accrual.remaining_amount_to_accrue < 0
Processing:
├── Dropped before accrual → Full negative accrual + CANCELED
└── Resignation → Full negative accrual + CANCELED
```

### Postponed Period Time Limits

```text
Condition: Last postponed period > 3 months
Processing:
├── Check if period exceeded POSTPONED_PERIOD_MAX_MONTHS
├── Verify it's the last service period
└── Accrue fully + CANCELED
```

### ISA Full-Time Contracts

```text
Condition: service.name == "ES - ISA - Full-Time"
Processing:
├── Check for new invoices in target month
├── Recalculate remaining amount if completed
└── Process new accruals
```

## Accrual Calculation

### Monthly Portion Calculation

```text
portion = sessions_in_overlap / remaining_sessions
accrued_amount = remaining_amount_to_accrue × portion
```

### Example

```text
Contract: €10,000 total, 100 sessions
Already accrued: €7,000 (70 sessions)
Remaining: €3,000 (30 sessions)

Month processing:
- Sessions in month: 15
- Portion: 15/30 = 50%
- Accrued: €3,000 × 50% = €1,500
```

## Constants & Configuration

### Time-Based Constants

```python
class AccrualTimeConstants:
    CONTRACT_RECENCY_DAYS = 15
    POSTPONED_PERIOD_MAX_MONTHS = 3
    CONTRACT_WITHOUT_PERIODS_MAX_MONTHS = 3
```

### Status Mappings

```python
ServiceContractStatus: ACTIVE, CANCELED, CLOSED
ServicePeriodStatus: ACTIVE, POSTPONED, DROPPED, ENDED
ContractAccrualStatus: ACTIVE, PAUSED, COMPLETED
```

## API Usage

### Process Accruals

```http
POST /accruals/process-contracts
{
  "period_start_date": "2024-01-01"
}
```

### Response Structure

```json
{
  "period_start_date": "2024-01-01",
  "summary": {
    "total_contracts_processed": 150,
    "successful_accruals": 120,
    "failed_accruals": 5,
    "skipped_accruals": 25
  },
  "processing_results": [...],
  "notifications": [...]
}
```

## Critical Fixes

### 1. Historical Processing Consistency

**Problem**: `_is_contract_recent()` used `date.today()` instead of target month
**Fix**: Added optional `target_month` parameter for historical processing

### 2. CLOSED Contracts Resignation Detection

**Problem**: Missing resignation logic for CLOSED contracts without service periods
**Fix**: Applied same resignation logic as ACTIVE contracts

### 3. Postponed Period Time Limits

**Problem**: Postponed periods exceeding 3 months not being processed
**Fix**: Added time limit checking and full accrual for exceeded periods

### 4. Non-Overlapping Postponed Periods

**Problem**: Postponed periods without target month overlap being skipped
**Fix**: Added processing logic for non-overlapping postponed periods

## Helper Methods

### Core Processing

- `_process_*_contract()` - Status-specific handlers
- `_process_*_service_period()` - Period-specific handlers
- `_handle_*_accrual()` - Special case handlers

### Validation & Checks

- `_is_contract_recent()` - Contract recency check
- `_has_postponed_period_exceeded_max_months()` - Time limit check
- `_is_last_service_period()` - Last period validation

### Calculation

- `_calculate_monthly_portion()` - Session-based portion calculation
- `_accrue_portion()` - Progressive accrual from remaining amounts
- `_accrue_fully()` - Complete remaining amount accrual

## Error Handling

### Notifications

- `not_congruent_status` - Status inconsistencies
- `missing_crm_data` - Client not found in Notion
- `processing_error` - System errors

### Logging

- Structured logging with contract IDs
- Performance metrics
- Debug output for variable inspection

## Performance Optimizations

### Smart Filtering

- Exclude completed contracts
- Include only relevant periods
- Eager loading of relationships

### Query Optimization

- Single query with `selectinload`
- Selective contract retrieval
- Efficient joins and filtering
