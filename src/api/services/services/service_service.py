from typing import List, Optional, Dict, Any
from sqlmodel import Session, select
from datetime import date
from src.api.services.models.service import Service, ServiceEnrollment, ServiceStatus
from src.api.services.schemas.service import ServiceCreate, ServiceUpdate, ServiceEnrollmentCreate, ServiceEnrollmentUpdate


class ServiceService:
    def __init__(self, db: Session):
        self.db = db

    def create_service(self, service_data: ServiceCreate) -> Service:
        """Create a new service"""
        service = Service(
            external_id=service_data.external_id,
            name=service_data.name,
            description=service_data.description,
            start_date=service_data.start_date,
            end_date=service_data.end_date,
            total_classes=service_data.total_classes,
            classes_per_week=service_data.classes_per_week,
            class_days=service_data.class_days,
            total_cost=service_data.total_cost,
            currency=service_data.currency
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

    def update_service(self, service_id: int, service_data: ServiceUpdate) -> Optional[Service]:
        """Update a service"""
        service = self.db.get(Service, service_id)
        if not service:
            return None

        service_data_dict = service_data.dict(exclude_unset=True)
        for key, value in service_data_dict.items():
            setattr(service, key, value)

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

    def create_enrollment(self, enrollment_data: ServiceEnrollmentCreate) -> ServiceEnrollment:
        """Create a new service enrollment"""
        enrollment = ServiceEnrollment(
            service_id=enrollment_data.service_id,
            client_id=enrollment_data.client_id,
            enrollment_date=enrollment_data.enrollment_date,
            status=enrollment_data.status
        )

        self.db.add(enrollment)
        self.db.commit()
        self.db.refresh(enrollment)
        return enrollment

    def get_enrollment(self, enrollment_id: int) -> Optional[ServiceEnrollment]:
        """Get an enrollment by ID"""
        return self.db.get(ServiceEnrollment, enrollment_id)

    def get_enrollments_by_service(self, service_id: int) -> List[ServiceEnrollment]:
        """Get all enrollments for a service"""
        return self.db.exec(select(ServiceEnrollment).where(ServiceEnrollment.service_id == service_id)).all()

    def get_enrollments_by_client(self, client_id: int) -> List[ServiceEnrollment]:
        """Get all enrollments for a client"""
        return self.db.exec(select(ServiceEnrollment).where(ServiceEnrollment.client_id == client_id)).all()

    def update_enrollment_status(self, enrollment_id: int, enrollment_data: ServiceEnrollmentUpdate) -> Optional[ServiceEnrollment]:
        """Update an enrollment status"""
        enrollment = self.db.get(ServiceEnrollment, enrollment_id)
        if not enrollment:
            return None

        enrollment_data_dict = enrollment_data.dict(exclude_unset=True)

        # Update status and corresponding date if status is changing
        if "status" in enrollment_data_dict:
            new_status = enrollment_data_dict["status"]
            if new_status != enrollment.status:
                enrollment.status = new_status

                # Set the appropriate date based on the new status
                if new_status == ServiceStatus.POSTPONED:
                    enrollment.postponed_date = date.today()
                elif new_status == ServiceStatus.DROPPED:
                    enrollment.dropped_date = date.today()
                elif new_status == ServiceStatus.COMPLETED:
                    enrollment.completed_date = date.today()

        # Update other fields
        for key, value in enrollment_data_dict.items():
            if key != "status":  # We already handled status above
                setattr(enrollment, key, value)

        self.db.add(enrollment)
        self.db.commit()
        self.db.refresh(enrollment)
        return enrollment

    def get_active_enrollments_by_date(self, target_date: date) -> List[ServiceEnrollment]:
        """Get all active enrollments on a specific date"""
        # Get all enrollments
        enrollments = self.db.exec(select(ServiceEnrollment)).all()

        # Filter for active enrollments on the target date
        active_enrollments = []
        for enrollment in enrollments:
            service = self.db.get(Service, enrollment.service_id)

            # Check if the enrollment is active on the target date
            if (service.start_date <= target_date <= service.end_date and
                    enrollment.status == ServiceStatus.ACTIVE):
                active_enrollments.append(enrollment)

            # Check if the enrollment was active before being postponed/dropped
            elif (enrollment.status == ServiceStatus.POSTPONED and
                  enrollment.postponed_date and
                  service.start_date <= target_date and
                  target_date < enrollment.postponed_date):
                active_enrollments.append(enrollment)

            elif (enrollment.status == ServiceStatus.DROPPED and
                  enrollment.dropped_date and
                  service.start_date <= target_date and
                  target_date < enrollment.dropped_date):
                active_enrollments.append(enrollment)

        return active_enrollments
