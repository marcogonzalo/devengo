from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.api.common.utils.database import get_db
from src.api.accruals.schemas import AccruedPeriodCreate, AccruedPeriodUpdate, AccruedPeriodResponse
from src.api.accruals.services.accrued_period_service import AccruedPeriodService

router = APIRouter(prefix="/accruals", tags=["accruals"])


@router.post("", response_model=AccruedPeriodResponse)
def create_accrual(
    accrual_data: AccruedPeriodCreate,
    db: Session = Depends(get_db)
):
    service = AccruedPeriodService(db)
    return service.create_accrual(accrual_data)


@router.get("/contract/{contract_id}", response_model=List[AccruedPeriodResponse])
def get_accruals_by_contract(
    contract_id: int,
    db: Session = Depends(get_db)
):
    service = AccruedPeriodService(db)
    return service.get_accruals_by_contract(contract_id)


@router.get("/period/", response_model=List[AccruedPeriodResponse])
def get_accruals_by_period(
    year: int = Query(..., description="Year of the accrual period"),
    month: int = Query(..., ge=1, le=12,
                       description="Month of the accrual period"),
    db: Session = Depends(get_db)
):
    service = AccruedPeriodService(db)
    return service.get_accruals_by_period(year, month)


@router.get("/{accrual_id}", response_model=AccruedPeriodResponse)
def get_accrual(
    accrual_id: int,
    db: Session = Depends(get_db)
):
    service = AccruedPeriodService(db)
    accrual = service.get_accrual(accrual_id)
    if not accrual:
        raise HTTPException(status_code=404, detail="Accrual not found")
    return accrual


@router.patch("/{accrual_id}", response_model=AccruedPeriodResponse)
def update_accrual(
    accrual_id: int,
    accrual_data: AccruedPeriodUpdate,
    db: Session = Depends(get_db)
):
    service = AccruedPeriodService(db)
    accrual = service.update_accrual(accrual_id, accrual_data)
    if not accrual:
        raise HTTPException(status_code=404, detail="Accrual not found")
    return accrual


@router.delete("/{accrual_id}")
def delete_accrual(
    accrual_id: int,
    db: Session = Depends(get_db)
):
    service = AccruedPeriodService(db)
    if not service.delete_accrual(accrual_id):
        raise HTTPException(status_code=404, detail="Accrual not found")
    return {"message": "Accrual deleted successfully"}
