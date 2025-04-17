# Import schema classes directly
from src.api.services.schemas.service import (
    ServiceBase, ServiceCreate, ServiceRead, ServiceUpdate
)
from src.api.services.schemas.service_contract import (
    ServiceContractBase, ServiceContractCreate, ServiceContractRead, ServiceContractUpdate
)
from src.api.services.schemas.service_period import (
    ServicePeriodBase, ServicePeriodCreate, ServicePeriodRead, ServicePeriodUpdate
)

# Export all schema classes
__all__ = [
    "ServiceBase", "ServiceCreate", "ServiceRead", "ServiceUpdate",
    "ServiceContractBase", "ServiceContractCreate", "ServiceContractRead", "ServiceContractUpdate",
    "ServicePeriodBase", "ServicePeriodCreate", "ServicePeriodRead", "ServicePeriodUpdate"
] 