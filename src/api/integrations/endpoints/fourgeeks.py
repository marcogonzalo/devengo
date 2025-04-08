from api.common.utils.database import get_db
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.logger import logger
from sqlmodel import Session
from src.api.integrations.fourgeeks import FourGeeksClient, FourGeeksConfig, FourGeeksCredentials
from src.api.clients.services.client_service import ClientService
from src.api.services.services.service_service import ServiceService
from src.api.clients.schemas.client import ClientCreate, ClientExternalIdCreate
from src.api.services.schemas.service import ServiceCreate, ServiceEnrollmentCreate

router = APIRouter(prefix="/integrations/4geeks", tags=["integrations"])


def get_client_service(db: Session = Depends(get_db)):
    return ClientService(db)


def get_service_service(db: Session = Depends(get_db)):
    return ServiceService(db)


def get_fourgeeks_client():
    config = FourGeeksConfig()
    credentials = FourGeeksCredentials(
        username=config.username,
        password=config.password
    )
    client = FourGeeksClient(credentials)
    client.login()  # Authenticates with 4Geeks API
    return client


@router.get("/sync-students")
def sync_students(
    client_service: ClientService = Depends(get_client_service),
    fourgeeks_client: FourGeeksClient = Depends(get_fourgeeks_client),
    academy_id: Optional[int] = None
):
    """Sync students from 4Geeks to the local database"""
    try:
        students = fourgeeks_client.get_students(academy_id=academy_id)

        created_count = 0
        skipped_count = 0
        error_count = 0
        errors = []

        for student in students:
            try:
                # Check if client already exists by external ID
                existing_client = client_service.get_client_by_external_id(
                    "fourgeeks", student.get("id"))

                if existing_client:
                    skipped_count += 1
                    continue

                # Create new client
                email = student.get("email")
                if not email:
                    skipped_count += 1
                    continue

                client_data = ClientCreate(
                    identifier=email,
                    name=f"{student.get('first_name', '')} {student.get('last_name', '')}"
                )

                client = client_service.create_client(client_data)

                # Add external ID
                external_id_data = ClientExternalIdCreate(
                    system="fourgeeks",
                    external_id=str(student.get("id"))
                )

                client_service.add_external_id(client.id, external_id_data)

                created_count += 1

            except Exception as e:
                error_count += 1
                errors.append(str(e))

        return {
            "success": True,
            "created": created_count,
            "skipped": skipped_count,
            "errors": error_count,
            "error_details": errors
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync students: {str(e)}"
        )


@router.get("/sync-cohorts")
def sync_cohorts(
    service_service: ServiceService = Depends(get_service_service),
    fourgeeks_client: FourGeeksClient = Depends(get_fourgeeks_client),
    academy_id: Optional[int] = None
):
    """Sync cohorts from 4Geeks to the local database"""
    try:
        cohorts = fourgeeks_client.get_cohorts(academy_id=academy_id)

        created_count = 0
        skipped_count = 0
        error_count = 0
        errors = []

        for cohort in cohorts:
            try:
                # Check if service already exists by external ID
                existing_service = service_service.get_service_by_external_id(
                    str(cohort.get("id")))

                if existing_service:
                    skipped_count += 1
                    continue

                # Create new service
                # Convert to date if needed
                start_date = cohort.get("kickoff_date")
                # Convert to date if needed
                end_date = cohort.get("ending_date")

                if not start_date or not end_date:
                    skipped_count += 1
                    continue

                # Convert schedule to class days format (e.g., "Mon,Wed")
                schedule = cohort.get("schedule") or {}
                class_days = ",".join(
                    [day for day, enabled in schedule.items() if enabled])

                service_data = ServiceCreate(
                    external_id=str(cohort.get("id")),
                    name=cohort.get("name", ""),
                    description=cohort.get("syllabus", {}).get("name", ""),
                    start_date=start_date,
                    end_date=end_date,
                    total_classes=cohort.get(
                        "syllabus", {}).get("total_duration", 0),
                    classes_per_week=2,  # This should be calculated based on schedule
                    class_days=class_days,
                    total_cost=cohort.get("price", 0.0),
                    currency="EUR"
                )

                service = service_service.create_service(service_data)
                created_count += 1

            except Exception as e:
                error_count += 1
                errors.append(str(e))

        return {
            "success": True,
            "created": created_count,
            "skipped": skipped_count,
            "errors": error_count,
            "error_details": errors
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync cohorts: {str(e)}"
        )


