from typing import List
from fastapi import HTTPException, APIRouter
from fastapi.params import Depends
from sqlmodel import Session
from datetime import date
from src.api.common.utils.database import get_db
from src.api.services.schemas.service_contract import ServiceContractRead, ServiceContractUpdate, ServiceContractCreate
from src.api.services.services.service_contract import ServiceContractService
from src.api.services.services.service_service import ServiceService


router = APIRouter(prefix="/service-contracts", tags=["service-contracts"])


def get_service_contract_service(db: Session = Depends(get_db)):
    return ServiceContractService(db)


def get_service_service(db: Session = Depends(get_db)):
    return ServiceService(db)


@router.post("", response_model=ServiceContractRead)
def create_contract(
    contract_data: ServiceContractCreate,
    service_service: ServiceService = Depends(get_service_service)
):
    """Create a new service contract"""
    return service_service.create_contract(contract_data)


@router.get("/{contract_id}", response_model=ServiceContractRead)
def get_contract(
    contract_id: int,
    service_service: ServiceService = Depends(get_service_service)
):
    """Get a contract by ID"""
    contract = service_service.get_contract(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract


@router.get("/{service_id}/contracts", response_model=List[ServiceContractRead])
def get_contracts_by_service(
    service_id: int,
    service_service: ServiceService = Depends(get_service_service)
):
    """Get all contracts for a service"""
    # Ensure the service exists
    service = service_service.get_service(service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    return service_service.get_contracts_by_service(service_id)


@router.get("/client/{client_id}", response_model=List[ServiceContractRead])
def get_contracts_by_client(
    client_id: int,
    service_service: ServiceService = Depends(get_service_service)
):
    """Get all contracts for a client"""
    return service_service.get_contracts_by_client(client_id)


@router.put("/{contract_id}", response_model=ServiceContractRead)
def update_contract_status(
    contract_id: int,
    contract_data: ServiceContractUpdate,
    service_contract_service: ServiceContractService = Depends(get_service_contract_service)
):
    """Update a contract status"""
    contract = service_contract_service.update_contract_status(
        contract_id, contract_data)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract


@router.get("/active-on-date", response_model=List[ServiceContractRead])
def get_active_contracts_by_date(
    target_date: date,
    service_service: ServiceContractService = Depends(get_service_contract_service)
):
    """Get all active contracts on a specific date"""
    return service_service.get_active_contracts_by_date(target_date)
