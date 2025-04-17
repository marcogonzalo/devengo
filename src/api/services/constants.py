from enum import Enum

class ServiceStatus(str, Enum):
    ACTIVE = "active"
    POSTPONED = "postponed"
    DROPPED = "dropped"
    ENDED = "ended"

class ServiceContractStatus(str, Enum):
    ACTIVE = "active"
    CANCELED = "canceled"
