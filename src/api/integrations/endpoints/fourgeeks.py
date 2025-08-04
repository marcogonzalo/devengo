import os
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.logger import logger
from fastapi.responses import JSONResponse
from sqlmodel import Session
from src.api.integrations.fourgeeks.log_error import log_contract_error, log_student_error
from src.api.services.services.service_period_service import ServicePeriodService
from src.api.common.utils.database import get_db
from src.api.services.services.service_contract import ServiceContractService
from src.api.integrations.fourgeeks import FourGeeksClient, FourGeeksConfig, FourGeeksCredentials
from src.api.clients.services.client_service import ClientService
from src.api.services.services.service_service import ServiceService
from src.api.integrations.fourgeeks.processor import EnrollmentProcessor, StudentProcessor

router = APIRouter(prefix="/integrations/fourgeeks", tags=["integrations"])


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


@router.route('/test', methods=['GET'])
def test_fourgeeks_integration(request: Request):
    """
    Test endpoint to verify 4Geeks API integration is working correctly.
    It will attempt to authenticate and get a token.
    """
    try:
        # Initialize 4Geeks client
        config = FourGeeksConfig()
        client = FourGeeksClient(FourGeeksCredentials(
            username=config.username,
            password=config.password
        ))

        # Test authentication
        client.login()

        return JSONResponse(content={
            "status": "success",
            "message": "4Geeks integration is working correctly",
            "data": {
                "authenticated": True
            }
        })

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"4Geeks integration test failed: {str(e)}"
        )


# @router.get("/sync-cohorts")
# def sync_cohorts(
#     service_service: ServiceService = Depends(get_service_service),
#     fourgeeks_client: FourGeeksClient = Depends(get_fourgeeks_client),
#     academy_id: Optional[int] = None
# ):
#     """Sync cohorts from 4Geeks to the local database"""
#     try:
#         cohorts = fourgeeks_client.get_cohorts(academy_id=academy_id)

#         created_count = 0
#         skipped_count = 0
#         error_count = 0
#         errors = []

#         for cohort in cohorts:
#             try:
#                 # Check if service already exists by external ID
#                 existing_service = service_service.get_service_by_external_id(
#                     str(cohort.get("id")))

#                 if existing_service:
#                     skipped_count += 1
#                     continue

#                 # Create new service
#                 # Convert to date if needed
#                 start_date = cohort.get("kickoff_date")
#                 # Convert to date if needed
#                 end_date = cohort.get("ending_date")

#                 if not start_date or not end_date:
#                     skipped_count += 1
#                     continue

#                 # Convert schedule to class days format (e.g., "Mon,Wed")
#                 schedule = cohort.get("schedule") or {}
#                 class_days = ",".join(
#                     [day for day, enabled in schedule.items() if enabled])

#                 service_data = ServiceCreate(
#                     external_id=str(cohort.get("id")),
#                     name=cohort.get("name", ""),
#                     description=cohort.get("syllabus", {}).get("name", ""),
#                     start_date=start_date,
#                     end_date=end_date,
#                     total_classes=cohort.get(
#                         "syllabus", {}).get("total_duration", 0),
#                     classes_per_week=2,  # This should be calculated based on schedule
#                     class_days=class_days,
#                     total_cost=cohort.get("price", 0.0),
#                     currency="EUR"
#                 )

#                 service = service_service.create_service(service_data)
#                 created_count += 1

#             except Exception as e:
#                 error_count += 1
#                 errors.append(str(e))

#         return {
#             "success": True,
#             "created": created_count,
#             "skipped": skipped_count,
#             "errors": error_count,
#             "error_details": errors
#         }

#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to sync cohorts: {str(e)}"
#         )


# @router.get("/sync-enrollments")
# def sync_enrollments(
#     client_service: ClientService = Depends(get_client_service),
#     service_service: ServiceService = Depends(get_service_service),
#     fourgeeks_client: FourGeeksClient = Depends(get_fourgeeks_client),
#     academy_id: Optional[int] = None
# ):
#     """Sync enrollments from 4Geeks to local contracts"""
#     try:
#         # Get enrollments from 4Geeks
#         enrollments = fourgeeks_client.get_enrollments(academy_id)

#         created_count = 0
#         skipped_count = 0
#         error_count = 0
#         errors = []

#         for enrollment in enrollments:
#             try:
#                 # Get client by 4Geeks student ID
#                 student_id = enrollment.get("user_id")
#                 client = client_service.get_client_by_external_id(
#                     "fourgeeks", str(student_id))

#                 if not client:
#                     skipped_count += 1
#                     continue

#                 # Get service by 4Geeks cohort ID
#                 cohort_id = enrollment.get("cohort_id")
#                 service = service_service.get_service_by_external_id(
#                     str(cohort_id))

