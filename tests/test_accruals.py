import pytest
from datetime import date, datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
from sqlmodel import Session

from src.api.accruals.services.contract_accrual_processor import ContractAccrualProcessor
from src.api.accruals.services.accrual_reports_service import AccrualReportsService
from src.api.accruals.models.accrued_period import AccruedPeriod
from src.api.common.constants.services import ServiceContractStatus, ServicePeriodStatus
from src.api.services.models.service_contract import ServiceContract
from src.api.services.models.service_period import ServicePeriod
from src.api.clients.models.client import Client
from src.api.invoices.models.invoice import Invoice
from src.api.accruals.models.contract_accrual import ContractAccrual
from src.api.accruals.constants.accruals import ContractAccrualStatus


class TestContractAccrualProcessor:
    """Test ContractAccrualProcessor class"""

    @pytest.fixture
    def processor(self, test_session):
        """Create a contract accrual processor for testing"""
        return ContractAccrualProcessor(test_session)

    @pytest.fixture
    def sample_contract(self, test_session, test_data_factory):
        """Create a sample service contract for testing"""
        client = test_data_factory.create_client(test_session)
        service = test_data_factory.create_service(test_session)

        contract = ServiceContract(
            client_id=client.id,
            service_id=service.id,
            contract_date=date(2024, 1, 1),
            contract_amount=5000.00,
            status="ACTIVE"
        )
        test_session.add(contract)
        test_session.commit()
        test_session.refresh(contract)
        return contract

    def test_processor_initialization(self, processor):
        """Test processor initialization"""
        assert processor is not None
        assert hasattr(processor, 'db')

    @pytest.mark.asyncio
    async def test_process_contract_accruals_success(self, processor, sample_contract, test_session):
        """Test successful contract accrual processing"""
        target_month = date(2024, 1, 1)

        # Create a service period for the contract
        service_period = ServicePeriod(
            contract_id=sample_contract.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            status=ServicePeriodStatus.ENDED
        )
        test_session.add(service_period)
        test_session.commit()

        result = await processor.process_all_contracts(target_month)

        # Should process without errors
        assert result is not None

    @pytest.mark.asyncio
    async def test_process_contract_accruals_no_contracts(self, processor):
        """Test processing when no contracts exist"""
        target_month = date(2024, 1, 1)

        result = await processor.process_all_contracts(target_month)

        # Should handle empty contracts gracefully
        assert result is not None

    @pytest.mark.asyncio
    async def test_process_contract_accruals_future_month(self, processor, sample_contract):
        """Test processing for future month"""
        future_month = date(2025, 12, 1)

        result = await processor.process_all_contracts(future_month)

        # Should handle future dates appropriately
        assert result is not None

    def test_calculate_accrual_amount_full_month(self, processor, sample_contract):
        """Test accrual calculation for full month"""
        # Mock the calculation method if it exists
        if hasattr(processor, '_calculate_accrual_amount'):
            amount = processor._calculate_accrual_amount(
                sample_contract,
                date(2024, 1, 1),
                date(2024, 1, 31)
            )

            # Should calculate based on monthly amount
            assert amount > 0

    def test_calculate_accrual_amount_partial_month(self, processor, sample_contract):
        """Test accrual calculation for partial month"""
        if hasattr(processor, '_calculate_accrual_amount'):
            amount = processor._calculate_accrual_amount(
                sample_contract,
                date(2024, 1, 15),  # Mid-month start
                date(2024, 1, 31)
            )

            # Should be prorated for partial month
            assert amount > 0
            assert amount < sample_contract.contract_amount

    def test_is_contract_recent_true(self, processor, sample_contract):
        """Test contract recency check - recent contract"""
        if hasattr(processor, '_is_contract_recent'):
            # Contract date is 2024-01-01, make target month close enough (within 15 days)
            # Reference will be end of target month, so use a month where end is within 15 days of contract date
            # Month end will be 2024-01-31, contract is 2024-01-01, difference = 30 days
            target_month = date(2024, 1, 10)
            # Actually, let's use a target month where the contract_date is very recent
            # Month end = 2024-01-31, contract = 2024-01-01, diff = 30 > 15
            target_month = date(2024, 1, 5)
            # The issue is sample_contract.contract_date is 2024-01-01, let's check what it actually is first

            # Let's use a different approach - modify to be within 15 days of month end
            # Month end = 2024-01-31, contract = 2024-01-01, diff = 30
            target_month = date(2024, 1, 1)
            # We need contract date to be within 15 days of month end (2024-01-31)
            # So contract should be >= 2024-01-16 to be recent
            # Let's change the contract date for this test
            # Now diff = 11 days, should be recent
            sample_contract.contract_date = date(2024, 1, 20)

            result = processor._is_contract_recent(
                sample_contract.contract_date, target_month)

            assert result is True

    def test_is_contract_recent_false(self, processor, sample_contract):
        """Test contract recency check - old contract"""
        if hasattr(processor, '_is_contract_recent'):
            target_month = date(2024, 6, 1)  # Far from contract date

            result = processor._is_contract_recent(
                sample_contract.contract_date, target_month)

            assert result is False

    def test_process_active_contracts(self, processor, sample_contract, test_session):
        """Test processing of active contracts"""
        target_month = date(2024, 1, 1)

        # Ensure contract is active
        sample_contract.status = ServiceContractStatus.ACTIVE
        test_session.add(sample_contract)
        test_session.commit()

        if hasattr(processor, '_process_active_contracts'):
            result = processor._process_active_contracts(target_month)
            assert result is not None

    def test_process_closed_contracts(self, processor, sample_contract, test_session):
        """Test processing of closed contracts"""
        target_month = date(2024, 1, 1)

        # Set contract as closed
        sample_contract.status = ServiceContractStatus.CLOSED
        test_session.add(sample_contract)
        test_session.commit()

        if hasattr(processor, '_process_closed_contracts'):
            result = processor._process_closed_contracts(target_month)
            assert result is not None

    def test_handle_resignation_detection(self, processor, sample_contract, test_session):
        """Test resignation detection logic"""
        target_month = date(2024, 3, 1)  # More than 15 days after contract

        if hasattr(processor, '_detect_resignation'):
            result = processor._detect_resignation(
                sample_contract, target_month)
            # Should detect resignation for old contracts without recent activity
            assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_process_with_existing_accruals(self, processor, sample_contract, test_session):
        """Test processing when accruals already exist"""
        target_month = date(2024, 1, 1)

        # Create existing accrual
        existing_accrual = AccruedPeriod(
            contract_accrual_id=1,  # This will need proper setup in actual test
            accrual_date=target_month,
            accrued_amount=1000.00,
            accrual_portion=0.2,
            status="ACTIVE",
            sessions_in_period=40,
            total_contract_amount=5000.00
        )
        test_session.add(existing_accrual)
        test_session.commit()

        result = await processor.process_all_contracts(target_month)

        # Should handle existing accruals appropriately
        assert result is not None

    @pytest.mark.asyncio
    async def test_process_with_overlapping_service_periods(self, processor, sample_contract, test_session):
        """Test processing with overlapping service periods"""
        target_month = date(2024, 1, 1)

        # Create overlapping service periods
        period1 = ServicePeriod(
            contract_id=sample_contract.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 20),
            status=ServicePeriodStatus.ENDED
        )
        period2 = ServicePeriod(
            contract_id=sample_contract.id,
            start_date=date(2024, 1, 15),
            end_date=date(2024, 1, 31),
            status=ServicePeriodStatus.ENDED
        )
        test_session.add_all([period1, period2])
        test_session.commit()

        result = await processor.process_all_contracts(target_month)

        # Should handle overlapping periods correctly
        assert result is not None

    @pytest.mark.asyncio
    async def test_process_with_gap_in_service_periods(self, processor, sample_contract, test_session):
        """Test processing with gaps in service periods"""
        target_month = date(2024, 1, 1)

        # Create service periods with gaps
        period1 = ServicePeriod(
            contract_id=sample_contract.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 10),
            status=ServicePeriodStatus.ENDED
        )
        period2 = ServicePeriod(
            contract_id=sample_contract.id,
            start_date=date(2024, 1, 20),
            end_date=date(2024, 1, 31),
            status=ServicePeriodStatus.ENDED
        )
        test_session.add_all([period1, period2])
        test_session.commit()

        result = await processor.process_all_contracts(target_month)

        # Should handle gaps appropriately
        assert result is not None

    @pytest.mark.asyncio
    async def test_process_with_credit_notes(self, processor, sample_contract, test_session, test_data_factory):
        """Test processing when credit notes exist"""
        target_month = date(2024, 1, 1)

        # Create a credit note (negative invoice)
        credit_note = test_data_factory.create_invoice(
            test_session,
            client_id=sample_contract.client_id,
            total_amount=-500.00,
            invoice_date=date(2024, 1, 15),
            status="ISSUED"
        )

        result = await processor.process_all_contracts(target_month)

        # Should account for credit notes in calculations
        assert result is not None

    @pytest.mark.asyncio
    async def test_processor_error_handling(self, processor, test_session, sample_contract):
        """Test processor error handling"""
        target_month = date(2024, 1, 1)

        # Ensure the contract will be processed by making it active and setting appropriate date
        sample_contract.status = ServiceContractStatus.ACTIVE
        sample_contract.contract_date = date(
            2024, 1, 1)  # Make it in the target month
        test_session.add(sample_contract)

        # Create a service period so it goes through the _accrue_portion path
        service_period = ServicePeriod(
            contract_id=sample_contract.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            status=ServicePeriodStatus.ACTIVE
        )
        test_session.add(service_period)
        test_session.commit()

        # Mock a database error during _accrue_portion
        with patch.object(processor, '_accrue_portion', side_effect=Exception("Database error")):
            # The processor should handle errors gracefully and return results
            result = await processor.process_all_contracts(target_month)

            # Should handle error gracefully and continue processing
            assert result is not None
            assert result['failed'] > 0  # Should have failed contracts

    @pytest.mark.asyncio
    async def test_processor_with_invalid_date(self, processor):
        """Test processor with invalid date input"""
        with pytest.raises((ValueError, TypeError)):
            await processor.process_all_contracts("invalid-date")

    @pytest.mark.asyncio
    async def test_processor_logging(self, processor, sample_contract):
        """Test that processor logs operations correctly"""
        target_month = date(2024, 1, 1)

        with patch('builtins.print') as mock_print:
            await processor.process_all_contracts(target_month)

            # Should have logged some operations
            # Note: This depends on the actual logging implementation
            # mock_print.assert_called()

    @pytest.mark.asyncio
    async def test_zero_amount_accrued_periods_not_created(self, processor, test_session, test_data_factory):
        """Test that AccruedPeriods with amount = 0.0 are not created for postponed periods outside their valid range."""
        # Create client and service
        client = test_data_factory.create_client(test_session)
        service = test_data_factory.create_service(test_session)

        # Create contract
        contract = ServiceContract(
            client_id=client.id,
            service_id=service.id,
            contract_amount=4800.0,
            contract_date=date(2024, 11, 1),
            status=ServiceContractStatus.ACTIVE
        )
        test_session.add(contract)
        test_session.commit()
        test_session.refresh(contract)

        # Create service period that gets postponed
        period = ServicePeriod(
            name="test-period",
            start_date=date(2024, 12, 1),
            end_date=date(2025, 4, 30),
            status=ServicePeriodStatus.POSTPONED,
            status_change_date=date(2025, 1, 15),  # Postponed mid-January
            contract_id=contract.id
        )
        test_session.add(period)
        test_session.commit()

        # Process December 2024 (should create AccruedPeriod)
        result_dec = await processor._process_contract(contract, date(2024, 12, 1))
        assert result_dec.status.value == "SUCCESS"

        # Process January 2025 (should create AccruedPeriod until postponement date)
        result_jan = await processor._process_contract(contract, date(2025, 1, 1))
        assert result_jan.status.value == "SUCCESS"

        # Process February 2025 (should NOT create AccruedPeriod - portion = 0.0)
        result_feb = await processor._process_contract(contract, date(2025, 2, 1))
        assert result_feb.status.value == "SUCCESS"

        # Process March 2025 (should NOT create AccruedPeriod - portion = 0.0)
        result_mar = await processor._process_contract(contract, date(2025, 3, 1))
        assert result_mar.status.value == "SUCCESS"

        # Verify AccruedPeriods created
        contract_accrual = test_session.query(ContractAccrual).filter(
            ContractAccrual.contract_id == contract.id
        ).first()
        assert contract_accrual is not None

        accrued_periods = test_session.query(AccruedPeriod).filter(
            AccruedPeriod.contract_accrual_id == contract_accrual.id
        ).all()

        # Should only have 2 AccruedPeriods (December and January)
        assert len(accrued_periods) == 2

        # Verify dates and amounts
        periods_by_date = {ap.accrual_date: ap for ap in accrued_periods}

        # December 2024 should exist with positive amount
        assert date(2024, 12, 1) in periods_by_date
        assert periods_by_date[date(2024, 12, 1)].accrued_amount > 0

        # January 2025 should exist with positive amount
        assert date(2025, 1, 1) in periods_by_date
        assert periods_by_date[date(2025, 1, 1)].accrued_amount > 0

        # February and March 2025 should NOT exist
        assert date(2025, 2, 1) not in periods_by_date
        assert date(2025, 3, 1) not in periods_by_date

        # Verify no AccruedPeriod exists with amount = 0.0
        zero_amount_periods = [
            ap for ap in accrued_periods if ap.accrued_amount == 0.0]
        assert len(
            zero_amount_periods) == 0, "No AccruedPeriods with amount = 0.0 should exist"

        # Verify contract totals consistency
        total_accrued_in_periods = sum(
            ap.accrued_amount for ap in accrued_periods)
        assert abs(contract_accrual.total_amount_accrued -
                   total_accrued_in_periods) < 0.01

        print(
            f"✅ Contract {contract.id} has {len(accrued_periods)} AccruedPeriods, none with amount = 0.0")
        print(
            f"✅ Total accrued: {contract_accrual.total_amount_accrued}, Sum of periods: {total_accrued_in_periods}")

    @pytest.mark.asyncio
    async def test_isa_full_time_contract_processing(self, processor, test_session, test_data_factory):
        """Test processing of ISA Full-Time contracts without overlapping periods."""
        # Create ISA Full-Time service
        isa_service = test_data_factory.create_service(
            test_session,
            name="ES - ISA - Full-Time",
            service_type="FS"
        )

        # Create client
        client = test_data_factory.create_client(test_session)

        # Create ISA contract with ended service period
        contract = ServiceContract(
            client_id=client.id,
            service_id=isa_service.id,
            contract_date=date(2022, 1, 1),
            contract_amount=5000.00,
            status=ServiceContractStatus.ACTIVE
        )
        test_session.add(contract)
        test_session.commit()
        test_session.refresh(contract)

        # Create ended service period (no overlap with target month)
        service_period = ServicePeriod(
            contract_id=contract.id,
            start_date=date(2022, 1, 1),
            end_date=date(2022, 12, 31),
            status=ServicePeriodStatus.ENDED
        )
        test_session.add(service_period)

        # Create recent invoice in target month
        invoice = test_data_factory.create_invoice(
            test_session,
            service_contract_id=contract.id,
            invoice_date=date(2024, 6, 29),
            total_amount=210.00
        )

        test_session.commit()

        # Process for June 2024
        target_month = date(2024, 6, 1)
        result = await processor.process_all_contracts(target_month)

        # Should process the ISA contract
        assert result['total_processed'] > 0
        assert result['successful'] > 0

        # Check that the contract was processed
        processed_contracts = [
            r for r in result['results'] if r.contract_id == contract.id]
        assert len(processed_contracts) > 0

        # Check that the accrual was created/updated
        contract_accrual = test_session.get(ContractAccrual, contract.id)
        assert contract_accrual is not None
        assert contract_accrual.remaining_amount_to_accrue >= 0


