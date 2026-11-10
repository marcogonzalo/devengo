# Internal Service Periods

Allowlisted Holded services (starting with AI Flex, `accountNum` `70501003`) skip CRM enrollment sync and use invoice-driven 12-month generic periods with period-scoped accrual.

## Quick path

1. Holded `sync-services` sets `Service.internal_service_periods=True` when `account_identifier` is in the allowlist (`INTERNAL_SERVICE_PERIOD_ACCOUNT_NUMBERS`).
2. Holded `sync-invoices-and-clients` creates/adjusts generic `ServicePeriod`s for those services (one per positive invoice).
3. FourGeeks `sync-enrollments-from-clients` skips contracts whose service has `internal_service_periods=True`.
4. Monthly accruals use `accrual_pending_amount / remaining_months_until_end_date` per overlapping ACTIVE period.
5. Period end month → `ENDED`; contract → `CLOSED` only when **all** periods are `ENDED`.

## Rules

| Topic                         | Decision                                                                                            |
| ----------------------------- | --------------------------------------------------------------------------------------------------- |
| Who opts in                   | Holded `account_identifier` allowlist in `src/api/common/constants/services.py` (start: `70501003`) |
| Default                       | `Service.internal_service_periods=False`                                                            |
| CRM                           | Skipped entirely for flagged services                                                               |
| Period source                 | Invoices, not 4Geeks enrollments                                                                    |
| Period identity               | `name` / `external_id` = `invoice_number`                                                           |
| Period window                 | Start = invoice date; end = last day of the 12th calendar month from the start month                |
| Amount                        | `ServicePeriod.period_amount` = invoice total                                                       |
| Open contract + new invoice   | Same client+service: add amount, create another generic period                                      |
| Closed contract + new invoice | New `ServiceContract` + new period (never reopen `CLOSED`)                                          |
| Credit note                   | Adjust matching period's `period_amount` (no new period)                                            |
| Monthly accrual               | `pending / remaining_months` (inclusive of target month through end month)                          |
| Period close                  | Accrual month reaches `end_date` while `ACTIVE` → `ENDED`, `status_change_date=end_date`            |
| Contract close                | Only when every period on the contract is `ENDED`                                                   |

## Sync behavior

### Services (`/api/integrations/holded/sync-services`)

- Sets `internal_service_periods` from allowlist.
- Runs `backfill_internal_service_periods()` afterward: flags existing allowlisted services and creates missing generic periods from linked invoices.

### Invoices (`/api/integrations/holded/sync-invoices-and-clients`)

For `internal_service_periods=True`:

1. Resolve **open** (non-`CLOSED`) contract via `get_open_service_contract_by_client_and_service`.
2. If none → create contract from the invoice.
3. If open → update contract amount / accrual totals.
4. On new invoice document → create generic period (or adjust amount on credit note).

Helper: `src/api/services/services/internal_service_period_service.py`.

### CRM enrollments (`/api/integrations/fourgeeks/sync-enrollments-from-clients`)

- Endpoint skips flagged contracts before calling 4Geeks.
- `EnrollmentProcessor.process_enrollment` also refuses flagged contracts defensively.

## Accrual behavior

Entry: `ContractAccrualProcessor._process_contract_with_service_periods` routes to `_process_internal_service_periods_contract` when `contract.service.internal_service_periods` is true.

For each overlapping `ACTIVE` period in the target month:

1. `accrual_pending_amount = period_amount - sum(AccruedPeriod for that period)`
2. `remaining_months = max(1, months from target_month through end_date month inclusive)`
3. Accrue `accrual_pending_amount / remaining_months`
4. If `end_date` falls in (or before) the target month → set `ENDED` and flush remaining pending

Contract and `ContractAccrual` complete only when all periods are `ENDED` and remaining amount ≈ 0.

## Add another allowlisted service

1. Add its Holded `accountNum` to `INTERNAL_SERVICE_PERIOD_ACCOUNT_NUMBERS`.
2. Re-run `sync-services` (backfill flags + periods).
3. Re-run invoice sync if needed.

## Code map

| Area               | Location                                                                          |
| ------------------ | --------------------------------------------------------------------------------- |
| Allowlist / helper | `src/api/common/constants/services.py`                                            |
| Models             | `Service.internal_service_periods`, `ServicePeriod.period_amount`                 |
| Invoice → period   | `internal_service_period_service.py`, Holded sync                                 |
| Skip CRM           | `fourgeeks` endpoint + `EnrollmentProcessor`                                      |
| Accrual            | `contract_accrual_processor.py` (`_process_internal_service_periods_contract`)    |
| Migration          | `migrations/versions/20261110160000-b1c2d3e4f5a6_add_internal_service_periods.py` |
| Tests              | `tests/test_internal_service_periods.py`                                          |

## Checklist

- [ ] Allowlisted service shows `internal_service_periods=True` after `sync-services`
- [ ] New invoice creates a period named with `invoice_number` and a 12-month calendar window
- [ ] Second invoice on an open contract adds a second period
- [ ] Credit note changes `period_amount`, does not add a period
- [ ] Invoice after `CLOSED` creates a new contract
- [ ] Accrual month uses pending/remaining-months; last period end closes the contract
