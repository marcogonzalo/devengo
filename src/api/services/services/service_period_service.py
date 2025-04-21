from typing import List, Optional
from sqlmodel import Session, select
from datetime import date
from src.api.services.models.service_period import ServicePeriod
from src.api.services.schemas.service_period import ServicePeriodCreate, ServicePeriodUpdate
from api.common.constants.services import ServiceStatus


class ServicePeriodService:
    def __init__(self, db: Session):
        self.db = db

    def create_period(self, period_data: ServicePeriodCreate) -> ServicePeriod:
        """Create a new service period"""
        period = ServicePeriod(**period_data.model_dump())

        self.db.add(period)
        self.db.commit()
        self.db.refresh(period)
        return period

    def get_period(self, period_id: int) -> Optional[ServicePeriod]:
        """Get a period by ID"""
        return self.db.get(ServicePeriod, period_id)

    def get_periods_by_contract(self, contract_id: int) -> List[ServicePeriod]:
        """Get all periods for a contract"""
        return self.db.exec(select(ServicePeriod).where(ServicePeriod.contract_id == contract_id)).all()

    def get_period_by_external_id(self, contract_id: int, external_id: str) -> Optional[ServicePeriod]:
        """Get a period by name or external ID"""
        statement = select(ServicePeriod).where(
            ServicePeriod.contract_id == contract_id,
            ServicePeriod.external_id == external_id
        )
        return self.db.exec(statement).first()

    def get_active_periods_by_date(self, target_date: date) -> List[ServicePeriod]:
        """Get all active periods on a specific date"""
        return self.db.exec(
            select(ServicePeriod).where(
                (ServicePeriod.start_date <= target_date) & 
                (ServicePeriod.end_date >= target_date) &
                (ServicePeriod.status == ServiceStatus.ACTIVE)
            )
        ).all()

    def update_period(self, period_id: int, period_data: ServicePeriodUpdate) -> Optional[ServicePeriod]:
        """Update a service period"""
        period = self.db.get(ServicePeriod, period_id)
        if not period:
            return None

        period_data_dict = period_data.model_dump(exclude_unset=True)
        for key, value in period_data_dict.items():
            setattr(period, key, value)

        self.db.add(period)
        self.db.commit()
        self.db.refresh(period)
        return period

    def update_period_status(self, period_id: int, status: ServiceStatus) -> Optional[ServicePeriod]:
        """Update the status of a service period"""
        period = self.db.get(ServicePeriod, period_id)
        if not period:
            return None

        period.status = status
        self.db.add(period)
        self.db.commit()
        self.db.refresh(period)
        return period

    def delete_period(self, period_id: int) -> bool:
        """Delete a service period"""
        period = self.db.get(ServicePeriod, period_id)
        if not period:
            return False

        self.db.delete(period)
        self.db.commit()
        return True 