from typing import Optional
from pydantic import BaseModel, field_validator
from datetime import datetime


class ClientBase(BaseModel):
    """Base schema for client data"""
    name: Optional[str] = None

    class Config:
        from_attributes = True


class ClientCreate(ClientBase):
    """Schema for creating a new client"""
    identifier: str  # This will be encrypted in the model

    @field_validator('identifier')
    def validate_identifier(cls, v):
        """Validate that identifier is not empty"""
        if not v:
            raise ValueError("Identifier cannot be empty")
        return v


class ClientRead(ClientBase):
    """Schema for reading client data"""
    id: int
    identifier: str  # This will be decrypted from the model
    created_at: datetime
    updated_at: datetime


class ClientUpdate(ClientBase):
    """Schema for updating client data"""
    identifier: Optional[str] = None


class ClientExternalIdBase(BaseModel):
    """Base schema for client external ID data"""
    system: str

    class Config:
        from_attributes = True


class ClientExternalIdCreate(ClientExternalIdBase):
    """Schema for creating a new client external ID"""
    external_id: str  # This will be encrypted in the model

    @field_validator('external_id')
    def validate_external_id(cls, v):
        """Validate that external ID is not empty"""
        if not v:
            raise ValueError("External ID cannot be empty")
        return v


class ClientExternalIdRead(ClientExternalIdBase):
    """Schema for reading client external ID data"""
    id: int
    client_id: int
    external_id: str  # This will be decrypted from the model
    created_at: datetime
    updated_at: datetime

