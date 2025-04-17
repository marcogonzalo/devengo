from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from src.api.common.utils.database import get_db
from src.api.services.services.service_period_service import ServicePeriodService
from src.api.services.schemas.service_period import (
    ServicePeriodCreate, ServicePeriodRead, ServicePeriodUpdate
)

router = APIRouter(tags=["service-periods"])


def get_service_period_service(db: Session = Depends(get_db)) -> ServicePeriodService:
    return ServicePeriodService(db)


@router.post("/periods", response_model=ServicePeriodRead)
def create_period(
    period_data: ServicePeriodCreate,
    service_period_service: ServicePeriodService = Depends(get_service_period_service)
):
    """Create a new service period"""
    return service_period_service.create_period(period_data)


@router.get("/periods/{period_id}", response_model=ServicePeriodRead)
def get_period(
    period_id: int,
    service_period_service: ServicePeriodService = Depends(get_service_period_service)
):
    """Get a service period by ID"""
    period = service_period_service.get_period(period_id)
    if not period:
        raise HTTPException(status_code=404, detail="Service period not found")
    return period


@router.get("/contracts/{contract_id}/periods", response_model=List[ServicePeriodRead])
def get_periods_by_contract(
    contract_id: int,
    service_period_service: ServicePeriodService = Depends(get_service_period_service)
):
    """Get all periods for a contract"""
    return service_period_service.get_periods_by_contract(contract_id)


@router.put("/periods/{period_id}", response_model=ServicePeriodRead)
def update_period(
    period_id: int,
    period_data: ServicePeriodUpdate,
    service_period_service: ServicePeriodService = Depends(get_service_period_service)
):
    """Update a service period"""
    period = service_period_service.update_period(period_id, period_data)
    if not period:
        raise HTTPException(status_code=404, detail="Service period not found")
    return period


@router.delete("/periods/{period_id}", response_model=bool)
def delete_period(
    period_id: int,
    service_period_service: ServicePeriodService = Depends(get_service_period_service)
):
    """Delete a service period"""
    result = service_period_service.delete_period(period_id)
    if not result:
        raise HTTPException(status_code=404, detail="Service period not found")
    return result 