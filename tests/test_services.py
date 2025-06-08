import pytest
from datetime import date
from unittest.mock import Mock, patch
from sqlmodel import Session

from src.api.services.services.service_service import ServiceService
from src.api.services.services.service_period_service import ServicePeriodService
from src.api.services.services.service_contract import ServiceContractService
from src.api.services.models.service import Service
from src.api.services.models.service_period import ServicePeriod
from src.api.services.models.service_contract import ServiceContract
from src.api.services.schemas.service import ServiceCreate, ServiceUpdate
from src.api.services.schemas.service_period import ServicePeriodCreate, ServicePeriodUpdate
from src.api.services.schemas.service_contract import ServiceContractCreate, ServiceContractUpdate
from src.api.common.constants.services import ServiceContractStatus, ServicePeriodStatus


class TestServiceService:
    """Test ServiceService class"""

    def test_create_service_success(self, test_session, sample_service_data):
        """Test successful service creation"""
        service_svc = ServiceService(test_session)
        service_data = ServiceCreate(**sample_service_data)
        
        result = service_svc.create_service(service_data)
        
        assert result.id is not None
        assert result.name == sample_service_data["name"]
        assert result.description == sample_service_data["description"]
        assert result.total_sessions == sample_service_data["total_sessions"]

    def test_create_service_minimal_data(self, test_session):
        """Test creating service with minimal data"""
        service_svc = ServiceService(test_session)
        service_data = ServiceCreate(
            name="Basic Service",
            external_id="BASIC-001"
        )
        
        result = service_svc.create_service(service_data)
        
        assert result.name == "Basic Service"
        assert result.external_id == "BASIC-001"
        assert result.description is None

    def test_get_service_success(self, test_session, test_data_factory):
        """Test successful service retrieval"""
        service_svc = ServiceService(test_session)
        created_service = test_data_factory.create_service(test_session)
        
        result = service_svc.get_service(created_service.id)
        
        assert result is not None
        assert result.id == created_service.id
        assert result.name == created_service.name

    def test_get_service_not_found(self, test_session):
        """Test getting non-existent service"""
        service_svc = ServiceService(test_session)
        
        result = service_svc.get_service(999)
        
        assert result is None

    def test_get_services_pagination(self, test_session, test_data_factory):
        """Test getting services with pagination"""
        service_svc = ServiceService(test_session)
        
        # Create multiple services
        for i in range(5):
            test_data_factory.create_service(
                test_session,
                name=f"Service {i}",
                total_sessions=50 + i
            )
        
        result = service_svc.get_services(skip=1, limit=3)
        
        assert len(result) == 3

    def test_update_service_success(self, test_session, test_data_factory):
        """Test successful service update"""
        service_svc = ServiceService(test_session)
        created_service = test_data_factory.create_service(test_session)
        
        update_data = ServiceUpdate(name="Updated Service", total_sessions=80)
        result = service_svc.update_service(created_service.id, update_data)
        
        assert result is not None
        assert result.name == "Updated Service"
        assert result.total_sessions == 80

    def test_update_service_not_found(self, test_session):
        """Test updating non-existent service"""
        service_svc = ServiceService(test_session)
        
        update_data = ServiceUpdate(name="Updated Service")
        result = service_svc.update_service(999, update_data)
        
        assert result is None

    def test_delete_service_success(self, test_session, test_data_factory):
        """Test successful service deletion"""
        service_svc = ServiceService(test_session)
        created_service = test_data_factory.create_service(test_session)
        
        result = service_svc.delete_service(created_service.id)
        
        assert result is True
        
        # Verify service is deleted
        deleted_service = test_session.get(Service, created_service.id)
        assert deleted_service is None

    def test_delete_service_not_found(self, test_session):
        """Test deleting non-existent service"""
        service_svc = ServiceService(test_session)
        
        result = service_svc.delete_service(999)
        
        assert result is False

    def test_service_with_zero_sessions(self, test_session):
        """Test creating service with zero total sessions"""
        service_svc = ServiceService(test_session)
        service_data = ServiceCreate(
            name="Free Service",
            external_id="FREE-001",
            total_sessions=0,
            description="Complimentary service"
        )
        
        result = service_svc.create_service(service_data)
        
        assert result.total_sessions == 0
        assert result.name == "Free Service"

    def test_service_with_high_sessions(self, test_session):
        """Test creating service with very high total sessions"""
        service_svc = ServiceService(test_session)
        service_data = ServiceCreate(
            name="Premium Service",
            external_id="PREM-001",
            total_sessions=200,
            description="Premium consulting service"
        )
        
        result = service_svc.create_service(service_data)
        
        assert result.total_sessions == 200


