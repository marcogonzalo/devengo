"""Tests for internal service periods (AI Flex / allowlisted accountNums)."""

from datetime import date
from unittest.mock import Mock

import pytest

from src.api.accruals.constants.accruals import ContractAccrualStatus
from src.api.accruals.models.accrued_period import AccruedPeriod
from src.api.accruals.models.contract_accrual import ContractAccrual
from src.api.accruals.schemas import ProcessingStatus
from src.api.accruals.services.contract_accrual_processor import ContractAccrualProcessor
from src.api.common.constants.services import (
    INTERNAL_SERVICE_PERIOD_ACCOUNT_NUMBERS,
    INTERNAL_SERVICE_PERIOD_MONTHS,
    ServiceContractStatus,
    ServicePeriodStatus,
    uses_internal_service_periods,
)
from src.api.integrations.fourgeeks.processor import EnrollmentProcessor
from src.api.invoices.models.invoice import Invoice
from src.api.services.models.service_contract import ServiceContract
from src.api.services.models.service_period import ServicePeriod
from src.api.services.services.internal_service_period_service import (
    backfill_internal_service_periods,
    compute_internal_period_end_date,
    sync_internal_service_period_for_invoice,
)
from src.api.services.services.service_contract import ServiceContractService
from src.api.services.services.service_period_service import ServicePeriodService
from src.api.services.services.service_service import ServiceService


class TestInternalServicePeriodConstants:
    def test_allowlist_contains_ai_flex_account(self):
        assert "70501003" in INTERNAL_SERVICE_PERIOD_ACCOUNT_NUMBERS

    def test_uses_internal_service_periods_true_for_allowlisted(self):
        assert uses_internal_service_periods("70501003") is True

    def test_uses_internal_service_periods_false_by_default(self):
        assert uses_internal_service_periods(None) is False
        assert uses_internal_service_periods("70501001") is False

    def test_duration_is_twelve_months(self):
        assert INTERNAL_SERVICE_PERIOD_MONTHS == 12
        # Start month counts as month 1 → last day of month 12
        assert compute_internal_period_end_date(
            date(2024, 1, 15)) == date(2024, 12, 31)
        assert compute_internal_period_end_date(
            date(2024, 3, 10)) == date(2025, 2, 28)


class TestServiceInternalFlag:
    def test_create_service_defaults_false(self, test_session):
        service = ServiceService(test_session).create_service(
            {
                "external_id": "svc-1",
                "name": "ES - Full-Stack",
                "account_identifier": "70501001",
            }
        )
        assert service.internal_service_periods is False

    def test_create_service_sets_true_for_allowlisted_account(self, test_session):
        service = ServiceService(test_session).create_service(
            {
                "external_id": "svc-ai-flex",
                "name": "ES - AI Flex",
                "account_identifier": "70501003",
            }
        )
        assert service.internal_service_periods is True


class TestOpenContractLookup:
    def test_prefers_non_closed_contract(self, test_session, test_data_factory):
        client = test_data_factory.create_client(test_session)
        service = test_data_factory.create_service(
            test_session,
            account_identifier="70501003",
            internal_service_periods=True,
            name="ES - AI Flex",
            external_id="ai-flex-1",
        )
        closed = ServiceContract(
            client_id=client.id,
            service_id=service.id,
            contract_date=date(2023, 1, 1),
            contract_amount=100.0,
            status=ServiceContractStatus.CLOSED,
        )
        open_contract = ServiceContract(
            client_id=client.id,
            service_id=service.id,
            contract_date=date(2024, 1, 1),
            contract_amount=200.0,
            status=ServiceContractStatus.ACTIVE,
        )
        test_session.add(closed)
        test_session.add(open_contract)
        test_session.commit()

        svc = ServiceContractService(test_session)
        found = svc.get_open_service_contract_by_client_and_service(
            client.id, service.id)
        assert found is not None
        assert found.id == open_contract.id

    def test_returns_none_when_only_closed(self, test_session, test_data_factory):
        client = test_data_factory.create_client(test_session)
        service = test_data_factory.create_service(
            test_session,
            account_identifier="70501003",
            internal_service_periods=True,
            external_id="ai-flex-2",
        )
        closed = ServiceContract(
            client_id=client.id,
            service_id=service.id,
            contract_date=date(2023, 1, 1),
            contract_amount=100.0,
            status=ServiceContractStatus.CLOSED,
        )
        test_session.add(closed)
        test_session.commit()

        found = ServiceContractService(test_session).get_open_service_contract_by_client_and_service(
            client.id, service.id
        )
        assert found is None


