"""
Admin Router - User management, system health, audit logs
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from database import get_db
from models.user import User, UserRole
from models.audit_log import AuditLog
from schemas.user_schema import UserCreate, UserUpdate, UserResponse
from security.auth import get_current_user, get_password_hash
from security.rbac import require_admin
from services.audit import AuditService
from services.inference import InferenceService

router = APIRouter()


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    page: int = 1,
    page_size: int = 50,
    role: Optional[UserRole] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """List all users (Admin only)"""
    query = db.query(User)

    if role:
        query = query.filter(User.role == role)

    offset = (page - 1) * page_size
    users = query.order_by(User.created_at.desc()).offset(offset).limit(page_size).all()

    return [UserResponse.from_orm(user) for user in users]


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create a new user (Admin only)"""

    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )

    # Create user
    new_user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        department=user_data.department,
        phone=user_data.phone,
        role=user_data.role,
        is_active=True
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Log action
    AuditService.log_action(
        db=db,
        user=current_user,
        action_type="user_create",
        resource_type="user",
        resource_id=new_user.id,
        metadata={"email": new_user.email, "role": new_user.role.value}
    )

    return UserResponse.from_orm(new_user)


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get user by ID (Admin only)"""
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse.from_orm(user)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update user (Admin only)"""
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update fields
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    if user_data.department is not None:
        user.department = user_data.department
    if user_data.phone is not None:
        user.phone = user_data.phone
    if user_data.role is not None:
        user.role = user_data.role
    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    user.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(user)

    # Log action
    AuditService.log_action(
        db=db,
        user=current_user,
        action_type="user_update",
        resource_type="user",
        resource_id=user_id
    )

    return UserResponse.from_orm(user)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete user (Admin only)"""

    # Can't delete yourself
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Log before deletion
    AuditService.log_action(
        db=db,
        user=current_user,
        action_type="user_delete",
        resource_type="user",
        resource_id=user_id,
        metadata={"email": user.email}
    )

    db.delete(user)
    db.commit()

    return {"message": "User deleted successfully"}


@router.get("/audit-logs")
async def get_audit_logs(
    page: int = 1,
    page_size: int = 100,
    action_type: Optional[str] = None,
    user_id: Optional[str] = None,
    days: int = 7,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get audit logs (Admin only)

    Returns paginated audit logs with optional filters
    """
    query = db.query(AuditLog)

    # Filter by date
    since = datetime.utcnow() - timedelta(days=days)
    query = query.filter(AuditLog.timestamp >= since)

    # Filter by action type
    if action_type:
        query = query.filter(AuditLog.action_type == action_type)

    # Filter by user
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)

    # Get total count
    total = query.count()

    # Paginate
    offset = (page - 1) * page_size
    logs = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(page_size).all()

    return {
        "logs": [
            {
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "user_email": log.user_email,
                "user_role": log.user_role,
                "action_type": log.action_type,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "agent_type": log.agent_type,
                "tokens_used": log.tokens_used,
                "status": log.status,
                "client_ip": log.client_ip
            }
            for log in logs
        ],
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/system-health")
async def get_system_health(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get system health status (Admin only)

    Returns health of all services and GPU utilization
    """
    # Check GPU services
    inference_service = InferenceService()
    gpu_health = await inference_service.health_check()

    # Get database stats
    user_count = db.query(User).count()
    from models.document import Document
    document_count = db.query(Document).count()
    from models.analysis import Analysis
    analysis_count = db.query(Analysis).count()
    recent_logs = db.query(AuditLog).filter(
        AuditLog.timestamp >= datetime.utcnow() - timedelta(hours=24)
    ).count()

    # Get inference stats (last 24 hours)
    recent_inferences = db.query(AuditLog).filter(
        AuditLog.action_type == "inference",
        AuditLog.timestamp >= datetime.utcnow() - timedelta(hours=24)
    ).all()

    total_tokens = sum(log.tokens_used or 0 for log in recent_inferences)
    avg_latency = sum(log.inference_latency or 0 for log in recent_inferences) / len(recent_inferences) if recent_inferences else 0

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "gpu_services": gpu_health,
        "database": {
            "users": user_count,
            "documents": document_count,
            "analyses": analysis_count,
            "audit_logs_24h": recent_logs
        },
        "inference_stats_24h": {
            "total_requests": len(recent_inferences),
            "total_tokens": total_tokens,
            "avg_latency_seconds": round(avg_latency, 2)
        }
    }


@router.get("/statistics")
async def get_statistics(
    days: int = 30,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get usage statistics (Admin only)

    Returns usage metrics for the specified time period
    """
    since = datetime.utcnow() - timedelta(days=days)

    # Document statistics
    from models.document import Document
    docs_uploaded = db.query(Document).filter(
        Document.uploaded_at >= since
    ).count()

    # Analysis statistics by agent type
    from models.analysis import Analysis
    analyses = db.query(Analysis).filter(
        Analysis.created_at >= since
    ).all()

    agent_stats = {}
    for analysis in analyses:
        agent_type = analysis.agent_type
        if agent_type not in agent_stats:
            agent_stats[agent_type] = {"count": 0, "total_tokens": 0}
        agent_stats[agent_type]["count"] += 1
        agent_stats[agent_type]["total_tokens"] += analysis.tokens_used or 0

    # User activity
    active_users = db.query(AuditLog.user_id).filter(
        AuditLog.timestamp >= since
    ).distinct().count()

    return {
        "period_days": days,
        "documents_uploaded": docs_uploaded,
        "analyses_by_agent": agent_stats,
        "active_users": active_users,
        "total_analyses": len(analyses)
    }


@router.post("/cleanup-audit-logs")
async def cleanup_old_audit_logs(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Clean up expired audit logs (Admin only)

    Deletes logs that have passed their retention period
    """
    deleted_count = AuditService.cleanup_expired_logs(db)

    return {
        "message": f"Cleaned up {deleted_count} expired audit logs"
    }