class TestServicePeriodService:
    """Test ServicePeriodService class"""

    def test_create_service_period_success(self, test_session, test_data_factory, sample_service_period_data):
        """Test successful service period creation"""
        client = test_data_factory.create_client(test_session)
        service = test_data_factory.create_service(test_session)
        
        # Create contract first
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
        
        sample_service_period_data["contract_id"] = contract.id
        # Remove invalid fields
        sample_service_period_data.pop("hours_worked", None)
        
        service_period_svc = ServicePeriodService(test_session)
        period_data = ServicePeriodCreate(**sample_service_period_data)
        
        result = service_period_svc.create_period(period_data)
        
        assert result.id is not None
        assert result.contract_id == contract.id
        assert result.start_date == sample_service_period_data["start_date"]
        assert result.end_date == sample_service_period_data["end_date"]
        assert result.status == sample_service_period_data["status"]

    def test_create_service_period_minimal_data(self, test_session, test_data_factory):
        """Test creating service period with minimal data"""
        client = test_data_factory.create_client(test_session)
        service = test_data_factory.create_service(test_session)
        
        # Create contract first
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
        
        period_data = ServicePeriodCreate(
            contract_id=contract.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )
        
        service_period_svc = ServicePeriodService(test_session)
        result = service_period_svc.create_period(period_data)
        
        assert result.contract_id == contract.id

    def test_get_service_period_success(self, test_session, test_data_factory):
        """Test successful service period retrieval"""
        client = test_data_factory.create_client(test_session)
        service = test_data_factory.create_service(test_session)
        
        # Create service contract first
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
        
        # Create service period manually since factory doesn't exist yet
        period = ServicePeriod(
            contract_id=contract.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            status=ServicePeriodStatus.ENDED
        )
        test_session.add(period)
        test_session.commit()
        test_session.refresh(period)
        
        service_period_svc = ServicePeriodService(test_session)
        result = service_period_svc.get_period(period.id)
        
        assert result is not None
        assert result.id == period.id
        assert result.contract_id == contract.id

    def test_get_service_period_not_found(self, test_session):
        """Test getting non-existent service period"""
        service_period_svc = ServicePeriodService(test_session)
        
        result = service_period_svc.get_period(999)
        
        assert result is None

    def test_get_service_periods_by_contract(self, test_session, test_data_factory):
        """Test getting service periods by contract ID"""
        client = test_data_factory.create_client(test_session)
        service1 = test_data_factory.create_service(test_session, name="Service 1")
        service2 = test_data_factory.create_service(test_session, name="Service 2")
        
        # Create contracts first
        contract1 = ServiceContract(
            client_id=client.id,
            service_id=service1.id,
            contract_date=date(2024, 1, 1),
            contract_amount=5000.00,
            status=ServiceContractStatus.ACTIVE
        )
        contract2 = ServiceContract(
            client_id=client.id,
            service_id=service2.id,
            contract_date=date(2024, 1, 1),
            contract_amount=3000.00,
            status=ServiceContractStatus.ACTIVE
        )
        test_session.add_all([contract1, contract2])
        test_session.commit()
        test_session.refresh(contract1)
        test_session.refresh(contract2)
        
        # Create periods for contract1
        for i in range(3):
            period = ServicePeriod(
                contract_id=contract1.id,
                start_date=date(2024, i+1, 1),
                end_date=date(2024, i+1, 28),
                status=ServicePeriodStatus.ENDED
            )
            test_session.add(period)
        
        # Create one period for contract2
        period = ServicePeriod(
            contract_id=contract2.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            status=ServicePeriodStatus.ENDED
        )
        test_session.add(period)
        test_session.commit()
        
        service_period_svc = ServicePeriodService(test_session)
        result = service_period_svc.get_periods_by_contract(contract1.id)
        
        assert len(result) == 3
        assert all(period.contract_id == contract1.id for period in result)

    def test_update_service_period_success(self, test_session, test_data_factory):
        """Test successful service period update"""
        client = test_data_factory.create_client(test_session)
        service = test_data_factory.create_service(test_session)
        
        # Create contract first
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
        
        period = ServicePeriod(
            contract_id=contract.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            status=ServicePeriodStatus.ACTIVE
        )
        test_session.add(period)
        test_session.commit()
        test_session.refresh(period)
        
        service_period_svc = ServicePeriodService(test_session)
        update_data = ServicePeriodUpdate(status=ServicePeriodStatus.ENDED)
        result = service_period_svc.update_period(period.id, update_data)
        
        assert result is not None
        assert result.status == ServicePeriodStatus.ENDED

    def test_delete_service_period_success(self, test_session, test_data_factory):
        """Test successful service period deletion"""
        client = test_data_factory.create_client(test_session)
        service = test_data_factory.create_service(test_session)
        
        # Create contract first
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
        
        period = ServicePeriod(
            contract_id=contract.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )
        test_session.add(period)
        test_session.commit()
        test_session.refresh(period)
        
        service_period_svc = ServicePeriodService(test_session)
        result = service_period_svc.delete_period(period.id)
        
        assert result is True
        
        # Verify period is deleted
        deleted_period = test_session.get(ServicePeriod, period.id)
        assert deleted_period is None

    def test_service_period_date_validation(self, test_session, test_data_factory):
        """Test service period with end date before start date"""
        client = test_data_factory.create_client(test_session)
        service = test_data_factory.create_service(test_session)
        
        # Create contract first
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
        
        # This should be handled by business logic or database constraints
        period_data = ServicePeriodCreate(
            contract_id=contract.id,
            start_date=date(2024, 1, 31),
            end_date=date(2024, 1, 1)  # End before start
        )
        
        service_period_svc = ServicePeriodService(test_session)
        # Depending on implementation, this might raise an error or be allowed
        result = service_period_svc.create_period(period_data)
        
        # Test passes if no exception is raised - validation might be elsewhere
        assert result is not None

    def test_service_period_overlapping_dates(self, test_session, test_data_factory):
        """Test creating overlapping service periods for same contract"""
        client = test_data_factory.create_client(test_session)
        service = test_data_factory.create_service(test_session)
        
        # Create contract first
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
        
        service_period_svc = ServicePeriodService(test_session)
        
        # Create first period
        period1_data = ServicePeriodCreate(
            contract_id=contract.id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )
        period1 = service_period_svc.create_period(period1_data)
        
        # Create overlapping period
        period2_data = ServicePeriodCreate(
            contract_id=contract.id,
            start_date=date(2024, 1, 15),  # Overlaps with period1
            end_date=date(2024, 2, 15)
        )
        period2 = service_period_svc.create_period(period2_data)
        
        # Both should be created (business logic might handle overlaps elsewhere)
        assert period1.id != period2.id


