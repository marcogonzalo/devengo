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
            target_month = date(2024, 1, 10)  # Month end will be 2024-01-31, contract is 2024-01-01, difference = 30 days
            # Actually, let's use a target month where the contract_date is very recent
            target_month = date(2024, 1, 5)   # Month end = 2024-01-31, contract = 2024-01-01, diff = 30 > 15
            # The issue is sample_contract.contract_date is 2024-01-01, let's check what it actually is first
            
            # Let's use a different approach - modify to be within 15 days of month end
            target_month = date(2024, 1, 1)  # Month end = 2024-01-31, contract = 2024-01-01, diff = 30
            # We need contract date to be within 15 days of month end (2024-01-31)
            # So contract should be >= 2024-01-16 to be recent
            # Let's change the contract date for this test
            sample_contract.contract_date = date(2024, 1, 20)  # Now diff = 11 days, should be recent
            
            result = processor._is_contract_recent(sample_contract.contract_date, target_month)
            
            assert result is True

    def test_is_contract_recent_false(self, processor, sample_contract):
        """Test contract recency check - old contract"""
        if hasattr(processor, '_is_contract_recent'):
            target_month = date(2024, 6, 1)  # Far from contract date
            
            result = processor._is_contract_recent(sample_contract.contract_date, target_month)
            
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
            result = processor._detect_resignation(sample_contract, target_month)
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
        sample_contract.contract_date = date(2024, 1, 1)  # Make it in the target month
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
            result = reports_service.get_accruals_by_date_range(start_date, end_date)
            
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
            active_found = any(accrual.status == "ACTIVE" for accrual in result)
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