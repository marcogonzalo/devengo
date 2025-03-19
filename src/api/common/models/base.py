import os
from datetime import datetime
from sqlmodel import Field, SQLModel, DateTime
from sqlalchemy.ext.declarative import declared_attr
from src.api.common.utils.datetime import get_current_datetime


class TimestampMixin:
    """Mixin to add created_at and updated_at fields to models"""
    created_at: datetime = Field(
        default_factory=get_current_datetime,
        sa_type=DateTime(timezone=True), nullable=False)
    updated_at: datetime = Field(
        default_factory=get_current_datetime,
        sa_type=DateTime(timezone=True), nullable=False)


class BaseModel(SQLModel):
    """Base model for all models in the application"""
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