class TestSyncInternalServicePeriodForInvoice:
    def test_creates_generic_period_from_invoice(self, test_session, test_data_factory):
        client = test_data_factory.create_client(test_session)
        service = test_data_factory.create_service(
            test_session,
            account_identifier="70501003",
            internal_service_periods=True,
            external_id="ai-flex-3",
        )
        contract = ServiceContract(
            client_id=client.id,
            service_id=service.id,
            contract_date=date(2024, 3, 1),
            contract_amount=1200.0,
            status=ServiceContractStatus.ACTIVE,
        )
        test_session.add(contract)
        test_session.commit()
        test_session.refresh(contract)

        invoice = test_data_factory.create_invoice(
            test_session,
            client_id=client.id,
            service_contract_id=contract.id,
            invoice_number="F-2024-100",
            invoice_date=date(2024, 3, 10),
            total_amount=1200.0,
            external_id="holded-inv-100",
        )
        period_service = ServicePeriodService(test_session)
        period = sync_internal_service_period_for_invoice(
            document={},
            invoice=invoice,
            service_contract=contract,
            period_service=period_service,
            is_credit_note=False,
        )
        assert period is not None
        assert period.external_id == "F-2024-100"
        assert period.name == "F-2024-100"
        assert period.start_date == date(2024, 3, 10)
        assert period.end_date == date(2025, 2, 28)
        assert period.period_amount == 1200.0
        assert period.status == ServicePeriodStatus.ACTIVE

    def test_second_invoice_adds_second_period(self, test_session, test_data_factory):
        client = test_data_factory.create_client(test_session)
        service = test_data_factory.create_service(
            test_session,
            account_identifier="70501003",
            internal_service_periods=True,
            external_id="ai-flex-4",
        )
        contract = ServiceContract(
            client_id=client.id,
            service_id=service.id,
            contract_date=date(2024, 3, 1),
            contract_amount=2400.0,
            status=ServiceContractStatus.ACTIVE,
        )
        test_session.add(contract)
        test_session.commit()
        test_session.refresh(contract)

        period_service = ServicePeriodService(test_session)
        inv1 = test_data_factory.create_invoice(
            test_session,
            client_id=client.id,
            service_contract_id=contract.id,
            invoice_number="F-1",
            invoice_date=date(2024, 3, 1),
            total_amount=1200.0,
            external_id="inv-1",
        )
        inv2 = test_data_factory.create_invoice(
            test_session,
            client_id=client.id,
            service_contract_id=contract.id,
            invoice_number="F-2",
            invoice_date=date(2024, 6, 1),
            total_amount=1200.0,
            external_id="inv-2",
        )
        p1 = sync_internal_service_period_for_invoice(
            document={},
            invoice=inv1,
            service_contract=contract,
            period_service=period_service,
            is_credit_note=False,
        )
        p2 = sync_internal_service_period_for_invoice(
            document={},
            invoice=inv2,
            service_contract=contract,
            period_service=period_service,
            is_credit_note=False,
        )
        periods = period_service.get_periods_by_contract(contract.id)
        assert len(periods) == 2
        assert {p1.external_id, p2.external_id} == {"F-1", "F-2"}

    def test_credit_note_adjusts_period_amount(self, test_session, test_data_factory):
        client = test_data_factory.create_client(test_session)
        service = test_data_factory.create_service(
            test_session,
            account_identifier="70501003",
            internal_service_periods=True,
            external_id="ai-flex-5",
        )
        contract = ServiceContract(
            client_id=client.id,
            service_id=service.id,
            contract_date=date(2024, 3, 1),
            contract_amount=1000.0,
            status=ServiceContractStatus.ACTIVE,
        )
        test_session.add(contract)
        test_session.commit()
        test_session.refresh(contract)

        period_service = ServicePeriodService(test_session)
        invoice = test_data_factory.create_invoice(
            test_session,
            client_id=client.id,
            service_contract_id=contract.id,
            invoice_number="F-200",
            invoice_date=date(2024, 3, 1),
            total_amount=1200.0,
            external_id="inv-200",
        )
        sync_internal_service_period_for_invoice(
            document={},
            invoice=invoice,
            service_contract=contract,
            period_service=period_service,
            is_credit_note=False,
        )
        credit = test_data_factory.create_invoice(
            test_session,
            client_id=client.id,
            service_contract_id=contract.id,
            invoice_number="CN-200",
            invoice_date=date(2024, 4, 1),
            total_amount=-200.0,
            external_id="cn-200",
            original_data={
                "from": {"docNumber": "F-200", "docType": "invoice"}},
        )
        updated = sync_internal_service_period_for_invoice(
            document=credit.original_data,
            invoice=credit,
            service_contract=contract,
            period_service=period_service,
            is_credit_note=True,
        )
        assert updated is not None
        assert updated.period_amount == 1000.0
        assert len(period_service.get_periods_by_contract(contract.id)) == 1


