"""
User Model - Authentication and user management
"""

from sqlalchemy import Column, String, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from database import Base


class UserRole(str, enum.Enum):
    """User role enumeration"""
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String)

    # Role and status
    role = Column(SQLEnum(UserRole), default=UserRole.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)

    # Metadata
    department = Column(String)
    phone = Column(String)

    # Relationships
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role"""
        return self.role == UserRole.ADMIN

    @property
    def is_analyst(self) -> bool:
        """Check if user has analyst role"""
        return self.role == UserRole.ANALYST

    @property
    def is_viewer(self) -> bool:
        """Check if user has viewer role"""
        return self.role == UserRole.VIEWER

    def can_upload_documents(self) -> bool:
        """Check if user can upload documents"""
        return self.role in [UserRole.ADMIN, UserRole.ANALYST]

    def can_delete_documents(self) -> bool:
        """Check if user can delete documents"""
        return self.role == UserRole.ADMIN

    def can_manage_users(self) -> bool:
        """Check if user can manage other users"""
        return self.role == UserRole.ADMIN
