from api.common.utils.database import get_db
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from datetime import date
from src.api.services.models.service import Service, ServiceEnrollment, ServiceStatus
from src.api.services.schemas.service import ServiceCreate, ServiceRead, ServiceUpdate, ServiceEnrollmentCreate, ServiceEnrollmentRead, ServiceEnrollmentUpdate
from src.api.services.services.service_service import ServiceService

router = APIRouter(prefix="/services", tags=["services"])


def get_service_service(db: Session = Depends(get_db)):
    return ServiceService(db)


@router.post("/", response_model=ServiceRead)
def create_service(
    service_data: ServiceCreate,
    service_service: ServiceService = Depends(get_service_service)
):
    """Create a new service"""
    return service_service.create_service(service_data)


@router.get("/{service_id}", response_model=ServiceRead)
def get_service(
    service_id: int,
    service_service: ServiceService = Depends(get_service_service)
):
    """Get a service by ID"""
    service = service_service.get_service(service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service


@router.get("/external/{external_id}", response_model=ServiceRead)
def get_service_by_external_id(
    external_id: str,
    service_service: ServiceService = Depends(get_service_service)
):
    """Get a service by external ID"""
    service = service_service.get_service_by_external_id(external_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service


@router.get("/", response_model=List[ServiceRead])
def get_services(
    skip: int = 0,
    limit: int = 100,
    service_service: ServiceService = Depends(get_service_service)
):
    """Get a list of services"""
    return service_service.get_services(skip, limit)


@router.put("/{service_id}", response_model=ServiceRead)
def update_service(
    service_id: int,
    service_data: ServiceUpdate,
    service_service: ServiceService = Depends(get_service_service)
):
    """Update a service"""
    service = service_service.update_service(service_id, service_data)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service


@router.delete("/{service_id}")
def delete_service(
    service_id: int,
    service_service: ServiceService = Depends(get_service_service)
):
    """Delete a service"""
    success = service_service.delete_service(service_id)
    if not success:
        raise HTTPException(status_code=404, detail="Service not found")
    return {"message": "Service deleted successfully"}


@router.post("/enrollments", response_model=ServiceEnrollmentRead)
def create_enrollment(
    enrollment_data: ServiceEnrollmentCreate,
    service_service: ServiceService = Depends(get_service_service)
):
    """Create a new service enrollment"""
    return service_service.create_enrollment(enrollment_data)


@router.get("/enrollments/{enrollment_id}", response_model=ServiceEnrollmentRead)
def get_enrollment(
    enrollment_id: int,
    service_service: ServiceService = Depends(get_service_service)
):
    """Get an enrollment by ID"""
    enrollment = service_service.get_enrollment(enrollment_id)
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    return enrollment


@router.get("/{service_id}/enrollments", response_model=List[ServiceEnrollmentRead])
def get_enrollments_by_service(
    service_id: int,
    service_service: ServiceService = Depends(get_service_service)
):
    """Get all enrollments for a service"""
    # Ensure the service exists
    service = service_service.get_service(service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    return service_service.get_enrollments_by_service(service_id)


@router.get("/enrollments/client/{client_id}", response_model=List[ServiceEnrollmentRead])
def get_enrollments_by_client(
    client_id: int,
    service_service: ServiceService = Depends(get_service_service)
):
    """Get all enrollments for a client"""
    return service_service.get_enrollments_by_client(client_id)


@router.put("/enrollments/{enrollment_id}", response_model=ServiceEnrollmentRead)
def update_enrollment_status(
    enrollment_id: int,
    enrollment_data: ServiceEnrollmentUpdate,
    service_service: ServiceService = Depends(get_service_service)
):
    """Update an enrollment status"""
    enrollment = service_service.update_enrollment_status(
        enrollment_id, enrollment_data)
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    return enrollment


@router.get("/enrollments/active-on-date", response_model=List[ServiceEnrollmentRead])
def get_active_enrollments_by_date(
    target_date: date,
    service_service: ServiceService = Depends(get_service_service)
):
    """Get all active enrollments on a specific date"""
    return service_service.get_active_enrollments_by_date(target_date)
