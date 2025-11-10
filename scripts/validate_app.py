#!/usr/bin/env python3
"""
Application Validation Script
Checks for import errors, configuration issues, and logical problems
"""

import sys
import os
from pathlib import Path

# Add API directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

print("=" * 60)
print("Legal AI Vault - Application Validation")
print("=" * 60)
print()

errors = []
warnings = []
successes = []

# Test 1: Check Python version
print("✓ Checking Python version...")
if sys.version_info < (3, 11):
    warnings.append(f"Python {sys.version_info.major}.{sys.version_info.minor} detected. Python 3.11+ recommended.")
else:
    successes.append(f"Python {sys.version_info.major}.{sys.version_info.minor} - OK")

# Test 2: Check required files exist
print("✓ Checking required files...")
required_files = [
    'api/main.py',
    'api/config.py',
    'api/database.py',
    'api/requirements.txt',
    'docker-compose.yml',
    '.env.example'
]

for file in required_files:
    if Path(f"/home/user/legal_financial_ai_vault/{file}").exists():
        successes.append(f"File exists: {file}")
    else:
        errors.append(f"Missing required file: {file}")

# Test 3: Check imports
print("✓ Checking imports...")

try:
    import config
    successes.append("config.py imports OK")
except Exception as e:
    errors.append(f"config.py import failed: {e}")

try:
    import database
    successes.append("database.py imports OK")
except Exception as e:
    errors.append(f"database.py import failed: {e}")

try:
    from models import User, Document, AuditLog, Analysis
    successes.append("All models import OK")
except Exception as e:
    errors.append(f"Models import failed: {e}")

try:
    from security import auth, rbac, encryption
    successes.append("Security modules import OK")
except Exception as e:
    errors.append(f"Security import failed: {e}")

try:
    from services import audit, document_processor, embedding, inference, vector_store
    successes.append("All services import OK")
except Exception as e:
    errors.append(f"Services import failed: {e}")

try:
    from agents import base_agent, contract_review, compliance, document_router, legal_research
    successes.append("All agents import OK")
except Exception as e:
    errors.append(f"Agents import failed: {e}")

try:
    from routers import auth, documents, agents, admin
    successes.append("All routers import OK")
except Exception as e:
    errors.append(f"Routers import failed: {e}")

# Test 4: Check schemas
print("✓ Checking Pydantic schemas...")
try:
    from schemas import user_schema, document_schema, agent_schema
    successes.append("All schemas import OK")
except Exception as e:
    errors.append(f"Schemas import failed: {e}")

# Test 5: Check main.py
print("✓ Checking main application...")
try:
    from main import app
    successes.append("FastAPI app initializes OK")

    # Check routes are registered
    routes = [route.path for route in app.routes]

    required_routes = [
        '/api/auth/login',
        '/api/documents/upload',
        '/api/agents/contract-review',
        '/api/admin/users',
        '/health'
    ]

    for route in required_routes:
        if any(r.startswith(route) for r in routes):
            successes.append(f"Route registered: {route}")
        else:
            warnings.append(f"Route may not be registered: {route}")

except Exception as e:
    errors.append(f"Main app initialization failed: {e}")

# Test 6: Check environment configuration
print("✓ Checking environment configuration...")
try:
    from config import settings

    # Check critical settings
    if hasattr(settings, 'JWT_SECRET'):
        if settings.JWT_SECRET == "your-secret-key-here-change-in-production-use-openssl-rand-hex-32":
            warnings.append("JWT_SECRET not changed from default!")
        else:
            successes.append("JWT_SECRET is configured")

    if hasattr(settings, 'DATABASE_URL'):
        successes.append("DATABASE_URL is configured")

    if hasattr(settings, 'VLLM_CONTRACT_URL'):
        successes.append("vLLM endpoints configured")

except Exception as e:
    errors.append(f"Configuration check failed: {e}")

# Test 7: Check Docker Compose
print("✓ Checking Docker Compose configuration...")
docker_compose = Path("/home/user/legal_financial_ai_vault/docker-compose.yml")
if docker_compose.exists():
    content = docker_compose.read_text()

    required_services = [
        'postgres',
        'qdrant',
        'redis',
        'vllm-contract',
        'vllm-compliance',
        'vllm-router',
        'embedding-service',
        'api',
        'prometheus',
        'grafana'
    ]

    for service in required_services:
        if f"{service}:" in content:
            successes.append(f"Docker service defined: {service}")
        else:
            errors.append(f"Missing Docker service: {service}")
else:
    errors.append("docker-compose.yml not found")

# Test 8: Check database models
print("✓ Checking database models...")
try:
    from models.user import User, UserRole
    from models.document import Document
    from models.audit_log import AuditLog
    from models.analysis import Analysis

    # Check User model
    if hasattr(User, 'email') and hasattr(User, 'password_hash') and hasattr(User, 'role'):
        successes.append("User model structure OK")
    else:
        errors.append("User model missing required fields")

    # Check Document model
    if hasattr(Document, 'filename') and hasattr(Document, 'storage_path') and hasattr(Document, 'uploaded_by'):
        successes.append("Document model structure OK")
    else:
        errors.append("Document model missing required fields")

except Exception as e:
    errors.append(f"Model structure check failed: {e}")

# Test 9: Check agent implementations
print("✓ Checking AI agent implementations...")
try:
    from agents.contract_review import ContractReviewAgent
    from agents.compliance import ComplianceAgent
    from agents.document_router import DocumentRouterAgent
    from agents.legal_research import LegalResearchAgent

    # Check agent properties
    agent = ContractReviewAgent()
    if hasattr(agent, 'agent_type') and hasattr(agent, 'system_prompt'):
        successes.append("Contract Review Agent structure OK")
    else:
        errors.append("Contract Review Agent missing required properties")

except Exception as e:
    errors.append(f"Agent implementation check failed: {e}")

# Print results
print()
print("=" * 60)
print("VALIDATION RESULTS")
print("=" * 60)
print()

if successes:
    print(f"✅ SUCCESSES ({len(successes)}):")
    for success in successes:
        print(f"   ✓ {success}")
    print()

if warnings:
    print(f"⚠️  WARNINGS ({len(warnings)}):")
    for warning in warnings:
        print(f"   ! {warning}")
    print()

if errors:
    print(f"❌ ERRORS ({len(errors)}):")
    for error in errors:
        print(f"   ✗ {error}")
    print()

# Summary
print("=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"Successes: {len(successes)}")
print(f"Warnings:  {len(warnings)}")
print(f"Errors:    {len(errors)}")
print()

if errors:
    print("❌ Validation FAILED - Please fix errors before deployment")
    sys.exit(1)
elif warnings:
    print("⚠️  Validation PASSED with warnings - Review warnings before deployment")
    sys.exit(0)
else:
    print("✅ Validation PASSED - Application is ready!")
    sys.exit(0)