class TestFourGeeksSkipInternalPeriods:
    def test_process_enrollment_skips_internal_service(self, test_session, test_data_factory):
        client = test_data_factory.create_client(test_session)
        service = test_data_factory.create_service(
            test_session,
            account_identifier="70501003",
            internal_service_periods=True,
            external_id="ai-flex-6",
        )
        contract = ServiceContract(
            client_id=client.id,
            service_id=service.id,
            contract_date=date(2024, 1, 1),
            contract_amount=1000.0,
            status=ServiceContractStatus.ACTIVE,
        )
        test_session.add(contract)
        test_session.commit()
        test_session.refresh(contract)

        period_service = ServicePeriodService(test_session)
        client_service = Mock()
        service_service = ServiceService(test_session)
        contract_service = ServiceContractService(test_session)
        processor = EnrollmentProcessor(
            period_service, client_service, service_service, contract_service
        )
        processor.process_enrollment(
            {
                "cohort": {
                    "slug": "spain-ai-flex-pt-1",
                    "kickoff_date": "2024-01-01",
                    "ending_date": "2024-06-01",
                },
                "educational_status": "ACTIVE",
            },
            contract.id,
        )
        assert processor.stats["skipped"] == 1
        assert period_service.get_periods_by_contract(contract.id) == []


