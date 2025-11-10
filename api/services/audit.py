"""
Audit Service - Comprehensive logging for compliance
Logs all user actions, AI inferences, and system events
"""

import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from models.audit_log import AuditLog
from models.user import User
from security.encryption import hash_string
from database import SessionLocal

logger = logging.getLogger(__name__)


class AuditService:
    """Service for creating and managing audit logs"""

    @staticmethod
    def initialize():
        """Initialize audit service (create log directories, etc.)"""
        logger.info("Audit service initialized")

    @staticmethod
    def log_action(
        db: Session,
        user: User,
        action_type: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error_message: Optional[str] = None
    ) -> AuditLog:
        """
        Log a general user action

        Args:
            db: Database session
            user: User performing the action
            action_type: Type of action (e.g., "login", "document_upload")
            resource_type: Type of resource affected (e.g., "document", "user")
            resource_id: ID of the resource
            client_ip: Client IP address
            metadata: Additional metadata as dictionary
            status: Action status ("success", "error", "warning")
            error_message: Error message if action failed

        Returns:
            Created AuditLog entry
        """
        audit_log = AuditLog(
            user_id=user.id,
            user_email=user.email,
            user_role=user.role.value,
            client_ip=client_ip,
            action_type=action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=json.dumps(metadata) if metadata else None,
            status=status,
            error_message=error_message
        )

        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)

        logger.info(
            f"Audit log created: user={user.email}, action={action_type}, "
            f"resource={resource_type}:{resource_id}, status={status}"
        )

        return audit_log

    @staticmethod
    def log_inference(
        db: Session,
        user: User,
        agent_type: str,
        prompt: str,
        response: str,
        tokens_used: int,
        latency: float,
        client_ip: Optional[str] = None,
        document_id: Optional[str] = None,
        status: str = "success",
        error_message: Optional[str] = None
    ) -> AuditLog:
        """
        Log an AI inference action

        Args:
            db: Database session
            user: User who triggered inference
            agent_type: Type of AI agent used
            prompt: User's prompt (will be hashed for privacy)
            response: AI response (will be hashed for privacy)
            tokens_used: Number of tokens consumed
            latency: Inference latency in seconds
            client_ip: Client IP address
            document_id: Related document ID if applicable
            status: Inference status
            error_message: Error message if inference failed

        Returns:
            Created AuditLog entry
        """
        # Hash prompt and response for privacy while maintaining audit trail
        prompt_hash = hash_string(prompt)
        response_hash = hash_string(response)

        metadata = {
            "document_id": document_id,
            "prompt_length": len(prompt),
            "response_length": len(response)
        }

        audit_log = AuditLog(
            user_id=user.id,
            user_email=user.email,
            user_role=user.role.value,
            client_ip=client_ip,
            action_type="inference",
            resource_type="agent",
            resource_id=agent_type,
            agent_type=agent_type,
            prompt_hash=prompt_hash,
            response_hash=response_hash,
            tokens_used=tokens_used,
            inference_latency=latency,
            metadata=json.dumps(metadata),
            status=status,
            error_message=error_message
        )

        db.add(audit_log)
        db.commit()
        db.refresh(audit_log)

        logger.info(
            f"Inference audit log created: user={user.email}, agent={agent_type}, "
            f"tokens={tokens_used}, latency={latency:.2f}s, status={status}"
        )

        return audit_log

    @staticmethod
    def log_document_action(
        db: Session,
        user: User,
        action_type: str,
        document_id: str,
        client_ip: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error_message: Optional[str] = None
    ) -> AuditLog:
        """
        Log a document-related action

        Args:
            db: Database session
            user: User performing action
            action_type: Type of action ("upload", "download", "delete", "process")
            document_id: ID of the document
            client_ip: Client IP address
            metadata: Additional metadata
            status: Action status
            error_message: Error message if action failed

        Returns:
            Created AuditLog entry
        """
        return AuditService.log_action(
            db=db,
            user=user,
            action_type=f"document_{action_type}",
            resource_type="document",
            resource_id=document_id,
            client_ip=client_ip,
            metadata=metadata,
            status=status,
            error_message=error_message
        )

    @staticmethod
    def log_authentication(
        db: Session,
        email: str,
        success: bool,
        client_ip: Optional[str] = None,
        error_message: Optional[str] = None
    ):
        """
        Log authentication attempt

        Args:
            db: Database session
            email: Email of user attempting to log in
            success: Whether authentication was successful
            client_ip: Client IP address
            error_message: Error message if authentication failed
        """
        # Create a temporary "user" object for logging
        # If authentication failed, user may not exist
        audit_log = AuditLog(
            user_id="system",
            user_email=email,
            user_role="unknown",
            client_ip=client_ip,
            action_type="login_attempt" if not success else "login",
            status="success" if success else "error",
            error_message=error_message
        )

        db.add(audit_log)
        db.commit()

        logger.info(
            f"Authentication attempt logged: email={email}, "
            f"success={success}, ip={client_ip}"
        )

    @staticmethod
    def get_user_audit_logs(
        db: Session,
        user_id: str,
        limit: int = 100,
        offset: int = 0
    ):
        """
        Get audit logs for a specific user

        Args:
            db: Database session
            user_id: User ID
            limit: Maximum number of logs to return
            offset: Number of logs to skip

        Returns:
            List of AuditLog entries
        """
        return (
            db.query(AuditLog)
            .filter(AuditLog.user_id == user_id)
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    @staticmethod
    def get_inference_logs(
        db: Session,
        limit: int = 100,
        offset: int = 0
    ):
        """
        Get all inference audit logs

        Args:
            db: Database session
            limit: Maximum number of logs to return
            offset: Number of logs to skip

        Returns:
            List of AuditLog entries for inference actions
        """
        return (
            db.query(AuditLog)
            .filter(AuditLog.action_type == "inference")
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    @staticmethod
    def cleanup_expired_logs(db: Session) -> int:
        """
        Delete audit logs that have passed their retention period

        Args:
            db: Database session

        Returns:
            Number of logs deleted
        """
        deleted_count = (
            db.query(AuditLog)
            .filter(AuditLog.retention_until < datetime.utcnow())
            .delete()
        )

        db.commit()

        logger.info(f"Cleaned up {deleted_count} expired audit logs")
        return deleted_count
