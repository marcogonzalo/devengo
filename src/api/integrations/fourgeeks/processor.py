from datetime import date, timedelta
from typing import Optional
from fastapi.logger import logger
from src.api.clients.schemas.client import ClientExternalIdCreate
from src.api.integrations.fourgeeks.client import FourGeeksClient
from src.api.integrations.fourgeeks.log_error import log_enrollment_error
from api.common.constants.services import ServicePeriodStatus
from src.api.clients.services.client_service import ClientService
from src.api.services.services.service_period_service import ServicePeriodService
from src.api.services.schemas.service_period import ServicePeriodCreate
from src.api.common.utils.datetime import get_date


def map_educational_status(status: str) -> ServicePeriodStatus:
    status_mapping = {
        "ACTIVE": ServicePeriodStatus.ACTIVE,
        "DROPPED": ServicePeriodStatus.DROPPED,
        "GRADUATED": ServicePeriodStatus.ENDED,
        "NOT_COMPLETING": ServicePeriodStatus.ENDED,
        "POSTPONED": ServicePeriodStatus.POSTPONED,
    }
    return status_mapping.get(status, ServicePeriodStatus.ACTIVE)


def _adjust_start_date_to_service(start_date_str: str | None, cohort_slug: str) -> Optional[date]:
    if start_date_str is None:
        return None
    start_date = get_date(start_date_str)
    if cohort_slug[0:8] in ["spain-fs", "spain-ds"]:
        # The start date is 2 weeks before the cohort start date becaus of the prework
        start_date = start_date - timedelta(weeks=2)
    return start_date


class EnrollmentProcessor:
    def __init__(self, period_service: ServicePeriodService, client_service: ClientService):
        self.period_service = period_service
        self.client_service = client_service
        self.stats = {
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0,
            "error_details": []
        }

    def process_enrollment(self, enrollment: dict, contract_id: int):
        try:
            cohort = enrollment.get("cohort", {})
            cohort_slug = cohort.get("slug")

            if not self._validate_enrollment(cohort, cohort_slug):
                return

            start_date = cohort.get("kickoff_date")
            end_date = cohort.get("ending_date")
            educational_status = map_educational_status(
                enrollment.get("educational_status", "ACTIVE"))

            status_change_date = get_date(enrollment.get(
                "updated_at")) if educational_status == ServicePeriodStatus.POSTPONED or educational_status == ServicePeriodStatus.DROPPED else None

            if not end_date:
                self.stats["skipped"] += 1
                return

            status = map_educational_status(educational_status)

            self._process_period(
                contract_id=contract_id,
                cohort_slug=cohort_slug,
                start_date=start_date,
                end_date=end_date,
                status=status,
                status_change_date=status_change_date
            )

        except Exception as e:
            self.stats["errors"] += 1
            self.stats["error_details"].append(
                log_enrollment_error(e, cohort_slug, contract_id)
            )
            self.client_service.db.rollback()

    def _validate_enrollment(self, cohort: dict, cohort_slug: str) -> bool:
        if not cohort_slug:
            self.stats["skipped"] += 1
            self.stats["error_details"].append(
                f"Found cohort without slug {cohort.get('id')}"
            )
            return False
        return True

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
                              client_identifier: str
                              ) -> tuple[Optional[str], Optional[str]]:
        """
        Finds a student in 4Geeks by client's email and links their external ID.

        Args:
            client: The local client object.
            client_service: Service for client operations.
            fourgeeks_client: Client for interacting with 4Geeks API.

        Returns:
            A tuple containing:
            - The linked student's 4Geeks ID (str) if successful, None otherwise.
            - An error message (str) if an error occurred, None otherwise.
        """
        try:
            students_response = self.fourgeeks_client.get_student_by_email(
                email=client_identifier)

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

            student_user_id = student.get("user", {}).get("id")
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
            error_msg = f"Error processing client {client_id}: {str(e)}"
            logger.error(error_msg)
            # Consider if specific exceptions need different handling
            # E.g., API connection errors vs. data validation errors
            return None, error_msg
