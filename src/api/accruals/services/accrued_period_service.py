from datetime import date
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import extract

from src.api.common.constants.services import ServiceContractStatus

from src.api.accruals.models.accrued_period import AccruedPeriod
from src.api.accruals.schemas import AccruedPeriodCreate, AccruedPeriodUpdate


class AccruedPeriodService:
    def __init__(self, db: Session):
        self.db = db

    def get_accrual(self, accrual_id: int) -> Optional[AccruedPeriod]:
        return self.db.query(AccruedPeriod).filter(AccruedPeriod.id == accrual_id).first()

    def get_accruals_by_contract(self, contract_id: int) -> List[AccruedPeriod]:
        return (
            self.db.query(AccruedPeriod)
            .join(AccruedPeriod.contract_accrual)
            .filter(AccruedPeriod.contract_accrual.has(contract_id=contract_id))
            .all()
        )

    def get_accruals_by_period(self, year: int, month: int) -> List[AccruedPeriod]:
        return (
            self.db.query(AccruedPeriod)
            .filter(
                extract('year', AccruedPeriod.accrual_date) == year,
                extract('month', AccruedPeriod.accrual_date) == month
            )
            .all()
        )

    def create_accrual(self, accrual_data: AccruedPeriodCreate) -> AccruedPeriod:
        accrual = AccruedPeriod(**accrual_data.model_dump())
        self.db.add(accrual)
        self.db.commit()
        self.db.refresh(accrual)
        return accrual

    def update_accrual(self, accrual_id: int, accrual_data: AccruedPeriodUpdate) -> Optional[AccruedPeriod]:
        accrual = self.get_accrual(accrual_id)
        if not accrual:
            return None

        update_data = accrual_data.model_dump(exclude_unset=True)

        # If status is being updated to POSTPONED or DROPPED, set status_change_date
        if "status" in update_data and update_data["status"] in [ServiceContractStatus.POSTPONED, ServiceContractStatus.DROPPED]:
            update_data["status_change_date"] = date.today()

        for field, value in update_data.items():
            setattr(accrual, field, value)

        self.db.commit()
        self.db.refresh(accrual)
        return accrual

    def delete_accrual(self, accrual_id: int) -> bool:
        accrual = self.get_accrual(accrual_id)
        if not accrual:
            return False

        self.db.delete(accrual)
        self.db.commit()
        return True
