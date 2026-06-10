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

    def test_extract_step_statistics_services_computes_processed_from_elements(
        self, test_session
    ):
        service = SyncManagementService(test_session)

        stats = service._extract_step_statistics(
            {
                "success": True,
                "created": 3,
                "updated": 5,
                "skipped": 2,
                "errors": 1,
            },
            "services",
        )

        assert stats["total_processed"] == 11
        assert stats["total_created"] == 3
        assert stats["total_updated"] == 5
        assert stats["total_errors"] == 1

    def test_extract_step_statistics_service_periods_computes_processed_from_elements(
        self, test_session
    ):
        service = SyncManagementService(test_session)

        stats = service._extract_step_statistics(
            {
                "success": True,
                "created": 4,
                "updated": 6,
                "skipped": 1,
                "errors": 2,
                "compatibility_errors": 3,
            },
            "service-periods",
        )

        assert stats["total_processed"] == 16
        assert stats["total_created"] == 4
        assert stats["total_updated"] == 6
        assert stats["total_errors"] == 5

    def test_extract_step_statistics_crm_clients_does_not_double_count_errors(
        self, test_session
    ):
        service = SyncManagementService(test_session)

        stats = service._extract_step_statistics(
            {
                "success": True,
                "linked": 50,
                "not_found": 64,
                "errors": 228,
                "error_details": [f"error-{index}" for index in range(228)],
            },
            "crm-clients",
        )

        assert stats["total_processed"] == 342
        assert stats["total_created"] == 50
        assert stats["total_failed"] == 64
        assert stats["total_errors"] == 228

    def test_extract_step_statistics_notion_splits_not_found_and_errors(
        self, test_session
    ):
        service = SyncManagementService(test_session)

        stats = service._extract_step_statistics(
            {
                "success": True,
                "linked": 0,
                "not_found": 3,
                "not_found_details": [
                    {
                        "client_id": 1,
                        "identifier": "a@example.com",
                        "reason": "No matching Notion page",
                    },
                    {
                        "client_id": 2,
                        "identifier": "b@example.com",
                        "reason": "Error querying Notion: HTTPError: rate limited",
                    },
                    {
                        "client_id": 3,
                        "identifier": "c@example.com",
                        "reason": "No matching Notion page",
                    },
                ],
            },
            "notion-external-id",
        )

        assert stats["total_processed"] == 3
        assert stats["total_created"] == 0
        assert stats["total_failed"] == 2
        assert stats["total_errors"] == 1

    def test_extract_step_statistics_notion_missing_page_only_counts_not_found(
        self, test_session
    ):
        service = SyncManagementService(test_session)

        stats = service._extract_step_statistics(
            {
                "success": True,
                "linked": 0,
                "not_found": 136,
                "not_found_details": [
                    {
                        "client_id": index,
                        "identifier": f"user{index}@example.com",
                        "reason": "No matching Notion page",
                    }
                    for index in range(136)
                ],
            },
            "notion-external-id",
        )

        assert stats["total_processed"] == 136
        assert stats["total_failed"] == 136
        assert stats["total_errors"] == 0
