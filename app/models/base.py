"""
Base model with common fields and utilities.

All database models should inherit from this base class.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr

from app.core.database import Base


class BaseModel(Base):
    """
    Base model class with common fields.

    Attributes:
        id: Primary key (UUID)
        created_at: Creation timestamp
        updated_at: Last update timestamp
        tenant_id: Tenant ID for multi-tenancy (nullable)
    """

    __abstract__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    tenant_id = Column(String(100), index=True, nullable=True)

    @declared_attr
    def __tablename__(cls) -> str:
        """Generate __tablename__ automatically from class name."""
        return cls.__name__.lower()

    def to_dict(self) -> dict[str, Any]:
        """
        Convert model instance to dictionary.

        Returns:
            dict: Model data as dictionary
        """
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }

    def __repr__(self) -> str:
        """String representation of model."""
        return f"<{self.__class__.__name__}(id={self.id})>"
