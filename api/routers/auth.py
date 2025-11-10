"""
Authentication Router - Login, logout, user info endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from database import get_db
from models.user import User
from schemas.user_schema import UserLogin, Token, UserResponse
from security.auth import authenticate_user, create_access_token, get_current_user
from services.audit import AuditService

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    credentials: UserLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    User login endpoint

    Returns JWT access token on successful authentication
    """
    # Authenticate user
    user = authenticate_user(db, credentials.email, credentials.password)

    if not user:
        # Log failed attempt
        AuditService.log_authentication(
            db=db,
            email=credentials.email,
            success=False,
            client_ip=request.client.host,
            error_message="Invalid credentials"
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Create access token
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "role": user.role.value}
    )

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()

    # Log successful login
    AuditService.log_authentication(
        db=db,
        email=user.email,
        success=True,
        client_ip=request.client.host
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.from_orm(user)
    )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    User logout endpoint

    Note: Since JWT is stateless, this mainly logs the action
    Client should discard the token
    """
    AuditService.log_action(
        db=db,
        user=current_user,
        action_type="logout",
        status="success"
    )

    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current authenticated user information"""
    return UserResponse.from_orm(current_user)


@router.post("/refresh")
async def refresh_token(
    current_user: User = Depends(get_current_user)
):
    """
    Refresh access token

    Returns a new JWT token with extended expiration
    """
    # Create new access token
    access_token = create_access_token(
        data={"sub": current_user.id, "email": current_user.email, "role": current_user.role.value}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