#                 if not service:
#                     skipped_count += 1
#                     continue

#                 # Create contract
#                 contract_date = enrollment.get(
#                     "created_at")  # Convert to date if needed

#                 contract_data = ServiceContractCreate(
#                     service_id=service.id,
#                     client_id=client.id,
#                     contract_date=contract_date
#                 )

#                 service_service.create_contract(contract_data)
#                 created_count += 1

#             except Exception as e:
#                 error_count += 1
#                 errors.append(str(e))

#         return {
#             "success": True,
#             "created": created_count,
#             "skipped": skipped_count,
#             "errors": error_count,
#             "error_details": errors
#         }

#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to sync enrollments: {str(e)}"
#         )


@router.get("/sync-enrollments-from-clients")
def sync_client_enrollments(
    client_service: ClientService = Depends(get_client_service),
    period_service: ServicePeriodService = Depends(get_period_service),
    contract_service: ServiceContractService = Depends(get_contract_service),
    service_service: ServiceService = Depends(get_service_service),
    fourgeeks_client: FourGeeksClient = Depends(get_fourgeeks_client)
) -> dict:
    """
    Synchronize all enrollments associated with client's 4Geeks users.

    Returns:
        dict: Statistics about the synchronization process including counts of
              created, updated, skipped, and failed operations.
    """
    processor = EnrollmentProcessor(period_service, client_service, service_service, contract_service)
    academy_ids = os.getenv("4GEEKS_ACADEMY_ID", "6").split(",")
    academy_ids = [int(a.strip()) for a in academy_ids if a.strip()]


    try:
        contracts = contract_service.get_active_contracts()

        for contract in contracts:
            #  Get the client enrollments from 4Geeks
            try:
                fourgeeks_external_id = contract.client.get_external_id(
                    system="fourgeeks")
                if not fourgeeks_external_id:
                    processor.stats["skipped"] += 1
                    processor.stats["error_details"].append(
                        f"No fourgeeks external ID found for client {contract.client.id}"
                    )
                    continue

                enrollments = []
                for academy_id in academy_ids:
                    enrollments = fourgeeks_client.get_user_enrollments(
                        user_id=fourgeeks_external_id,
                        params={"roles": "STUDENT"},
                        academy_id=academy_id
                    )
                    if len(enrollments) > 0:
                        break

                for enrollment in enrollments:
                    processor.process_enrollment(enrollment, contract.id)

            except Exception as e:
                processor.stats["errors"] += 1
                processor.stats["error_details"].append(
                    log_contract_error(e, contract.id)
                )

        return {
            "success": True,
            **processor.stats
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
) -> dict:
    """
    Syncs clients in the local database with 4Geeks students by email.
    Adds the 4Geeks user ID as an external ID to matching clients
    who don't already have one.

    Returns:
        dict: Statistics about the synchronization process including counts
              of linked clients, clients not found, and errors.
    """
    processor = StudentProcessor(client_service, fourgeeks_client)
    academy_ids = os.getenv("4GEEKS_ACADEMY_ID", "6").split(",")
    academy_ids = [int(a.strip()) for a in academy_ids if a.strip()]

    try:
        clients_to_sync = client_service.get_clients_with_no_external_id(
            "fourgeeks")
        logger.info(
            f"Found {len(clients_to_sync)} clients without a 4Geeks external ID.")

        # Track which clients still need to be found after each academy_id
        clients_remaining = [(client.id, client.identifier.lower()) for client in clients_to_sync]
        not_found_details = []
        error_details = []
        linked = 0
        errors = 0
        not_found = 0

        for academy_id in academy_ids:
            next_clients_remaining = []
            for client_id, client_identifier in clients_remaining:
                linked_id, error_msg = processor.find_and_link_student(
                    client_id, client_identifier, academy_id=academy_id
                )
                if linked_id:
                    linked += 1
                elif error_msg == "not_found":
                    next_clients_remaining.append((client_id, client_identifier))
                else:
                    errors += 1
                    if error_msg:
                        error_details.append(log_student_error(error_msg))
                    next_clients_remaining.append((client_id, client_identifier))
            clients_remaining = next_clients_remaining
            # Only retry not found/errors in the next academy_id
            if not clients_remaining:
                break

        if len(clients_remaining) > 0:
            not_found += len(clients_remaining)
            not_found_details = [client_identifier for client_id, client_identifier in clients_remaining]

        logger.info(
            f"Sync completed. Linked: {linked}, Not Found: {not_found}, Errors: {errors}")

        response = {
            "success": True,
            "linked": linked,
            "not_found": not_found,
            "not_found_details": not_found_details,
            "errors": errors,
            "error_details": error_details
        }
        return response

    except Exception as e:
        logger.exception("Critical error during sync_students_from_clients")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync clients with 4Geeks students: {str(e)}"
        )
