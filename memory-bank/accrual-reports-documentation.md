# Accrual Reports and CSV Generation System

## Overview

This document describes the accrual reporting system that generates comprehensive CSV reports showing all accrued periods within a date range, including contracts that have not been fully accrued before the date range. The system provides detailed financial tracking with monthly breakdowns grouped by client, contract, and service period.

**Key Features:**

- **Comprehensive Coverage**: Shows all accrued periods in date range + contracts not fully accrued
- **Monthly Breakdown**: Columns represent months with accrual amounts
- **Hierarchical Grouping**: Rows grouped by client → contract → service period
- **Edge Case Handling**: Handles contracts without periods, NULL accruals, and complex scenarios
- **Data Integrity**: Redistributes NULL period accruals to correct service periods

## Architecture

### Service Layer

- **`AccrualReportsService`**: Main service class for report generation
- Located in: `src/api/accruals/services/accrual_reports_service.py`
- **CSV Generation**: Direct CSV output with proper formatting
- **Data Aggregation**: Complex queries with multiple joins and conditions

### Endpoint Layer

- **`/accruals/export/csv`**: Main endpoint for CSV export
- **Query Parameters**: `start_date` and `end_date` (inclusive)
- **Response**: CSV file with proper headers and filename
- Located in: `src/api/accruals/endpoints/accruals.py`

### Data Models

- **`AccruedPeriod`**: Individual accrual transactions with amounts and dates
- **`ContractAccrual`**: Contract-level accrual tracking
- **`ServiceContract`**: Contract information and status
- **`ServicePeriod`**: Service delivery periods with status tracking
- **`Client`**: Client information for grouping
- **`Service`**: Service type information

## CSV Report Algorithm

### Step 1: Contract Selection Logic

The algorithm uses a sophisticated query to include contracts that meet ANY of these conditions:

#### Condition 1: Contracts with Accruals in Date Range

```sql
ContractAccrual.id IN (
    SELECT DISTINCT contract_accrual_id
    FROM AccruedPeriod
    WHERE accrual_date BETWEEN start_date AND end_date
)
```

#### Condition 2: Contracts Not Fully Accrued

```sql
(ServiceContract.contract_date <= end_date) AND
(
    (ContractAccrual.id IS NULL) OR  -- New contracts without accrual records
    (ContractAccrual.accrual_status != 'COMPLETED')  -- Incomplete accruals
)
```

**This ensures the report includes:**

- All contracts that had accruals in the date range
- All contracts that were created before/during the date range but haven't been fully accrued
- Contracts without accrual records yet (new contracts)

### Step 2: Data Organization and Processing

#### 2.1 Accrual Data Collection

- Query all `AccruedPeriod` records in the date range
- Create mapping: `(contract_accrual_id, service_period_id) → {month_key: amount}`
- Handle NULL service_period_id accruals (final accruals without specific periods)

#### 2.2 NULL Period Redistribution

The algorithm handles a critical edge case where final accruals have `service_period_id = NULL`:

**Redistribution Logic:**

1. **Find overlapping periods**: Look for service periods that overlap with the accrual date
2. **Use most recent period**: If no overlap, assign to the most recent service period
3. **Keep as NULL**: If no service periods exist, keep as NULL (handled as "No Period")

**Example:**

```text
NULL accrual on 2024-03-15 → Find period that overlaps with March 2024
If found: Move amount to that period's row
If not found: Move to most recent period (e.g., ended in January 2024)
```

#### 2.3 Monthly Column Generation

- Generate all months between `start_date` and `end_date`
- Format: `YYYY-MM` keys with `"Month YYYY"` display names
- Ensure complete month coverage even if no accruals in certain months

### Step 3: CSV Row Generation

#### 3.1 Row Structure

Each row represents a **client-contract-service_period** combination:

**Fixed Columns:**

- Contract start date
- Client name
- Client email
- Contract status
- Service name
- Period name (or "No Period")
- Period status
- Status change date
- Total to accrue
- Pending to accrue
- Period start date
- Period end date

**Dynamic Columns:**

- One column per month in date range (e.g., "January 2024", "February 2024")

#### 3.2 Grouping Logic

- **Primary Group**: Client name
- **Secondary Group**: Contract (by contract ID)
- **Tertiary Group**: Service period (by period ID or NULL)

**Row Deduplication:**

- Only show contract-level data (start date, client, etc.) on first occurrence
- Subsequent rows for same contract show empty values for contract-level fields
- This creates a hierarchical view: Client → Contract → Period

#### 3.3 Data Population

