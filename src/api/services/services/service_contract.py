from src.api.services.models.service import Service  #  noqa
from datetime import date
from typing import List, Optional, Dict, Any
from sqlmodel import Session, select
from src.api.common.constants.services import ServiceContractStatus
from src.api.invoices.schemas.invoice import InvoiceBase
from src.api.services.models.service_contract import ServiceContract
from src.api.services.schemas.service_contract import ServiceContractCreate, ServiceContractUpdate


class ServiceContractService:
    def __init__(self, db: Session):
        self.db = db

    def create_contract(self, contract_data: ServiceContractCreate) -> ServiceContract:
        """Create a new service contract"""
        contract = ServiceContract(
            service_id=contract_data.service_id,
            client_id=contract_data.client_id,
            contract_date=contract_data.contract_date,
            contract_amount=contract_data.contract_amount,
            contract_currency=contract_data.contract_currency,
            status=contract_data.status
        )

        self.db.add(contract)
        self.db.commit()
        self.db.refresh(contract)
        return contract

    def get_contract(self, contract_id: int) -> Optional[ServiceContract]:
        """Get an contract by ID"""
        return self.db.get(ServiceContract, contract_id)

    def get_contracts_by_service(self, service_id: int) -> List[ServiceContract]:
        """Get all contracts for a service"""
        return self.db.exec(select(ServiceContract).where(ServiceContract.service_id == service_id)).all()

    def get_contracts_by_client(self, client_id: int) -> List[ServiceContract]:
        """Get all contracts for a client"""
        return self.db.exec(select(ServiceContract).where(ServiceContract.client_id == client_id)).all()

    def update_contract_amount(self, contract_id: int, aggregated_amount: float = 0.0, invoice_id: Optional[int] = None) -> Optional[ServiceContract]:
        """Update a contract amount
        
        Args:
            contract_id: ID of the contract to update
            aggregated_amount: Amount to add to the contract
            invoice_id: Optional invoice ID to track which invoices have been processed
        """

        contract = self.db.get(ServiceContract, contract_id)
        if not contract:
            return None

        # Check if this invoice amount has already been added to the contract
        if invoice_id:
            # Check if we have any invoices with this ID already linked to this contract
            from src.api.invoices.models.invoice import Invoice
            existing_invoice = self.db.exec(
                select(Invoice).where(
                    Invoice.id == invoice_id,
                    Invoice.service_contract_id == contract_id
                )
            ).first()
            
            if existing_invoice:
                # This invoice is already linked and its amount should already be in contract_amount
                # Check if the contract_amount needs to be recalculated
                total_invoice_amount = sum(inv.total_amount for inv in contract.invoices if inv.service_contract_id == contract_id)
                
                # If contract_amount doesn't match total invoice amount, fix it
                if abs(contract.contract_amount - total_invoice_amount) > 0.01:
                    print(f'contract_amount_mismatch_fixing', f'contract_{contract_id}', 
                          f'current_amount_{contract.contract_amount}', f'total_invoices_{total_invoice_amount}')
                    contract.contract_amount = total_invoice_amount
                    self.db.add(contract)
                    self.db.commit()
                    self.db.refresh(contract)
                
                return contract

        # If no aggregated amount to add, return after checking invoice logic
        if not aggregated_amount or aggregated_amount == 0:
            return contract

        # Update status and corresponding date if contract_amount is changing
        old_amount = contract.contract_amount
        contract.contract_amount += aggregated_amount
        
        print(f'updating_contract_amount', f'contract_{contract_id}', 
              f'old_amount_{old_amount}', f'added_amount_{aggregated_amount}', 
              f'new_amount_{contract.contract_amount}')

        self.db.add(contract)
        self.db.commit()
        self.db.refresh(contract)
        return contract

    def update_contract_status(self, contract_id: int, contract_data: ServiceContractUpdate) -> Optional[ServiceContract]:
        """Update an contract status"""
        contract = self.db.get(ServiceContract, contract_id)
        if not contract:
            return None

        contract_data_dict = contract_data.model_dump(exclude_unset=True)

        # Update status and corresponding date if status is changing
        if "status" in contract_data_dict:
            new_status = contract_data_dict["status"]
            if new_status != contract.status:
                contract.status = new_status

        # Update other fields
        for key, value in contract_data_dict.items():
            if key != "status":  # We already handled status above
                setattr(contract, key, value)

        self.db.add(contract)
        self.db.commit()
        self.db.refresh(contract)
        return contract

    def get_active_contracts(self, target_date: Optional[date] = None) -> List[ServiceContract]:
        """Get all active contracts on a specific date"""
        # Get all contracts
        contracts = self.db.exec(select(ServiceContract)).all()

        # Filter for active contracts on the target date
        active_contracts = []
        for contract in contracts:
            service = self.db.get(Service, contract.service_id)

            # Check if the contract is active on the target date
            if (contract.status == ServiceContractStatus.ACTIVE and (target_date is None or service.start_date <= target_date <= service.end_date)):
                active_contracts.append(contract)

        return active_contracts

    def get_service_contract_by_client_and_service(self, client_id: int, service_id: int) -> Optional[ServiceContract]:
        """Retrieve a service contract by client and service IDs"""
        return self.db.exec(select(ServiceContract).where(
            (ServiceContract.client_id == client_id) &
            (ServiceContract.service_id == service_id)
        )).first()

    def create_service_contract(self, client_id: int, service_id: int, first_invoice: InvoiceBase) -> ServiceContract:
        """Create a new service contract for a given client and service"""
        contract_data = ServiceContract(
            client_id=client_id,
            service_id=service_id,
            # Assuming contract starts with first invoice
            contract_date=first_invoice.invoice_date,
            contract_amount=first_invoice.total_amount,
            contract_currency="EUR",  # Default currency
            status=ServiceContractStatus.ACTIVE  # Default status
        )
        self.db.add(contract_data)
        self.db.commit()
        self.db.refresh(contract_data)
        return contract_data