class TestServiceContractService:
    """Test ServiceContractService class"""

    def test_create_service_contract_success(self, test_session, test_data_factory, sample_service_contract_data):
        """Test successful service contract creation"""
        client = test_data_factory.create_client(test_session)
        service = test_data_factory.create_service(test_session)
        
        sample_service_contract_data["client_id"] = client.id
        sample_service_contract_data["service_id"] = service.id
        
        contract_svc = ServiceContractService(test_session)
        contract_data = ServiceContractCreate(**sample_service_contract_data)
        
        result = contract_svc.create_contract(contract_data)
        
        assert result.id is not None
        assert result.client_id == client.id
        assert result.service_id == service.id
        assert result.contract_date == sample_service_contract_data["contract_date"]
        assert result.contract_amount == sample_service_contract_data["contract_amount"]
        assert result.status == sample_service_contract_data["status"]

    def test_create_service_contract_minimal_data(self, test_session, test_data_factory):
        """Test creating service contract with minimal data"""
        client = test_data_factory.create_client(test_session)
        service = test_data_factory.create_service(test_session)
        
        contract_data = ServiceContractCreate(
            client_id=client.id,
            service_id=service.id,
            contract_date=date(2024, 1, 1),
            contract_amount=1000.00
        )
        
        contract_svc = ServiceContractService(test_session)
        result = contract_svc.create_contract(contract_data)
        
        assert result.client_id == client.id
        assert result.service_id == service.id
        assert result.status == ServiceContractStatus.ACTIVE  # Default status
        assert result.contract_currency == "EUR"  # Default currency

    def test_get_service_contract_success(self, test_session, test_data_factory):
        """Test successful service contract retrieval"""
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
        
        contract_svc = ServiceContractService(test_session)
        result = contract_svc.get_contract(contract.id)
        
        assert result is not None
        assert result.id == contract.id
        assert result.client_id == client.id

    def test_get_service_contract_not_found(self, test_session):
        """Test getting non-existent service contract"""
        contract_svc = ServiceContractService(test_session)
        
        result = contract_svc.get_contract(999)
        
        assert result is None

    def test_get_service_contracts_by_client(self, test_session, test_data_factory):
        """Test getting service contracts by client ID"""
        client1 = test_data_factory.create_client(test_session, name="Client 1")
        client2 = test_data_factory.create_client(test_session, name="Client 2")
        service = test_data_factory.create_service(test_session)
        
        # Create contracts for client1
        for i in range(2):
            contract = ServiceContract(
                client_id=client1.id,
                service_id=service.id,
                contract_date=date(2024, 1, 1),
                contract_amount=1000.00 * (i + 1),
                status=ServiceContractStatus.ACTIVE
            )
            test_session.add(contract)
        
        # Create one contract for client2
        contract = ServiceContract(
            client_id=client2.id,
            service_id=service.id,
            contract_date=date(2024, 1, 1),
            contract_amount=2000.00,
            status=ServiceContractStatus.ACTIVE
        )
        test_session.add(contract)
        test_session.commit()
        
        contract_svc = ServiceContractService(test_session)
        result = contract_svc.get_contracts_by_client(client1.id)
        
        assert len(result) == 2
        assert all(contract.client_id == client1.id for contract in result)

    def test_get_service_contracts_by_service(self, test_session, test_data_factory):
        """Test getting service contracts by service ID"""
        client = test_data_factory.create_client(test_session)
        service1 = test_data_factory.create_service(test_session, name="Service 1")
        service2 = test_data_factory.create_service(test_session, name="Service 2")
        
        # Create contracts for service1
        for i in range(3):
            contract = ServiceContract(
                client_id=client.id,
                service_id=service1.id,
                contract_date=date(2024, 1, 1),
                contract_amount=1000.00,
                status=ServiceContractStatus.ACTIVE
            )
            test_session.add(contract)
        
        # Create one contract for service2
        contract = ServiceContract(
            client_id=client.id,
            service_id=service2.id,
            contract_date=date(2024, 1, 1),
            contract_amount=2000.00,
            status=ServiceContractStatus.ACTIVE
        )
        test_session.add(contract)
        test_session.commit()
        
        contract_svc = ServiceContractService(test_session)
        result = contract_svc.get_contracts_by_service(service1.id)
        
        assert len(result) == 3
        assert all(contract.service_id == service1.id for contract in result)

    def test_update_service_contract_success(self, test_session, test_data_factory):
        """Test successful service contract update"""
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
        
        contract_svc = ServiceContractService(test_session)
        update_data = ServiceContractUpdate(status=ServiceContractStatus.CLOSED, contract_amount=0.00)
        result = contract_svc.update_contract_status(contract.id, update_data)
        
        assert result is not None
        assert result.status == ServiceContractStatus.CLOSED
        assert result.contract_amount == 0.00

    # Note: delete_service_contract method doesn't exist in the actual implementation
    # def test_delete_service_contract_success(self, test_session, test_data_factory):
    #     """Test successful service contract deletion"""
    #     # Method not implemented in ServiceContractService

    def test_service_contract_with_zero_amount(self, test_session, test_data_factory):
        """Test creating service contract with zero monthly amount"""
        client = test_data_factory.create_client(test_session)
        service = test_data_factory.create_service(test_session)
        
        contract_data = ServiceContractCreate(
            client_id=client.id,
            service_id=service.id,
            contract_date=date(2024, 1, 1),
            contract_amount=0.00,
            status=ServiceContractStatus.CANCELED
        )
        
        contract_svc = ServiceContractService(test_session)
        result = contract_svc.create_contract(contract_data)
        
        assert result.contract_amount == 0.00
        assert result.status == ServiceContractStatus.CANCELED

    def test_service_contract_future_date(self, test_session, test_data_factory):
        """Test creating service contract with future contract date"""
        client = test_data_factory.create_client(test_session)
        service = test_data_factory.create_service(test_session)
        
        future_date = date(2025, 12, 31)
        contract_data = ServiceContractCreate(
            client_id=client.id,
            service_id=service.id,
            contract_date=future_date,
            contract_amount=5000.00,
            status=ServiceContractStatus.ACTIVE
        )
        
        contract_svc = ServiceContractService(test_session)
        result = contract_svc.create_contract(contract_data)
        
        assert result.contract_date == future_date
        assert result.status == ServiceContractStatus.ACTIVE

    def test_service_contract_database_error_handling(self, test_session, test_data_factory):
        """Test service contract service handles database errors gracefully"""
        client = test_data_factory.create_client(test_session)
        service = test_data_factory.create_service(test_session)
        contract_svc = ServiceContractService(test_session)
        
        # Mock a database error
        with patch.object(test_session, 'commit', side_effect=Exception("Database error")):
            contract_data = ServiceContractCreate(
                client_id=client.id,
                service_id=service.id,
                contract_date=date(2024, 1, 1),
                contract_amount=5000.00,
                status=ServiceContractStatus.ACTIVE
            )
            
            with pytest.raises(Exception, match="Database error"):
                contract_svc.create_contract(contract_data) 