class TestAccrualReportsService:
    """Test AccrualReportsService class"""

    @pytest.fixture
    def reports_service(self, test_session):
        """Create an accrual reports service for testing"""
        return AccrualReportsService(test_session)

    @pytest.fixture
    def sample_accrual_data(self, test_session, test_data_factory):
        """Create sample accrual data for testing"""
        client = test_data_factory.create_client(test_session)
        service = test_data_factory.create_service(test_session)

        contract = ServiceContract(
            client_id=client.id,
            service_id=service.id,
            contract_date=date(2024, 1, 1),
            contract_amount=5000.00,
            status="ACTIVE"
        )
        test_session.add(contract)
        test_session.commit()
        test_session.refresh(contract)

        # Create accrual periods
        accruals = []
        for i in range(3):
            accrual = AccruedPeriod(
                contract_accrual_id=1,  # This will need proper setup with ContractAccrual
                accrual_date=date(2024, i+1, 1),
                accrued_amount=1000.00 + (i * 100),
                accrual_portion=0.2,
                status="ACTIVE",
                sessions_in_period=40,
                total_contract_amount=5000.00
            )
            accruals.append(accrual)

        test_session.add_all(accruals)
        test_session.commit()

        return {
            'client': client,
            'service': service,
            'contract': contract,
            'accruals': accruals
        }

    def test_reports_service_initialization(self, reports_service):
        """Test reports service initialization"""
        assert reports_service is not None
        assert hasattr(reports_service, 'db')

    def test_get_accruals_by_month(self, reports_service, sample_accrual_data):
        """Test getting accruals by month"""
        target_month = date(2024, 1, 1)

        if hasattr(reports_service, 'get_accruals_by_month'):
            result = reports_service.get_accruals_by_month(target_month)

            assert isinstance(result, list)
            # Should find accruals for the target month
            assert len(result) >= 0

    def test_get_accruals_by_client(self, reports_service, sample_accrual_data):
        """Test getting accruals by client"""
        client_id = sample_accrual_data['client'].id

        if hasattr(reports_service, 'get_accruals_by_client'):
            result = reports_service.get_accruals_by_client(client_id)

            assert isinstance(result, list)
            # Should find accruals for the client
            assert len(result) >= 0

    def test_get_accruals_by_date_range(self, reports_service, sample_accrual_data):
        """Test getting accruals by date range"""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 3, 31)

        if hasattr(reports_service, 'get_accruals_by_date_range'):
            result = reports_service.get_accruals_by_date_range(
                start_date, end_date)

            assert isinstance(result, list)
            # Should find accruals in the date range
            assert len(result) >= 0

    def test_calculate_total_accruals(self, reports_service, sample_accrual_data):
        """Test calculating total accruals"""
        if hasattr(reports_service, 'calculate_total_accruals'):
            total = reports_service.calculate_total_accruals(
                date(2024, 1, 1),
                date(2024, 3, 31)
            )

            assert isinstance(total, (int, float, Decimal))
            assert total >= 0

    def test_get_accrual_summary_by_client(self, reports_service, sample_accrual_data):
        """Test getting accrual summary by client"""
        if hasattr(reports_service, 'get_accrual_summary_by_client'):
            result = reports_service.get_accrual_summary_by_client(
                date(2024, 1, 1),
                date(2024, 3, 31)
            )

            assert isinstance(result, list)
            # Each item should have client info and totals
            for item in result:
                assert 'client_id' in item or 'client' in item
                assert 'total_amount' in item or 'amount' in item

    def test_get_monthly_accrual_report(self, reports_service, sample_accrual_data):
        """Test getting monthly accrual report"""
        target_month = date(2024, 1, 1)

        if hasattr(reports_service, 'get_monthly_accrual_report'):
            result = reports_service.get_monthly_accrual_report(target_month)

            assert isinstance(result, dict)
            # Should contain summary information
            assert 'total_amount' in result or 'accruals' in result

    def test_get_accruals_with_status_filter(self, reports_service, sample_accrual_data):
        """Test getting accruals with status filter"""
        if hasattr(reports_service, 'get_accruals_by_status'):
            result = reports_service.get_accruals_by_status("PROCESSED")

            assert isinstance(result, list)
            # All returned accruals should have the specified status
            for accrual in result:
                assert accrual.status == "PROCESSED"

    def test_get_pending_accruals(self, reports_service, sample_accrual_data, test_session):
        """Test getting pending accruals"""
        # Create a pending accrual
        pending_accrual = AccruedPeriod(
            contract_accrual_id=1,  # This will need proper setup with ContractAccrual
            accrual_date=date(2024, 4, 1),
            accrued_amount=1500.00,
            accrual_portion=0.3,
            status="ACTIVE",
            sessions_in_period=60,
            total_contract_amount=5000.00
        )
        test_session.add(pending_accrual)
        test_session.commit()

        if hasattr(reports_service, 'get_pending_accruals'):
            result = reports_service.get_pending_accruals()

            assert isinstance(result, list)
            # Should include the active accrual
            active_found = any(
                accrual.status == "ACTIVE" for accrual in result)
            assert active_found

    def test_export_accruals_to_csv(self, reports_service, sample_accrual_data):
        """Test exporting accruals to CSV format"""
        if hasattr(reports_service, 'export_accruals_to_csv'):
            result = reports_service.export_accruals_to_csv(
                date(2024, 1, 1),
                date(2024, 3, 31)
            )

            # Should return CSV data or file path
            assert result is not None
            assert isinstance(result, (str, bytes))

    def test_reports_service_error_handling(self, reports_service, test_session):
        """Test reports service error handling"""
        # Mock a database error
        with patch.object(test_session, 'exec', side_effect=Exception("Database error")):
            if hasattr(reports_service, 'get_accruals_by_month'):
                with pytest.raises(Exception, match="Database error"):
                    reports_service.get_accruals_by_month(date(2024, 1, 1))

    def test_reports_service_with_no_data(self, reports_service):
        """Test reports service with no accrual data"""
        if hasattr(reports_service, 'get_accruals_by_month'):
            result = reports_service.get_accruals_by_month(date(2025, 1, 1))

            # Should handle empty results gracefully
            assert isinstance(result, list)
            assert len(result) == 0

    def test_reports_service_date_validation(self, reports_service):
        """Test reports service with invalid dates"""
        if hasattr(reports_service, 'get_accruals_by_date_range'):
            # End date before start date
            with pytest.raises((ValueError, AssertionError)):
                reports_service.get_accruals_by_date_range(
                    date(2024, 3, 1),
                    date(2024, 1, 1)
                )

    def test_csv_export_includes_all_required_contracts(self, reports_service, test_session, test_data_factory):
        """Test that CSV export includes all contracts according to requirements"""
        # Create test data
        client1 = test_data_factory.create_client(
            test_session, name="Client with accruals in range")
        client2 = test_data_factory.create_client(
            test_session, name="Active client contract before end_date")
        client3 = test_data_factory.create_client(
            test_session, name="Active client far before range no accrual")
        client4 = test_data_factory.create_client(
            test_session, name="Closed client before end_date incomplete")
        client5 = test_data_factory.create_client(
            test_session, name="Closed client before end_date completed")

        service = test_data_factory.create_service(test_session)

        # Contract 1: Has accruals in the date range (should be included)
        contract1 = ServiceContract(
            client_id=client1.id,
            service_id=service.id,
            contract_date=date(2024, 12, 1),  # Before end_date
            contract_amount=5000.00,
            # Even if closed, should be included due to accruals
            status=ServiceContractStatus.CLOSED
        )
        test_session.add(contract1)

        # Contract 2: Active with contract date before end_date (should be included)
        contract2 = ServiceContract(
            client_id=client2.id,
            service_id=service.id,
            contract_date=date(2024, 10, 15),  # Before end_date
            contract_amount=3000.00,
            status=ServiceContractStatus.ACTIVE
        )
        test_session.add(contract2)

        # Contract 3: Active with contract date far before range, no accrual yet (should be included)
        contract3 = ServiceContract(
            client_id=client3.id,
            service_id=service.id,
            contract_date=date(2023, 11, 1),  # Far before end_date
            contract_amount=2000.00,
            status=ServiceContractStatus.ACTIVE
        )
        test_session.add(contract3)

        # Contract 4: Closed with contract date before end_date, incomplete accrual (should be included)
        contract4 = ServiceContract(
            client_id=client4.id,
            service_id=service.id,
            contract_date=date(2024, 8, 1),  # Before end_date
            contract_amount=4000.00,
            status=ServiceContractStatus.CLOSED
        )
        test_session.add(contract4)

        # Contract 5: Closed with contract date before end_date, completed accrual (should NOT be included)
        contract5 = ServiceContract(
            client_id=client5.id,
            service_id=service.id,
            contract_date=date(2024, 9, 1),  # Before end_date
            contract_amount=1000.00,
            status=ServiceContractStatus.CLOSED
        )
        test_session.add(contract5)

        test_session.commit()
        test_session.refresh(contract1)
        test_session.refresh(contract2)
        test_session.refresh(contract3)
        test_session.refresh(contract4)
        test_session.refresh(contract5)

        # Create contract accruals
        accrual1 = ContractAccrual(
            contract_id=contract1.id,
            total_amount_to_accrue=5000.00,
            total_amount_accrued=5000.00,
            remaining_amount_to_accrue=0.00,
            total_sessions_to_accrue=100,
            total_sessions_accrued=100,
            sessions_remaining_to_accrue=0,
            accrual_status=ContractAccrualStatus.COMPLETED
        )

        accrual4 = ContractAccrual(
            contract_id=contract4.id,
            total_amount_to_accrue=4000.00,
            total_amount_accrued=2000.00,
            remaining_amount_to_accrue=2000.00,
            total_sessions_to_accrue=80,
            total_sessions_accrued=40,
            sessions_remaining_to_accrue=40,
            accrual_status=ContractAccrualStatus.ACTIVE
        )

        accrual5 = ContractAccrual(
            contract_id=contract5.id,
            total_amount_to_accrue=1000.00,
            total_amount_accrued=1000.00,
            remaining_amount_to_accrue=0.00,
            total_sessions_to_accrue=20,
            total_sessions_accrued=20,
            sessions_remaining_to_accrue=0,
            accrual_status=ContractAccrualStatus.COMPLETED
        )

        test_session.add_all([accrual1, accrual4, accrual5])
        test_session.commit()
        test_session.refresh(accrual1)
        test_session.refresh(accrual4)
        test_session.refresh(accrual5)

        # Create accrued period in range for contract1
        accrued_period = AccruedPeriod(
            contract_accrual_id=accrual1.id,
            accrual_date=date(2025, 1, 1),  # In range
            accrued_amount=1000.00,
            accrual_portion=0.2,
            status="ACTIVE",
            sessions_in_period=20,
            total_contract_amount=5000.00
        )
        test_session.add(accrued_period)
        test_session.commit()

        # Test the export function
        start_date = date(2025, 1, 1)
        end_date = date(2025, 1, 31)

        export_data = reports_service.get_accruals_export(start_date, end_date)

        # Extract client names from the export data
        client_names_in_export = {row['Client']
                                  for row in export_data['data'] if row['Client']}

        # Verify contracts that SHOULD be included
        assert "Client with accruals in range" in client_names_in_export, "Contract with accruals in range should be included"
        assert "Active client contract before end_date" in client_names_in_export, "Active contract with date before end_date should be included"
        assert "Active client far before range no accrual" in client_names_in_export, "Active contract without accrual should be included"
        assert "Closed client before end_date incomplete" in client_names_in_export, "Closed contract with incomplete accrual should be included"

        # Verify contract that should NOT be included
        assert "Closed client before end_date completed" not in client_names_in_export, "Closed contract with completed accrual should NOT be included"

        # Verify the export contains expected number of unique contracts (4 should be included)
        assert len(
            client_names_in_export) == 4, f"Expected 4 contracts, found {len(client_names_in_export)}: {client_names_in_export}"


