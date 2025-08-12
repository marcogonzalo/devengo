from typing import Optional, Dict, Any
from sqlmodel import Field, Relationship, Column, JSON
from src.api.common.models.base import BaseModel, TimestampMixin
from src.api.clients.models.client import Client
from src.api.services.models.service_contract import ServiceContract


class IntegrationError(BaseModel, TimestampMixin, table=True):
    """
    Model to track failed imports from integrations
    """
    id: Optional[int] = Field(default=None, primary_key=True)

    # Integration details
    integration_name: str = Field(index=True, description="Name of the integration (e.g., 'fourgeeks', 'holded', 'notion')")
    operation_type: str = Field(index=True, description="Type of operation that failed (e.g., 'enrollment', 'invoice', 'client')")
    
    # Entity identification for uniqueness
    external_id: str = Field(index=True, description="External ID from the integration system")
    entity_type: str = Field(description="Type of entity (e.g., 'cohort', 'invoice', 'client')")
    
    # Error details
    error_message: str = Field(description="Human-readable error message")
    error_details: Dict[str, Any] = Field(default={}, sa_column=Column(JSON), description="Additional error details as JSON")
    
    # Related entities (optional)
    client_id: Optional[int] = Field(default=None, foreign_key="client.id")
    contract_id: Optional[int] = Field(default=None, foreign_key="servicecontract.id")
    
    # Relationships
    client: Optional[Client] = Relationship()
    contract: Optional[ServiceContract] = Relationship()
    
    # Status tracking
    is_resolved: bool = Field(default=False, index=True, description="Whether the error has been resolved")
    is_ignored: bool = Field(default=False, index=True, description="Whether the error has been ignored")
    resolved_at: Optional[str] = Field(default=None, description="When the error was resolved")
    resolution_notes: Optional[str] = Field(default=None, description="Notes about how the error was resolved")
    ignored_at: Optional[str] = Field(default=None, description="When the error was ignored")
    ignore_notes: Optional[str] = Field(default=None, description="Notes about why the error was ignored")
    
    class Config:
        from_attributes = True
        arbitrary_types_allowed = True
