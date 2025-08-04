from typing import List, Optional, Union, Dict
from sqlmodel import Session, select
from datetime import date
from src.api.services.models.service import Service
from src.api.services.schemas.service import ServiceCreate, ServiceUpdate
from src.api.services.utils import get_service_type_from_service_name


class ServiceService:
    def __init__(self, db: Session):
        self.db = db

    def create_service(self, service_data: Union[ServiceCreate, Dict]) -> Service:
        """Create a new service"""
        if isinstance(service_data, dict):
            # Handle dictionary input
            service_name = service_data.get('name')
            service_type = service_data.get('service_type') or get_service_type_from_service_name(service_name)
            
            service = Service(
                external_id=service_data.get('external_id'),
                name=service_name,
                description=service_data.get('description'),
                account_identifier=service_data.get('account_identifier'),
                service_type=service_type,
                total_sessions=service_data.get('total_sessions', 60),
                sessions_per_week=service_data.get('sessions_per_week', 3)
            )
        else:
            # Handle Pydantic model input
            service_name = service_data.name
            service_type = getattr(service_data, 'service_type', None) or get_service_type_from_service_name(service_name)
            
            service = Service(
                external_id=service_data.external_id,
                name=service_name,
                description=service_data.description,
                account_identifier=getattr(service_data, 'account_identifier', None),
                service_type=service_type,
                total_sessions=getattr(service_data, 'total_sessions', 60),
                sessions_per_week=getattr(service_data, 'sessions_per_week', 3)
            )

        self.db.add(service)
        self.db.commit()
        self.db.refresh(service)
        return service

    def get_service(self, service_id: int) -> Optional[Service]:
        """Get a service by ID"""
        return self.db.get(Service, service_id)

    def get_service_by_external_id(self, external_id: str) -> Optional[Service]:
        """Get a service by external ID"""
        return self.db.exec(select(Service).where(Service.external_id == external_id)).first()

    def get_services(self, skip: int = 0, limit: int = 100) -> List[Service]:
        """Get a list of services"""
        return self.db.exec(select(Service).offset(skip).limit(limit)).all()

    def update_service(self, service_id: int, service_data: Union[ServiceUpdate, Dict]) -> Optional[Service]:
        """Update a service"""
        service = self.db.get(Service, service_id)
        if not service:
            return None

        if isinstance(service_data, dict):
            # Handle dictionary input
            for key, value in service_data.items():
                setattr(service, key, value)
            
            # Auto-update service_type if name changed and service_type not explicitly set
            if 'name' in service_data and 'service_type' not in service_data:
                service.service_type = get_service_type_from_service_name(service.name)
        else:
            # Handle Pydantic model input
            service_data_dict = service_data.model_dump(exclude_unset=True)
            for key, value in service_data_dict.items():
                setattr(service, key, value)
            
            # Auto-update service_type if name changed and service_type not explicitly set
            if 'name' in service_data_dict and 'service_type' not in service_data_dict:
                service.service_type = get_service_type_from_service_name(service.name)

        self.db.add(service)
        self.db.commit()
        self.db.refresh(service)
        return service

    def delete_service(self, service_id: int) -> bool:
        """Delete a service"""
        service = self.db.get(Service, service_id)
        if not service:
            return False

        self.db.delete(service)
        self.db.commit()
        return True

