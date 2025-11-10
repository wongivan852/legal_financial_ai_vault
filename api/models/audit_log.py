"""
Audit Log Model - Comprehensive logging for compliance
"""

from sqlalchemy import Column, String, DateTime, Integer, Text, Float
from datetime import datetime, timedelta
import uuid

from database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # User information
    user_id = Column(String, nullable=False, index=True)
    user_email = Column(String)
    user_role = Column(String)
    client_ip = Column(String)

    # Action details
    action_type = Column(String, nullable=False, index=True)  # "inference", "document_upload", "login", etc.
    resource_type = Column(String)  # "document", "agent", "user", etc.
    resource_id = Column(String)

    # AI-specific fields
    agent_type = Column(String)  # "contract_review", "compliance", etc.
    prompt_hash = Column(String)  # SHA-256 hash of user prompt
    response_hash = Column(String)  # SHA-256 hash of AI response
    tokens_used = Column(Integer)
    inference_latency = Column(Float)  # Seconds

    # Additional context
    metadata = Column(Text)  # JSON string for extra data
    status = Column(String)  # "success", "error", "warning"
    error_message = Column(Text)

    # Retention (for automated cleanup)
    retention_until = Column(DateTime)  # Auto-calculated: timestamp + 7 years

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Auto-calculate retention date (7 years for legal compliance)
        if not self.retention_until:
            self.retention_until = self.timestamp + timedelta(days=2555)

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action_type}, user={self.user_id}, timestamp={self.timestamp})>"

    @property
    def is_expired(self) -> bool:
        """Check if log has passed retention period"""
        return datetime.utcnow() > self.retention_until

    @property
    def is_inference_action(self) -> bool:
        """Check if this is an AI inference action"""
        return self.action_type == "inference"

    @property
    def is_successful(self) -> bool:
        """Check if action was successful"""
        return self.status == "success"
