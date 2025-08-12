from datetime import date, timedelta
from typing import Optional
from fastapi.logger import logger
from src.api.clients.schemas.client import ClientExternalIdCreate
from src.api.integrations.fourgeeks.client import FourGeeksClient
from src.api.integrations.fourgeeks.log_error import log_enrollment_error
from src.api.integrations.utils.error_logger import log_integration_error
from src.api.common.constants.services import ServicePeriodStatus, map_educational_status
from src.api.clients.services.client_service import ClientService
from src.api.services.services.service_period_service import ServicePeriodService
from src.api.services.services.service_service import ServiceService
from src.api.services.services.service_contract import ServiceContractService
from src.api.services.schemas.service_period import ServicePeriodCreate
from src.api.services.utils import (
    get_service_type_from_service_name, 
    validate_service_period_compatibility
)
from src.api.common.utils.datetime import get_date


def _adjust_start_date_to_service(start_date_str: str | None, cohort_slug: str) -> Optional[date]:
    if start_date_str is None:
        return None
    start_date = get_date(start_date_str)
    if cohort_slug[0:8] in ["spain-fs", "spain-ds"]:
        # The start date is 2 weeks before the cohort start date becaus of the prework
        start_date = start_date - timedelta(weeks=2)
    return start_date


class EnrollmentProcessor:
    def __init__(self, period_service: ServicePeriodService, client_service: ClientService, service_service: ServiceService, contract_service: ServiceContractService):
        self.period_service = period_service
        self.client_service = client_service
        self.service_service = service_service
        self.contract_service = contract_service
        self.stats = {
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0,
            "compatibility_errors": 0,
            "error_details": []
        }

    def process_enrollment(self, enrollment: dict, contract_id: int):
        try:
            cohort = enrollment.get("cohort", {})

            if not self._validate_enrollment(cohort):
                return

            cohort_slug = cohort.get("slug")
            
            # Validate cohort-service compatibility
            if not self._validate_service_period_compatibility(cohort_slug, contract_id):
                return

            start_date = cohort.get("kickoff_date")
            end_date = cohort.get("ending_date")

            educational_status = map_educational_status(
                enrollment.get("educational_status"))

            fallback_date = start_date if educational_status == ServicePeriodStatus.ACTIVE else None
            status_change_date = get_date(enrollment.get("updated_at", fallback_date))

            self._process_period(
                contract_id=contract_id,
                cohort_slug=cohort_slug,
                start_date=start_date,
                end_date=end_date,
                status=educational_status,
                status_change_date=status_change_date
            )

        except Exception as e:
            self.stats["errors"] += 1
            error_msg = log_enrollment_error(e, cohort_slug, contract_id)
            self.stats["error_details"].append(error_msg)
            
            # Log to integration errors table
            try:
                log_integration_error(
                    integration_name="fourgeeks",
                    operation_type="enrollment",
                    external_id=cohort_slug,
                    entity_type="cohort",
                    error_message=str(e),
                    error_details={"contract_id": contract_id, "enrollment_data": enrollment},
                    contract_id=contract_id,
                    db=self.client_service.db
                )
            except Exception as log_error:
                logger.error(f"Failed to log integration error: {log_error}")
            
            self.client_service.db.rollback()

    def _validate_enrollment(self, cohort: dict) -> bool:
        cohort_slug = cohort.get("slug")
        cohort_ending_date = cohort.get("ending_date")
        if cohort_slug and cohort_ending_date and cohort_slug != "yomequedoencasa":
            return True

        self.stats["skipped"] += 1
        return False

    def _validate_service_period_compatibility(self, cohort_slug: str, contract_id: int) -> bool:
        """
        Validate that the cohort program type matches the service contract program type
        """
        try:
            # Get the service contract and its service
            contract = self.contract_service.get_contract(contract_id)
            if not contract:
                self.stats["error_details"].append(
                    f"Contract {contract_id} not found for cohort {cohort_slug}"
                )
                self.stats["compatibility_errors"] += 1
                return False

            service = self.service_service.get_service(contract.service_id)
            if not service:
                self.stats["error_details"].append(
                    f"Service {contract.service_id} not found for contract {contract_id}"
                )
                self.stats["compatibility_errors"] += 1
                return False

            # Get program types
            cohort_service_type = get_service_type_from_service_name(cohort_slug)
            service_service_type = service.computed_service_type

            # Validate compatibility
            if not validate_service_period_compatibility(cohort_slug, service_service_type):
                error_msg = (
                    f"Cohort-Service compatibility error: "
                    f"Cohort '{cohort_slug}' (program: {cohort_service_type}) "
                    f"incompatible with service '{service.name}' (program: {service_service_type}) "
                    f"for contract {contract_id}"
                )
                self.stats["error_details"].append(error_msg)
                self.stats["compatibility_errors"] += 1
                logger.warning(error_msg)
                return False

            logger.info(
                f"Cohort-Service compatibility validated: "
                f"Cohort '{cohort_slug}' ({cohort_service_type}) "
                f"compatible with service '{service.name}' ({service_service_type})"
            )
            return True

        except Exception as e:
            error_msg = f"Error validating cohort-service compatibility: {str(e)}"
            self.stats["error_details"].append(error_msg)
            self.stats["compatibility_errors"] += 1
            logger.error(error_msg)
            return False

    def _process_period(
        self,
        contract_id: int,
        cohort_slug: str,
        start_date: str,
        status_change_date: date | None,
        end_date: str,
        status: ServicePeriodStatus
    ):
        existing_period = self.period_service.get_period_by_external_id(
            contract_id, cohort_slug
        )

        if existing_period:
            self.period_service.update_period_status(
                existing_period.id,
                status,
                status_change_date
            )
            self.stats["updated"] += 1
        else:
            period_data = ServicePeriodCreate(
                contract_id=contract_id,
                name=cohort_slug,
                external_id=cohort_slug,
                start_date=_adjust_start_date_to_service(
                    start_date, cohort_slug),
                end_date=get_date(end_date),
                status=status,
                status_change_date=status_change_date
            )
            self.period_service.create_period(period_data)
            self.stats["created"] += 1


