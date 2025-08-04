from typing import TYPE_CHECKING, Optional, List
from sqlmodel import Field, Relationship
from src.api.common.models.base import BaseModel, TimestampMixin


if TYPE_CHECKING:
    from src.api.services.models.service_contract import ServiceContract

class Service(BaseModel, TimestampMixin, table=True):
    """
    Service model to store educational services (course programs)
    """
    id: int = Field(default=None, primary_key=True)

    # External service ID (from 4Geeks)
    external_id: Optional[str] = Field(default=None, index=True)

    # Service details
    account_identifier: Optional[str] = Field(default=None, index=True)
    name: str
    description: Optional[str] = None
    
    # Program type based on course category
    service_type: Optional[str] = Field(default=None, index=True, description="Program type: FS (Full-Stack), DS (Data Science), CS (Cybersecurity)")

    # Class schedule information
    total_sessions: int = 60
    sessions_per_week: int = 3

    # Relationships
    contracts: List["ServiceContract"] = Relationship(back_populates="service")
    
    @property
    def computed_service_type(self) -> str:
        """
        Get the program type, using stored value or computing from name
        """
        if self.service_type:
            return self.service_type
        
        # Import here to avoid circular imports
        from src.api.services.utils import get_service_type_from_service_name
        return get_service_type_from_service_name(self.name)

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True
