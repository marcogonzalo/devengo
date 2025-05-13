from enum import Enum
from sqlalchemy.dialects.postgresql import ENUM

# Python enums for type hints and constants

class ContractAccrualStatus(str, Enum):
    ACTIVE = "ACTIVE"
    CANCELED = "CANCELED"
    COMPLETED = "COMPLETED"
    PAUSED = "PAUSED"

contract_accrual_status_enum = ENUM(
    *[x.value for x in ContractAccrualStatus],
    name='contractaccrualstatus',
    create_type=False  # Important: let migrations handle type creation
)
