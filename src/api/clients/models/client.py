from typing import Optional, List
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel, Relationship
from pydantic import validator
from src.api.common.models.base import BaseModel, TimestampMixin
from src.api.common.utils.encryption import encrypt_data, decrypt_data


class Client(BaseModel, TimestampMixin, table=True):
    """
    Client model with encrypted personal information
    """
    id: Optional[int] = Field(default=None, primary_key=True)

    # Encrypted identifier (usually email)
    encrypted_identifier: str = Field(index=True)

    # Additional information (can be extended as needed)
    name: Optional[str] = None

    # Relationships
    external_ids: List["ClientExternalId"] = Relationship(
        back_populates="client")

    # Properties to access encrypted data
    @property
    def identifier(self) -> str:
        """Get decrypted identifier"""
        return decrypt_data(self.encrypted_identifier)

    @identifier.setter
    def identifier(self, value: str):
        """Set encrypted identifier"""
        self.encrypted_identifier = encrypt_data(value)

    class Config:
        from_attributes = True


class ClientExternalId(BaseModel, table=True):
    """
    Model to store encrypted external IDs for clients from different systems
    """
    id: Optional[int] = Field(default=None, primary_key=True)

    # Foreign key to client
    client_id: int = Field(foreign_key="client.id")
    client: Client = Relationship(back_populates="external_ids")

    # System identifier (e.g., "holded", "fourgeeks")
    system: str = Field(index=True)

    # Encrypted external ID
    encrypted_external_id: str

    # Properties to access encrypted data
    @property
    def external_id(self) -> str:
        """Get decrypted external ID"""
        return decrypt_data(self.encrypted_external_id)

    @external_id.setter
    def external_id(self, value: str):
        """Set encrypted external ID"""
        self.encrypted_external_id = encrypt_data(value)

    class Config:
        from_attributes = True
