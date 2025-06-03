from enum import Enum
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


def map_educational_status(status: str) -> ServicePeriodStatus:
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
    return status_mapping.get(status, ServicePeriodStatus.ACTIVE)
