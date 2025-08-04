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

# Time-based constants for accrual processing
class AccrualTimeConstants:
    """Constants for time-based accrual processing rules."""
    
    # Contract recency threshold (days)
    CONTRACT_RECENCY_DAYS = 15
    
    # Postponed service period time limits (months)
    POSTPONED_PERIOD_MAX_MONTHS = 3
    
    # Contract without service periods time limits (months)
    CONTRACT_WITHOUT_PERIODS_MAX_MONTHS = 3
