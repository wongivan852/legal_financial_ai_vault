#!/usr/bin/env python3
"""
Create Admin User Script
Creates the first admin user for the system
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

from database import SessionLocal
from models.user import User, UserRole
from security.auth import get_password_hash
import uuid


def create_admin_user(email: str, password: str, full_name: str = "Admin User"):
    """Create admin user"""

    db = SessionLocal()

    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()

        if existing_user:
            print(f"User with email {email} already exists!")
            return False

        # Create admin user
        admin_user = User(
            id=str(uuid.uuid4()),
            email=email,
            password_hash=get_password_hash(password),
            full_name=full_name,
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True
        )

        db.add(admin_user)
        db.commit()

        print(f"Admin user created successfully!")
        print(f"Email: {email}")
        print(f"Role: {admin_user.role.value}")
        return True

    except Exception as e:
        print(f"Error creating admin user: {e}")
        db.rollback()
        return False

    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python create_admin.py <email> <password> [full_name]")
        sys.exit(1)

    email = sys.argv[1]
    password = sys.argv[2]
    full_name = sys.argv[3] if len(sys.argv) > 3 else "Admin User"

    success = create_admin_user(email, password, full_name)
    sys.exit(0 if success else 1)