@router.get("/sync-enrollments")
def sync_enrollments(
    client_service: ClientService = Depends(get_client_service),
    service_service: ServiceService = Depends(get_service_service),
    fourgeeks_client: FourGeeksClient = Depends(get_fourgeeks_client),
    academy_id: Optional[int] = None
):
    """Sync enrollments from 4Geeks to the local database"""
    try:
        enrollments = fourgeeks_client.get_enrollments(academy_id=academy_id)

        created_count = 0
        skipped_count = 0
        error_count = 0
        errors = []

        for enrollment in enrollments:
            try:
                # Get client by 4Geeks student ID
                student_id = enrollment.get("student_id")
                client = client_service.get_client_by_external_id(
                    "fourgeeks", str(student_id))

                if not client:
                    skipped_count += 1
                    continue

                # Get service by 4Geeks cohort ID
                cohort_id = enrollment.get("cohort_id")
                service = service_service.get_service_by_external_id(
                    str(cohort_id))

                if not service:
                    skipped_count += 1
                    continue

                # Create enrollment
                enrollment_date = enrollment.get(
                    "created_at")  # Convert to date if needed

                enrollment_data = ServiceEnrollmentCreate(
                    service_id=service.id,
                    client_id=client.id,
                    enrollment_date=enrollment_date
                )

                service_service.create_enrollment(enrollment_data)
                created_count += 1

            except Exception as e:
                error_count += 1
                errors.append(str(e))

        return {
            "success": True,
            "created": created_count,
            "skipped": skipped_count,
            "errors": error_count,
            "error_details": errors
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync enrollments: {str(e)}"
        )


@router.get("/sync-students-from-clients")
def sync_students_from_clients(
    client_service: ClientService = Depends(get_client_service),
    fourgeeks_client: FourGeeksClient = Depends(get_fourgeeks_client),
    academy_id: Optional[int] = None
):
    """Sync clients in local database with 4Geeks students"""
    try:
        # Get all clients without a 4Geeks external ID
        clients = client_service.get_clients_without_external_id("fourgeeks")

        linked_count = 0
        not_found_count = 0
        error_count = 0
        errors = []

        for client in clients:
            try:
                # Get client identifier (email)
                client_email = client.identifier.lower()

                # Search for the student in 4Geeks by email
                # The get_student_by_email method returns a list of students or a single student
                students_response = fourgeeks_client.get_student_by_email(
                    email=client_email)

                # Handle different response formats
                if not students_response:
                    logger.error(
                        "No student was found with identifier " + client_email)

                    not_found_count += 1
                    continue

                # If it's a list, find an exact match
                if isinstance(students_response, list):
                    student = None
                    for s in students_response:
                        # Try to find an exact match by email
                        if s.get("email", "").lower() == client_email:
                            student = s
                            break

                    # If no exact match, take the first one if available
                    if not student and students_response:
                        student = students_response[0]
                else:
                    # Single student object
                    student = students_response

                if not student:
                    not_found_count += 1
                    logger.error(
                        "No student was found with identifier " + client_email)
                    continue

                # Add external ID to the client
                external_id_data = ClientExternalIdCreate(
                    system="fourgeeks",
                    external_id=str(student.get("id"))
                )

                client_service.add_external_id(client.id, external_id_data)
                linked_count += 1

            except Exception as e:
                error_count += 1
                errors.append(f"Error processing client {client.id}: {str(e)}")

        return {
            "success": True,
            "linked": linked_count,
            "not_found": not_found_count,
            "errors": error_count,
            "error_details": errors
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync clients with 4Geeks students: {str(e)}"
        )
