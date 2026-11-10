from enum import Enum
from typing import Optional
from sqlalchemy.dialects.postgresql import ENUM

# Python enums for type hints and constants


class ServicePeriodStatus(str, Enum):
    ACTIVE = "ACTIVE"
    POSTPONED = "POSTPONED"
    DROPPED = "DROPPED"
    ENDED = "ENDED"


class ServiceContractStatus(str, Enum):
    ACTIVE = "ACTIVE"
    CANCELED = "CANCELED"
    CLOSED = "CLOSED"


# Holded accountNums that use internal 12-month generic service periods
# instead of CRM enrollment sync (e.g. AI Flex).
INTERNAL_SERVICE_PERIOD_ACCOUNT_NUMBERS = {"70501003"}
INTERNAL_SERVICE_PERIOD_MONTHS = 12


def uses_internal_service_periods(account_identifier: Optional[str]) -> bool:
    """Return True when the Holded accountNum opts into internal service periods."""
    if account_identifier is None:
        return False
    return str(account_identifier) in INTERNAL_SERVICE_PERIOD_ACCOUNT_NUMBERS


# SQLAlchemy enum types for database
service_period_status_enum = ENUM(
    *[x.value for x in ServicePeriodStatus],
    name='serviceperiodstatus',
    create_type=False  # Important: let migrations handle type creation
)

service_contract_status_enum = ENUM(
    *[x.value for x in ServiceContractStatus],
    name='servicecontractstatus',
    create_type=False  # Important: let migrations handle type creation
)


def map_educational_status(status) -> ServicePeriodStatus:
    status_mapping = {
        "ACTIVE": ServicePeriodStatus.ACTIVE,
        "DROPPED": ServicePeriodStatus.DROPPED,
        "EARLY_DROPPED": ServicePeriodStatus.DROPPED,
        "EARLY_POSTPONED": ServicePeriodStatus.POSTPONED,
        "GRADUATED": ServicePeriodStatus.ENDED,
        "NOT_COMPLETING": ServicePeriodStatus.ENDED,
        "POSTPONED": ServicePeriodStatus.POSTPONED,
        "SUSPENDED": ServicePeriodStatus.DROPPED,
    }
    if not isinstance(status, str) or not status:
        return ServicePeriodStatus.ACTIVE
    return status_mapping.get(status, ServicePeriodStatus.ACTIVE)