class TestInternalPeriodAccrual:
    @pytest.fixture
    def processor(self, test_session):
        return ContractAccrualProcessor(test_session)

    def _build_internal_contract(self, test_session, test_data_factory, amount=1200.0):
        client = test_data_factory.create_client(test_session)
        service = test_data_factory.create_service(
            test_session,
            account_identifier="70501003",
            internal_service_periods=True,
            name="ES - AI Flex",
            external_id=f"ai-flex-{amount}",
        )
        contract = ServiceContract(
            client_id=client.id,
            service_id=service.id,
            contract_date=date(2024, 1, 1),
            contract_amount=amount,
            status=ServiceContractStatus.ACTIVE,
        )
        test_session.add(contract)
        test_session.commit()
        test_session.refresh(contract)

        period = ServicePeriod(
            contract_id=contract.id,
            name="F-ACC-1",
            external_id="F-ACC-1",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            status=ServicePeriodStatus.ACTIVE,
            period_amount=amount,
        )
        test_session.add(period)

        accrual = ContractAccrual(
            contract_id=contract.id,
            total_amount_to_accrue=amount,
            remaining_amount_to_accrue=amount,
            total_amount_accrued=0.0,
            total_sessions_to_accrue=0,
            sessions_remaining_to_accrue=0,
            total_sessions_accrued=0,
            accrual_status=ContractAccrualStatus.ACTIVE,
        )
        test_session.add(accrual)
        test_session.commit()
        test_session.refresh(contract)
        test_session.refresh(period)
        test_session.refresh(accrual)

        # Ensure relationship loaded
        contract.service = service
        contract.periods = [period]
        contract.contract_accrual = accrual
        return contract, period, accrual

    @pytest.mark.asyncio
    async def test_first_month_accrues_pending_over_remaining_months(
        self, processor, test_session, test_data_factory
    ):
        contract, period, accrual = self._build_internal_contract(
            test_session, test_data_factory, amount=1200.0
        )
        result = processor._process_internal_service_periods_contract(
            contract, accrual, [period], date(2024, 1, 1)
        )
        assert result.status == ProcessingStatus.SUCCESS
        test_session.refresh(accrual)
        # Jan 2024 -> Dec 2024 inclusive = 12 months
        expected = 1200.0 / 12.0
        assert abs(accrual.total_amount_accrued - expected) < 0.01
        assert period.status == ServicePeriodStatus.ACTIVE
        assert contract.status == ServiceContractStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_end_month_marks_period_ended_and_closes_when_last(
        self, processor, test_session, test_data_factory
    ):
        contract, period, accrual = self._build_internal_contract(
            test_session, test_data_factory, amount=1200.0
        )
        # Accrue first 11 months partially by setting prior accrued rows
        prior = AccruedPeriod(
            contract_accrual_id=accrual.id,
            service_period_id=period.id,
            accrual_date=date(2024, 11, 1),
            accrued_amount=1100.0,
            accrual_portion=0.9,
            status=ServicePeriodStatus.ACTIVE,
            sessions_in_period=0,
            total_contract_amount=1200.0,
        )
        accrual.total_amount_accrued = 1100.0
        accrual.remaining_amount_to_accrue = 100.0
        test_session.add(prior)
        test_session.add(accrual)
        test_session.commit()

        result = processor._process_internal_service_periods_contract(
            contract, accrual, [period], date(2024, 12, 1)
        )
        assert result.status == ProcessingStatus.SUCCESS
        test_session.refresh(period)
        test_session.refresh(contract)
        test_session.refresh(accrual)
        assert period.status == ServicePeriodStatus.ENDED
        assert period.status_change_date == period.end_date
        assert contract.status == ServiceContractStatus.CLOSED
        assert accrual.accrual_status == ContractAccrualStatus.COMPLETED
        assert abs(accrual.remaining_amount_to_accrue) <= 0.01

    @pytest.mark.asyncio
    async def test_keeps_contract_open_while_second_period_active(
        self, processor, test_session, test_data_factory
    ):
        client = test_data_factory.create_client(test_session)
        service = test_data_factory.create_service(
            test_session,
            account_identifier="70501003",
            internal_service_periods=True,
            external_id="ai-flex-multi",
        )
        contract = ServiceContract(
            client_id=client.id,
            service_id=service.id,
            contract_date=date(2024, 1, 1),
            contract_amount=2400.0,
            status=ServiceContractStatus.ACTIVE,
        )
        test_session.add(contract)
        test_session.commit()
        test_session.refresh(contract)

        p1 = ServicePeriod(
            contract_id=contract.id,
            name="F-A",
            external_id="F-A",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
            status=ServicePeriodStatus.ACTIVE,
            period_amount=1200.0,
        )
        p2 = ServicePeriod(
            contract_id=contract.id,
            name="F-B",
            external_id="F-B",
            start_date=date(2024, 3, 1),
            end_date=date(2025, 3, 1),
            status=ServicePeriodStatus.ACTIVE,
            period_amount=1200.0,
        )
        accrual = ContractAccrual(
            contract_id=contract.id,
            total_amount_to_accrue=2400.0,
            remaining_amount_to_accrue=2400.0,
            total_amount_accrued=0.0,
            total_sessions_to_accrue=0,
            sessions_remaining_to_accrue=0,
            total_sessions_accrued=0,
            accrual_status=ContractAccrualStatus.ACTIVE,
        )
        test_session.add(p1)
        test_session.add(p2)
        test_session.add(accrual)
        test_session.commit()
        test_session.refresh(p1)
        test_session.refresh(p2)
        test_session.refresh(accrual)

        contract.service = service
        contract.periods = [p1, p2]
        contract.contract_accrual = accrual

        # End month for p1 only
        result = processor._process_internal_service_periods_contract(
            contract, accrual, [p1, p2], date(2024, 6, 1)
        )
        assert result.status == ProcessingStatus.SUCCESS
        test_session.refresh(p1)
        test_session.refresh(p2)
        test_session.refresh(contract)
        assert p1.status == ServicePeriodStatus.ENDED
        assert p2.status == ServicePeriodStatus.ACTIVE
        assert contract.status == ServiceContractStatus.ACTIVE


class TestBackfillInternalServicePeriods:
    def test_backfill_creates_periods_for_allowlisted_service(
        self, test_session, test_data_factory
    ):
        client = test_data_factory.create_client(test_session)
        service = test_data_factory.create_service(
            test_session,
            account_identifier="70501003",
            internal_service_periods=False,
            external_id="ai-flex-backfill",
            name="ES - AI Flex",
        )
        contract = ServiceContract(
            client_id=client.id,
            service_id=service.id,
            contract_date=date(2024, 2, 1),
            contract_amount=500.0,
            status=ServiceContractStatus.ACTIVE,
        )
        test_session.add(contract)
        test_session.commit()
        test_session.refresh(contract)

        test_data_factory.create_invoice(
            test_session,
            client_id=client.id,
            service_contract_id=contract.id,
            invoice_number="BF-1",
            invoice_date=date(2024, 2, 1),
            total_amount=500.0,
            external_id="bf-inv-1",
        )

        stats = backfill_internal_service_periods(test_session)
        test_session.refresh(service)
        assert service.internal_service_periods is True
        assert stats["periods_created"] >= 1
        periods = ServicePeriodService(
            test_session).get_periods_by_contract(contract.id)
        assert len(periods) == 1
        assert periods[0].external_id == "BF-1"
        assert periods[0].period_amount == 500.0
