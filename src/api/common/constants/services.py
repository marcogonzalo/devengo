from enum import Enum

class ServiceStatus(str, Enum):
    ACTIVE = "ACTIVE"
    POSTPONED = "POSTPONED"
    DROPPED = "DROPPED"
    ENDED = "ENDED"

class ServiceContractStatus(str, Enum):
    ACTIVE = "ACTIVE"
    CANCELED = "CANCELED"
