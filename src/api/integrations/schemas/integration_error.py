from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class IntegrationErrorBase(BaseModel):
    """Base schema for integration errors"""
    integration_name: str = Field(..., description="Name of the integration")
    operation_type: str = Field(..., description="Type of operation that failed")
    external_id: str = Field(..., description="External ID from the integration system")
    entity_type: str = Field(..., description="Type of entity")
    error_message: str = Field(..., description="Human-readable error message")
    error_details: Optional[Dict[str, Any]] = Field(default={}, description="Additional error details")
    client_id: Optional[int] = Field(default=None, description="Related client ID")
    contract_id: Optional[int] = Field(default=None, description="Related contract ID")


class IntegrationErrorCreate(IntegrationErrorBase):
    """Schema for creating a new integration error"""
    pass


class IntegrationErrorUpdate(BaseModel):
    """Schema for updating an integration error"""
    is_resolved: Optional[bool] = Field(default=None, description="Whether the error has been resolved")
    is_ignored: Optional[bool] = Field(default=None, description="Whether the error has been ignored")
    resolution_notes: Optional[str] = Field(default=None, description="Notes about how the error was resolved")
    ignore_notes: Optional[str] = Field(default=None, description="Notes about why the error was ignored")


class IntegrationErrorRead(IntegrationErrorBase):
    """Schema for reading integration error data"""
    id: int
    is_resolved: bool
    is_ignored: bool
    resolved_at: Optional[str] = None
    resolution_notes: Optional[str] = None
    ignored_at: Optional[str] = None
    ignore_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class IntegrationErrorFilter(BaseModel):
    """Schema for filtering integration errors"""
    integration_name: Optional[str] = Field(default=None, description="Filter by integration name")
    operation_type: Optional[str] = Field(default=None, description="Filter by operation type")
    entity_type: Optional[str] = Field(default=None, description="Filter by entity type")
    is_resolved: Optional[bool] = Field(default=None, description="Filter by resolution status")
    is_ignored: Optional[bool] = Field(default=None, description="Filter by ignored status")
    client_id: Optional[int] = Field(default=None, description="Filter by client ID")
    contract_id: Optional[int] = Field(default=None, description="Filter by contract ID")
    limit: Optional[int] = Field(default=100, description="Maximum number of results")
    offset: Optional[int] = Field(default=0, description="Number of results to skip")


class IntegrationErrorSummary(BaseModel):
    """Schema for integration error summary statistics"""
    total_errors: int
    resolved_errors: int
    unresolved_errors: int
    ignored_errors: int
    errors_by_integration: Dict[str, int]
    errors_by_operation: Dict[str, int]
    errors_by_entity_type: Dict[str, int]


class BulkResolveRequest(BaseModel):
    """Schema for bulk resolve request"""
    error_ids: List[int] = Field(..., description="List of error IDs to resolve")
    resolution_notes: Optional[str] = Field(default=None, description="Notes about how the errors were resolved")


class BulkIgnoreRequest(BaseModel):
    """Schema for bulk ignore request"""
    error_ids: List[int] = Field(..., description="List of error IDs to ignore")
    ignore_notes: Optional[str] = Field(default=None, description="Notes about why the errors were ignored")
