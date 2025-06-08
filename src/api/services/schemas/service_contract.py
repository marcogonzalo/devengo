from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from src.api.common.constants.services import ServiceContractStatus


class ServiceContractBase(BaseModel):
    """Base schema for service contract data"""
    contract_date: date
    contract_amount: float
    contract_currency: str = "EUR"
    status: ServiceContractStatus = ServiceContractStatus.ACTIVE

    model_config = ConfigDict(from_attributes=True,
                              arbitrary_types_allowed=True)


class ServiceContractCreate(ServiceContractBase):
    """Schema for creating a new service contract"""
    service_id: int
    client_id: int


class ServiceContractRead(ServiceContractBase):
    """Schema for reading service contract data"""
    id: int
    service_id: int
    client_id: int
    created_at: datetime
    updated_at: datetime


class ServiceContractUpdate(BaseModel):
    """Schema for updating service contract data"""
    contract_amount: Optional[float] = None
    contract_currency: Optional[str] = None
    status: Optional[ServiceContractStatus] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)