```python
# For each contract-period combination
period_id = period.id if period else None
contract_accrual_id = contract_accrual.id if contract_accrual else None
key = (contract_accrual_id, period_id)
period_accruals = accruals_by_contract_period.get(key, {})

# Populate monthly amounts
for month_key, month_name in months:
    row[month_name] = period_accruals.get(month_key, 0.0)
```

## Business Logic Integration

### Contract Status Handling

The report respects the same business logic as the accrual processor:

#### Active Contracts

- Show pending amounts from `ContractAccrual.remaining_amount_to_accrue`
- Display accrual status and completion progress
- Include contracts that haven't been processed yet

#### Canceled/Closed Contracts

- Show final accrual amounts
- Include contracts that were processed during the date range
- Display status changes and completion dates

#### Contracts Without Periods

- Handle "No Period" cases for contracts without service periods
- Show accruals that were processed based on Notion integration or resignation logic
- Include zero-amount contracts with proper audit trails

### Edge Cases Handled

#### 1. Contracts Without ContractAccrual Records

- New contracts that haven't been processed yet
- Show contract amount as "Pending to accrue"
- Include in report for visibility

#### 2. NULL Service Period Accruals

- Final accruals that don't belong to specific periods
- Redistributed to appropriate periods when possible
- Kept as "No Period" when no redistribution possible

#### 3. Multiple Service Periods

- Contracts with overlapping or sequential periods
- Each period gets its own row
- Proper chronological ordering

#### 4. Zero-Amount Contracts

- Contracts with zero contract amounts
- Still included for audit trail
- Show proper status progression

## CSV Output Format

### File Structure

```txt
accruals_YYYY-MM-DD_YYYY-MM-DD.csv
```

### Column Headers

```txt
Contract start date,Client,Email,Contract Status,Service,Period,Period Status,Status Change Date,Total to accrue,Pending to accrue,Period start date,Period end date,January 2024,February 2024,March 2024,...
```

### Sample Data

```csv
2024-01-15,John Doe,john@example.com,ACTIVE,Programming Course,Spring 2024,ACTIVE,,1000.00,750.00,2024-01-15,2024-06-15,250.00,250.00,250.00,0.00,0.00,0.00
,,,ACTIVE,Programming Course,Summer 2024,ACTIVE,,1000.00,750.00,2024-07-01,2024-12-31,0.00,0.00,0.00,250.00,250.00,250.00
2024-02-01,Jane Smith,jane@example.com,CANCELED,Design Course,Winter 2024,DROPPED,2024-03-15,800.00,0.00,2024-02-01,2024-05-01,200.00,200.00,400.00,0.00,0.00,0.00
```

## Performance Considerations

### Query Optimization

- **Eager Loading**: All related entities loaded in single query
- **Efficient Joins**: Left joins to include contracts without periods/accruals
- **Indexed Fields**: Date ranges and foreign keys properly indexed
- **Distinct Queries**: Separate queries for contracts and accruals to avoid N+1

### Memory Management

- **Streaming CSV**: Direct StringIO output without storing full dataset
- **Batch Processing**: Process contracts in manageable chunks
- **Efficient Data Structures**: Use defaultdict for accrual mapping

### Scalability

- **Date Range Limiting**: Reasonable date range constraints
- **Pagination Support**: Ready for large dataset pagination
- **Caching Opportunities**: Dashboard summaries can be cached

## Technical Implementation Notes

### Database Schema Considerations

- **AccruedPeriod Indexes**: Optimize for date range queries
- **ContractAccrual Status**: Index for completion status filtering
- **ServicePeriod Overlaps**: Efficient overlap detection queries
- **Client Relationships**: Optimize for client-based grouping

### Error Handling

- **Missing Data**: Graceful handling of NULL values
- **Data Inconsistencies**: Validation and correction logic
- **Large Datasets**: Memory-efficient processing
- **Export Failures**: Proper error reporting and recovery

### Testing Strategy

- **Unit Tests**: Individual method testing
- **Integration Tests**: End-to-end CSV generation
- **Performance Tests**: Large dataset processing
- **Edge Case Tests**: NULL periods, zero amounts, etc.

## Conclusion

The accrual reports system provides comprehensive financial tracking with sophisticated data handling for complex business scenarios. The CSV generation algorithm ensures complete coverage of all relevant contracts while maintaining data integrity and providing clear hierarchical organization for analysis and reporting.

The system is designed for extensibility, with clear separation of concerns and well-defined interfaces for future enhancements. The business logic integration ensures consistency with the accrual processing system while providing the detailed reporting needed for financial management and compliance.
