from datetime import date, timedelta
from api.common.utils.datetime import get_date
from api.services.constants import ServiceStatus
from api.services.services.service_period_service import ServicePeriodService
from src.api.common.utils.database import get_db
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.logger import logger
from src.api.services.schemas.service_period import ServicePeriodCreate
from src.api.services.services.service_contract import ServiceContractService
from sqlmodel import Session
from src.api.integrations.fourgeeks import FourGeeksClient, FourGeeksConfig, FourGeeksCredentials
from src.api.clients.services.client_service import ClientService
from src.api.services.services.service_service import ServiceService
from src.api.clients.schemas.client import ClientExternalIdCreate
from src.api.services.schemas.service import ServiceCreate
from src.api.services.schemas.service_contract import ServiceContractCreate

router = APIRouter(prefix="/integrations/4geeks", tags=["integrations"])


def _adjust_start_date_to_service(start_date_str: str | None, cohort_slug: str) -> Optional[date]:
    if start_date_str is None:
        return None
    start_date = get_date(start_date_str)
    if cohort_slug[0:8] in ["spain-fs", "spain-ds"]:
        # The start date is 2 weeks before the cohort start date becaus of the prework
        start_date = start_date - timedelta(weeks=2)
    return start_date


def get_client_service(db: Session = Depends(get_db)):
    return ClientService(db)


def get_service_service(db: Session = Depends(get_db)):
    return ServiceService(db)


def get_contract_service(db: Session = Depends(get_db)):
    return ServiceContractService(db)


def get_period_service(db: Session = Depends(get_db)):
    return ServicePeriodService(db)


def get_fourgeeks_client():
    config = FourGeeksConfig()
    credentials = FourGeeksCredentials(
        username=config.username,
        password=config.password
    )
    client = FourGeeksClient(credentials)
    client.login()  # Authenticates with 4Geeks API
    return client


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
    """Sync enrollments from 4Geeks to local contracts"""
    try:
        # Get enrollments from 4Geeks
        enrollments = fourgeeks_client.get_enrollments(academy_id)

        created_count = 0
        skipped_count = 0
        error_count = 0
        errors = []

        for enrollment in enrollments:
            try:
                # Get client by 4Geeks student ID
                student_id = enrollment.get("user_id")
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

                # Create contract
                contract_date = enrollment.get(
                    "created_at")  # Convert to date if needed

                contract_data = ServiceContractCreate(
                    service_id=service.id,
                    client_id=client.id,
                    contract_date=contract_date
                )

                service_service.create_contract(contract_data)
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


@router.get("/sync-enrollments-from-clients")
def sync_client_enrollments(
    client_service: ClientService = Depends(get_client_service),
    period_service: ServicePeriodService = Depends(get_period_service),
    contract_service: ServiceContractService = Depends(get_contract_service),
    fourgeeks_client: FourGeeksClient = Depends(get_fourgeeks_client)
):
    """Get all enrollments associated to client's 4Geeks users"""
    created_count = 0
    updated_count = 0
    skipped_count = 0
    error_count = 0
    errors = []

    try:
        contracts = contract_service.get_active_contracts()

        for contract in contracts:
            client = contract.client
            fourgeeks_external_ids = [external_id for external_id in client.external_ids if external_id.system == "fourgeeks"]
            if len(fourgeeks_external_ids) == 0:
                logger.error(
                    f"No fourgeeks external ID found for client {client.id}")
                skipped_count += 1
                continue
            fourgeeks_external_id = fourgeeks_external_ids[0].external_id

            service = contract.service
            # Start a new transaction for each contract
            try:
                client_enrollments = fourgeeks_client.get_user_enrollments(
                    user_id=fourgeeks_external_id, params={"roles": "STUDENT"})
                for enrollment in client_enrollments:
                    # Start a new transaction for each enrollment
                    cohort = enrollment.get("cohort", {})
                    cohort_slug = cohort.get("slug")
                    if not cohort_slug:
                        skipped_count += 1
                        continue

                    start_date = cohort.get("kickoff_date")
                    end_date = cohort.get("ending_date", None)
                    educational_status = enrollment.get("educational_status", ServiceStatus.ACTIVE)

                    if end_date is None:
                        skipped_count += 1
                        continue

                    if educational_status == "NOT_COMPLETING" or educational_status == "GRADUATED":
                        educational_status = ServiceStatus.ENDED

                    try:
                        # Check if period exists by external_id
                        existing_period = period_service.get_period_by_external_id(
                            contract.id, cohort_slug)

                        if existing_period:
                            # Update status if period exists
                            period_service.update_period_status(
                                existing_period.id,
                                educational_status
                            )
                            updated_count += 1
                        else:
                            # Create new period if it doesn't exist
                            period_data = ServicePeriodCreate(
                                contract_id=contract.id,
                                name=cohort_slug,
                                external_id=cohort_slug,
                                start_date=_adjust_start_date_to_service(
                                    start_date, cohort_slug),
                                end_date=get_date(end_date),
                                status=educational_status
                            )
                            period_service.create_period(period_data)
                            created_count += 1

                    except Exception as e:
                        error_count += 1
                        errors.append(
                            f"Error processing enrollment for {cohort_slug} in contract {contract.id}: {str(e)}")
                        # Ensure transaction is rolled back
                        client_service.db.rollback()

            except Exception as e:
                error_count += 1
                errors.append(
                    f"Error processing contract {contract.id}: {str(e)}")
        return {
            "success": True,
            "created": created_count,
            "updated": updated_count,
            "skipped": skipped_count,
            "errors": error_count,
            "error_details": errors,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync enrollments from clients: {str(e)}"
        )



@router.get("/sync-students-from-clients")
def sync_students_from_clients(
    client_service: ClientService = Depends(get_client_service),
    fourgeeks_client: FourGeeksClient = Depends(get_fourgeeks_client)
):
    """Sync clients in local database with 4Geeks students"""
    try:
        # Get all clients without a 4Geeks external ID
        clients = client_service.get_clients_with_no_external_id("fourgeeks")

        linked_count = 0
        not_found = []
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
                    not_found.append(client_email)
                    logger.error(
                        "No student was found with identifier " + client_email)
                    continue

                # If it's a list, find an exact match
                if isinstance(students_response, list):
                    student = None
                    for s in students_response:
                        try:
                            # Try to find an exact match by email
                            if s.get("email", "").lower() == client_email:
                                student = s
                            break
                        except Exception as e:
                            raise Exception(
                                f"Possible email confirmation pending in 4Geeks.com: {client_email}")
                    # If no exact match, take the first one if available
                    if not student and students_response:
                        student = students_response[0]
                else:
                    # Single student object
                    student = students_response

                if not student:
                    not_found.append(client_email)
                    logger.error(
                        "No student was found with identifier " + client_email)
                    continue

                # Add external ID to the client
                external_id_data = ClientExternalIdCreate(
                    system="fourgeeks",
                    external_id=str(student.get("user", {}).get("id"))
                )

                client_service.add_external_id(client.id, external_id_data)
                linked_count += 1

            except Exception as e:
                error_count += 1
                errors.append(f"Error processing client {client.id}: {str(e)}")

        return {
            "success": True,
            "linked": linked_count,
            "not_found": len(not_found),
            "errors": error_count,
            "error_details": errors,
            "not_found_details": not_found if len(not_found) > 0 else None
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync clients with 4Geeks students: {str(e)}"
        )
