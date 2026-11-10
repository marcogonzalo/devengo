"""Helpers for invoice-driven internal (generic) service periods."""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from dateutil.relativedelta import relativedelta
from fastapi.logger import logger
from sqlmodel import Session, select

from src.api.common.constants.services import (
    INTERNAL_SERVICE_PERIOD_ACCOUNT_NUMBERS,
    INTERNAL_SERVICE_PERIOD_MONTHS,
    ServiceContractStatus,
    ServicePeriodStatus,
)
from src.api.invoices.models.invoice import Invoice
from src.api.services.models.service import Service
from src.api.services.models.service_contract import ServiceContract
from src.api.services.models.service_period import ServicePeriod
from src.api.services.schemas.service_period import ServicePeriodCreate, ServicePeriodUpdate
from src.api.services.services.service_period_service import ServicePeriodService


def compute_internal_period_end_date(start_date: date) -> date:
    """
    Return end date for an internal generic period covering N calendar months.

    Start month counts as month 1; end is the last day of month N
    (e.g. 2024-01-15 → 2024-12-31 for 12 months).
    """
    month_start = start_date.replace(day=1)
    return (
        month_start
        + relativedelta(months=INTERNAL_SERVICE_PERIOD_MONTHS)
        - relativedelta(days=1)
    )


def _referenced_invoice_number(document: Dict[str, Any]) -> Optional[str]:
    """Extract the original invoice docNumber from a Holded credit note document."""
    from_data = document.get("from") or {}
    if isinstance(from_data, dict):
        doc_number = from_data.get("docNumber") or from_data.get("number")
        if doc_number:
            return str(doc_number)
    return None


def _find_period_for_credit_note(
    period_service: ServicePeriodService,
    contract: ServiceContract,
    document: Dict[str, Any],
) -> Optional[ServicePeriod]:
    """Locate the generic period a credit note should adjust."""
    referenced_number = _referenced_invoice_number(document)
    if referenced_number:
        period = period_service.get_period_by_external_id(
            contract.id, referenced_number)
        if period:
            return period

    periods = period_service.get_periods_by_contract(contract.id)
    active_periods = [p for p in periods if p.status ==
                      ServicePeriodStatus.ACTIVE]
    if active_periods:
        return max(active_periods, key=lambda p: (p.start_date, p.id or 0))
    if periods:
        return max(periods, key=lambda p: (p.start_date, p.id or 0))
    return None


def sync_internal_service_period_for_invoice(
    *,
    document: Dict[str, Any],
    invoice: Invoice,
    service_contract: ServiceContract,
    period_service: ServicePeriodService,
    is_credit_note: bool,
) -> Optional[ServicePeriod]:
    """
    Create or adjust an internal generic service period for an invoice/credit note.

    - Regular invoice: idempotent create of 12-month period keyed by invoice_number
    - Credit note: adjust matching period's period_amount (no new period)
    """
    if is_credit_note:
        period = _find_period_for_credit_note(
            period_service, service_contract, document)
        if not period:
            logger.warning(
                "No internal service period found for credit note %s on contract %s",
                invoice.invoice_number,
                service_contract.id,
            )
            return None

        current_amount = period.period_amount or 0.0
        updated_amount = current_amount + invoice.total_amount
        return period_service.update_period(
            period.id,
            ServicePeriodUpdate(period_amount=updated_amount),
        )

    existing = period_service.get_period_by_external_id(
        service_contract.id, invoice.invoice_number
    )
    if existing:
        # Keep amount in sync if period already exists (idempotent re-sync)
        if existing.period_amount != invoice.total_amount:
            return period_service.update_period(
                existing.id,
                ServicePeriodUpdate(period_amount=invoice.total_amount),
            )
        return existing

    period_data = ServicePeriodCreate(
        contract_id=service_contract.id,
        name=invoice.invoice_number,
        external_id=invoice.invoice_number,
        start_date=invoice.invoice_date,
        end_date=compute_internal_period_end_date(invoice.invoice_date),
        status=ServicePeriodStatus.ACTIVE,
        period_amount=invoice.total_amount,
    )
    return period_service.create_period(period_data)


def backfill_internal_service_periods(db: Session) -> Dict[str, int]:
    """
    Backfill internal_service_periods flag and generic periods for allowlisted services.

    - Sets Service.internal_service_periods=True for allowlisted account_identifiers
    - For each non-CLOSED contract, creates one generic period per positive invoice
    - Applies negative invoices (credit notes) against matching periods
    """
    period_service = ServicePeriodService(db)
    stats = {
        "services_flagged": 0,
        "periods_created": 0,
        "periods_adjusted": 0,
        "contracts_processed": 0,
    }

    services = db.exec(
        select(Service).where(
            Service.account_identifier.in_(
                list(INTERNAL_SERVICE_PERIOD_ACCOUNT_NUMBERS))
        )
    ).all()

    for service in services:
        if not service.internal_service_periods:
            service.internal_service_periods = True
            db.add(service)
            stats["services_flagged"] += 1

        contracts = db.exec(
            select(ServiceContract).where(
                ServiceContract.service_id == service.id,
                ServiceContract.status != ServiceContractStatus.CLOSED,
            )
        ).all()

        for contract in contracts:
            stats["contracts_processed"] += 1
            invoices: List[Invoice] = db.exec(
                select(Invoice).where(
                    Invoice.service_contract_id == contract.id)
            ).all()

            positive = [inv for inv in invoices if inv.total_amount > 0]
            credit_notes = [inv for inv in invoices if inv.total_amount < 0]

            for invoice in positive:
                existing = period_service.get_period_by_external_id(
                    contract.id, invoice.invoice_number
                )
                if existing:
                    continue
                period_service.create_period(
                    ServicePeriodCreate(
                        contract_id=contract.id,
                        name=invoice.invoice_number,
                        external_id=invoice.invoice_number,
                        start_date=invoice.invoice_date,
                        end_date=compute_internal_period_end_date(
                            invoice.invoice_date),
                        status=ServicePeriodStatus.ACTIVE,
                        period_amount=invoice.total_amount,
                    )
                )
                stats["periods_created"] += 1

            for credit_note in credit_notes:
                document = credit_note.original_data or {}
                if not isinstance(document, dict):
                    document = {}
                # Ensure referenced invoice number is available for matching
                if "from" not in document and credit_note.invoice_number:
                    # Try match by stripping CN prefix heuristics is unreliable; use fallback
                    document = {"from": {}}
                period = _find_period_for_credit_note(
                    period_service, contract, document)
                if not period and positive:
                    # Fallback: adjust most recent period
                    periods = period_service.get_periods_by_contract(
                        contract.id)
                    if periods:
                        period = max(periods, key=lambda p: (
                            p.start_date, p.id or 0))
                if period:
                    current = period.period_amount or 0.0
                    period_service.update_period(
                        period.id,
                        ServicePeriodUpdate(
                            period_amount=current + credit_note.total_amount),
                    )
                    stats["periods_adjusted"] += 1

    db.commit()
    return stats
