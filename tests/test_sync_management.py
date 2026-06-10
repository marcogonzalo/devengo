from datetime import date

import pytest

from src.api.sync.services.sync_management_service import SyncManagementService


class TestSyncManagementService:
    def test_count_invoices_for_period_returns_zero_when_no_invoices(
        self, test_session
    ):
        service = SyncManagementService(test_session)

        assert service.count_invoices_for_period(2025, 6) == 0
        assert service.count_invoices_for_period(2025) == 0

    def test_count_invoices_for_period_filters_by_month(
        self, test_session, test_data_factory
    ):
        service = SyncManagementService(test_session)
        test_data_factory.create_invoice(
            test_session,
            external_id="INV-JUNE",
            invoice_date=date(2025, 6, 10),
        )
        test_data_factory.create_invoice(
            test_session,
            external_id="INV-JULY",
            invoice_date=date(2025, 7, 10),
        )

        assert service.count_invoices_for_period(2025, 6) == 1
        assert service.count_invoices_for_period(2025, 7) == 1
        assert service.count_invoices_for_period(2025, 5) == 0

    def test_count_invoices_for_period_without_month_counts_whole_year(
        self, test_session, test_data_factory
    ):
        service = SyncManagementService(test_session)
        test_data_factory.create_invoice(
            test_session,
            external_id="INV-2025",
            invoice_date=date(2025, 3, 1),
        )
        test_data_factory.create_invoice(
            test_session,
            external_id="INV-2024",
            invoice_date=date(2024, 3, 1),
        )

        assert service.count_invoices_for_period(2025) == 1
        assert service.count_invoices_for_period(2024) == 1