class StudentProcessor:
    def __init__(self, client_service: ClientService, fourgeeks_client: FourGeeksClient):
        self.client_service = client_service
        self.fourgeeks_client = fourgeeks_client
        self.stats = {
            "linked": 0,
            "not_found": 0,
            "errors": 0,
            "error_details": [],
            "not_found_details": []
        }

    def _find_matching_student(self, students_response: list | dict, target_email: str) -> Optional[dict]:
        """
        Finds the best matching student from the 4Geeks API response.
        Handles both list and single object responses.
        Prioritizes exact email match if a list is returned.
        """
        if isinstance(students_response, list):
            exact_match = None
            for s in students_response:
                # Defensive check for email existence and type
                student_email = s.get("email")
                if isinstance(student_email, str) and student_email.lower() == target_email:
                    exact_match = s
                    break  # Found exact match, stop searching

            # If no exact match, but list is not empty, return the first one as a fallback?
            # Decide if this fallback is desired or if only exact matches should proceed.
            # For now, returning the first one if no exact match is found.
            if not exact_match and students_response:
                logger.warning(
                    f"No exact email match in list, using first result.")
                return students_response[0]
            return exact_match  # Returns exact match or None if list was empty or no matches
        elif isinstance(students_response, dict):
            # Single student object returned
            return students_response
        else:
            # Unexpected response type
            logger.error(
                f"Unexpected response type from get_student_by_email: {type(students_response)}")
            return None

    def find_and_link_student(self,
                              client_id: int,
                              client_identifier: str,
                              academy_id: int = 6
                              ) -> tuple[Optional[str], Optional[str]]:
        """
        Finds a student in 4Geeks by client's email and links their external ID.

        Args:
            client: The local client object.
            client_service: Service for client operations.
            fourgeeks_client: Client for interacting with 4Geeks API.
            academy_id: The academy ID to use for the search.

        Returns:
            A tuple containing:
            - The linked student's 4Geeks ID (str) if successful, None otherwise.
            - An error message (str) if an error occurred, None otherwise.
        """
        try:
            students_response = self.fourgeeks_client.get_member_by_email(
                email=client_identifier,
                roles=["student", "assistant"],
                academy_id=academy_id
            )

            if not students_response:
                logger.warning(
                    f"No 4Geeks student found for client {client_id}")
                return None, "not_found"

            student = self._find_matching_student(
                students_response, client_identifier)

            if not student:
                logger.warning(
                    f"Could not determine a unique 4Geeks student client {client_id} identifier")
                return None, "not_found"

            # TODO: Consider status INVITED as another case
            try:
                student_user_id = student.get("user", {}).get("id")
            except Exception as e:
                raise Exception(
                    f"4Geeks student data has not user attribute")

            if not student_user_id:
                logger.error(
                    f"4Geeks student data missing user ID for client {client_id} - Data: {student}")
                return None, "missing_user_id"

            external_id_data = ClientExternalIdCreate(
                system="fourgeeks",
                external_id=str(student_user_id)
            )
            self.client_service.add_external_id(client_id, external_id_data)
            return str(student_user_id), None

        except Exception as e:
            error_msg = f"FourGeeksClient error on Client {client_id}: {str(e)}"
            logger.error(error_msg)
            # Consider if specific exceptions need different handling
            # E.g., API connection errors vs. data validation errors
            return None, error_msg
