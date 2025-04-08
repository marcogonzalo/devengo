from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from api.accrual.schemas.accrual import AccrualPeriodCreate, AccrualPeriodRead, AccrualClassDistributionCreate, AccrualClassDistributionRead
from api.accrual.services.accrual_service import AccrualService
from api.common.utils.database import get_db

router = APIRouter(prefix="/accruals", tags=["accruals"])


def get_accrual_service(db: Session = Depends(get_db)):
    return AccrualService(db)


@router.post("/periods", response_model=AccrualPeriodRead)
def create_accrual_period(
    period_data: AccrualPeriodCreate,
    accrual_service: AccrualService = Depends(get_accrual_service)
):
    """Create a new accrual period"""
    return accrual_service.create_accrual_period(period_data)


@router.get("/periods/{period_id}", response_model=AccrualPeriodRead)
def get_accrual_period(
    period_id: int,
    accrual_service: AccrualService = Depends(get_accrual_service)
):
    """Get an accrual period by ID"""
    period = accrual_service.get_accrual_period(period_id)
    if not period:
        raise HTTPException(status_code=404, detail="Accrual period not found")
    return period


@router.get("/periods", response_model=List[AccrualPeriodRead])
def get_accrual_periods(
    skip: int = 0,
    limit: int = 100,
    accrual_service: AccrualService = Depends(get_accrual_service)
):
    """Get a list of accrual periods"""
    return accrual_service.get_accrual_periods(skip, limit)


@router.get("/periods/by-month-year", response_model=AccrualPeriodRead)
def get_accrual_period_by_month_year(
    year: int,
    month: int,
    accrual_service: AccrualService = Depends(get_accrual_service)
):
    """Get an accrual period by month and year"""
    period = accrual_service.get_accrual_period_by_month_year(year, month)
    if not period:
        raise HTTPException(status_code=404, detail="Accrual period not found")
    return period


@router.post("/periods/{period_id}/process", response_model=AccrualPeriodRead)
def mark_period_as_processed(
    period_id: int,
    accrual_service: AccrualService = Depends(get_accrual_service)
):
    """Mark an accrual period as processed"""
    period = accrual_service.mark_period_as_processed(period_id)
    if not period:
        raise HTTPException(status_code=404, detail="Accrual period not found")
    return period


@router.post("/class-distributions", response_model=AccrualClassDistributionRead)
def create_class_distribution(
    distribution_data: AccrualClassDistributionCreate,
    accrual_service: AccrualService = Depends(get_accrual_service)
):
    """Create a new class distribution for a service in a specific month"""
    return accrual_service.create_class_distribution(distribution_data)


@router.get("/class-distributions/service/{service_id}", response_model=List[AccrualClassDistributionRead])
def get_class_distributions_by_service(
    service_id: int,
    accrual_service: AccrualService = Depends(get_accrual_service)
):
    """Get all class distributions for a service"""
    return accrual_service.get_class_distributions_by_service(service_id)


@router.get("/class-distributions/by-month-year", response_model=List[AccrualClassDistributionRead])
def get_class_distributions_by_month_year(
    year: int,
    month: int,
    accrual_service: AccrualService = Depends(get_accrual_service)
):
    """Get all class distributions for a specific month and year"""
    return accrual_service.get_class_distributions_by_month_year(year, month)


@router.post("/service/{service_id}/calculate-distribution", response_model=List[AccrualClassDistributionRead])
def calculate_class_distribution(
    service_id: int,
    accrual_service: AccrualService = Depends(get_accrual_service)
):
    """Calculate the distribution of classes per month for a service"""
    distributions = accrual_service.calculate_class_distribution(service_id)
    if not distributions:
        raise HTTPException(
            status_code=404, detail="Service not found or no distributions calculated")
    return distributions


@router.post("/process-period", response_model=Dict[str, Any])
def process_accruals_for_period(
    year: int,
    month: int,
    accrual_service: AccrualService = Depends(get_accrual_service)
):
    """Process accruals for a specific period (month/year)"""
    accruals_created, errors = accrual_service.process_accruals_for_period(
        year, month)

    return {
        "success": len(errors) == 0,
        "accruals_created": accruals_created,
        "errors": errors
    }