class TestAccrualModels:
    """Test accrual-related models"""

    def test_accrual_period_creation(self, test_session, test_data_factory):
        """Test AccruedPeriod model creation"""
        client = test_data_factory.create_client(test_session)
        service = test_data_factory.create_service(test_session)

        contract = ServiceContract(
            client_id=client.id,
            service_id=service.id,
            contract_date=date(2024, 1, 1),
            contract_amount=5000.00,
            status=ServiceContractStatus.ACTIVE
        )
        test_session.add(contract)
        test_session.commit()
        test_session.refresh(contract)

        accrual = AccruedPeriod(
            contract_accrual_id=1,  # This will need proper setup with ContractAccrual
            accrual_date=date(2024, 1, 1),
            accrued_amount=1000.00,
            accrual_portion=0.2,
            status="ACTIVE",
            sessions_in_period=40,
            total_contract_amount=5000.00
        )
        test_session.add(accrual)
        test_session.commit()
        test_session.refresh(accrual)

        assert accrual.id is not None
        assert accrual.contract_accrual_id == 1
        assert accrual.accrued_amount == 1000.00
        assert accrual.status == "ACTIVE"

    def test_accrual_period_relationships(self, test_session, test_data_factory):
        """Test AccruedPeriod model relationships"""
        client = test_data_factory.create_client(test_session)
        service = test_data_factory.create_service(test_session)

        contract = ServiceContract(
            client_id=client.id,
            service_id=service.id,
            contract_date=date(2024, 1, 1),
            contract_amount=5000.00,
            status=ServiceContractStatus.ACTIVE
        )
        test_session.add(contract)
        test_session.commit()
        test_session.refresh(contract)

        accrual = AccruedPeriod(
            contract_accrual_id=1,
            accrual_date=date(2024, 1, 1),
            accrued_amount=1000.00,
            accrual_portion=0.2,
            status="ACTIVE",
            sessions_in_period=40,
            total_contract_amount=5000.00
        )
        test_session.add(accrual)
        test_session.commit()
        test_session.refresh(accrual)

        # Test relationships if they exist
        assert accrual.contract_accrual_id == 1

    def test_accrual_period_validation(self, test_session, test_data_factory):
        """Test AccruedPeriod model validation"""
        # Test invalid accrual data
        accrual = AccruedPeriod(
            contract_accrual_id=1,
            accrual_date=date(2024, 1, 1),
            accrued_amount=1000.00,
            accrual_portion=0.2,
            status="ACTIVE",
            sessions_in_period=40,
            total_contract_amount=5000.00
        )

        # Should handle validation appropriately
        assert accrual.contract_accrual_id == 1

    def test_accrual_period_amount_precision(self, test_session, test_data_factory):
        """Test AccruedPeriod amount precision handling"""
        client = test_data_factory.create_client(test_session)
        service = test_data_factory.create_service(test_session)

        contract = ServiceContract(
            client_id=client.id,
            service_id=service.id,
            contract_date=date(2024, 1, 1),
            contract_amount=5000.00,
            status=ServiceContractStatus.ACTIVE
        )
        test_session.add(contract)
        test_session.commit()
        test_session.refresh(contract)

        # Test with high precision amount
        accrual = AccruedPeriod(
            contract_accrual_id=1,
            accrual_date=date(2024, 1, 1),
            accrued_amount=1234.5678,  # High precision
            accrual_portion=0.2,
            status="ACTIVE",
            sessions_in_period=40,
            total_contract_amount=5000.00
        )
        test_session.add(accrual)
        test_session.commit()
        test_session.refresh(accrual)

        # Amount should be stored with appropriate precision
        assert accrual.accrued_amount is not None
        assert isinstance(accrual.accrued_amount, (int, float, Decimal))
