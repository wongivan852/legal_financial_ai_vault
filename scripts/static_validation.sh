#!/bin/bash
# Static Validation Script - Checks code without running it

set -e

echo "============================================================"
echo "Legal AI Vault - Static Validation"
echo "============================================================"
echo ""

SUCCESS=0
WARNING=0
ERROR=0

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

success() {
    echo -e "${GREEN}✓${NC} $1"
    ((SUCCESS++))
}

warning() {
    echo -e "${YELLOW}!${NC} $1"
    ((WARNING++))
}

error() {
    echo -e "${RED}✗${NC} $1"
    ((ERROR++))
}

cd /home/user/legal_financial_ai_vault

echo "1. Checking Python Syntax..."
echo "----------------------------"

# Check all Python files for syntax errors
find api -name "*.py" -type f | while read file; do
    if python3 -m py_compile "$file" 2>/dev/null; then
        success "Syntax OK: $file"
    else
        error "Syntax ERROR: $file"
    fi
done

echo ""
echo "2. Checking File Structure..."
echo "----------------------------"

# Check critical files exist
FILES=(
    "api/main.py"
    "api/config.py"
    "api/database.py"
    "api/models/user.py"
    "api/models/document.py"
    "api/models/audit_log.py"
    "api/models/analysis.py"
    "api/security/auth.py"
    "api/security/rbac.py"
    "api/security/encryption.py"
    "api/services/audit.py"
    "api/services/document_processor.py"
    "api/services/embedding.py"
    "api/services/inference.py"
    "api/services/vector_store.py"
    "api/agents/base_agent.py"
    "api/agents/contract_review.py"
    "api/agents/compliance.py"
    "api/agents/document_router.py"
    "api/agents/legal_research.py"
    "api/routers/auth.py"
    "api/routers/documents.py"
    "api/routers/agents.py"
    "api/routers/admin.py"
    "api/schemas/user_schema.py"
    "api/schemas/document_schema.py"
    "api/schemas/agent_schema.py"
    "api/embedding_server.py"
    "docker-compose.yml"
    ".env.example"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        success "File exists: $file"
    else
        error "Missing file: $file"
    fi
done

echo ""
echo "3. Checking Import Statements..."
echo "--------------------------------"

# Check for common import issues
if grep -r "from \. import" api/ --include="*.py" > /dev/null 2>&1; then
    success "Relative imports found (OK for packages)"
fi

if grep -r "import \*" api/ --include="*.py" > /dev/null 2>&1; then
    warning "Wildcard imports found (consider being more specific)"
fi

echo ""
echo "4. Checking Docker Configuration..."
echo "-----------------------------------"

# Check Docker Compose file
if [ -f "docker-compose.yml" ]; then
    success "docker-compose.yml exists"

    # Check for required services
    SERVICES=("postgres" "qdrant" "redis" "vllm-contract" "vllm-compliance" "vllm-router" "embedding-service" "api" "prometheus" "grafana")

    for service in "${SERVICES[@]}"; do
        if grep -q "  $service:" docker-compose.yml; then
            success "Service defined: $service"
        else
            error "Missing service: $service"
        fi
    done

    # Check for GPU configuration
    if grep -q "runtime: nvidia" docker-compose.yml; then
        success "NVIDIA runtime configured"
    else
        warning "NVIDIA runtime not found"
    fi

    # Check for health checks
    if grep -q "healthcheck:" docker-compose.yml; then
        success "Health checks configured"
    else
        warning "No health checks found"
    fi
else
    error "docker-compose.yml not found"
fi

echo ""
echo "5. Checking Requirements..."
echo "--------------------------"

if [ -f "api/requirements.txt" ]; then
    success "requirements.txt exists"

    # Check for critical dependencies
    DEPS=("fastapi" "sqlalchemy" "pydantic" "uvicorn" "qdrant-client" "aiohttp")

    for dep in "${DEPS[@]}"; do
        if grep -q "^$dep" api/requirements.txt; then
            success "Dependency listed: $dep"
        else
            warning "Dependency may be missing: $dep"
        fi
    done
else
    error "requirements.txt not found"
fi

echo ""
echo "6. Checking Configuration..."
echo "---------------------------"

if [ -f ".env.example" ]; then
    success ".env.example exists"

    # Check for required environment variables
    ENV_VARS=("JWT_SECRET" "DATABASE_URL" "VLLM_CONTRACT_URL" "ENCRYPTION_KEY")

    for var in "${ENV_VARS[@]}"; do
        if grep -q "^$var=" .env.example; then
            success "Environment variable defined: $var"
        else
            error "Missing environment variable: $var"
        fi
    done
else
    error ".env.example not found"
fi

echo ""
echo "7. Checking Nginx Configuration..."
echo "----------------------------------"

if [ -f "nginx/nginx.conf" ]; then
    success "nginx.conf exists"
else
    error "nginx.conf not found"
fi

if [ -f "nginx/conf.d/api.conf" ]; then
    success "API configuration exists"

    if grep -q "ssl_certificate" nginx/conf.d/api.conf; then
        success "SSL configured"
    else
        warning "SSL not configured"
    fi
else
    error "API configuration not found"
fi

echo ""
echo "8. Checking Scripts..."
echo "----------------------"

SCRIPTS=("backup.sh" "health_check.sh" "create_admin.py" "validate_app.py")

for script in "${SCRIPTS[@]}"; do
    if [ -f "scripts/$script" ]; then
        success "Script exists: $script"

        if [ -x "scripts/$script" ]; then
            success "Script is executable: $script"
        else
            warning "Script not executable: $script"
        fi
    else
        error "Missing script: $script"
    fi
done

echo ""
echo "9. Checking Documentation..."
echo "----------------------------"

DOCS=("README.md" "DEVELOPMENT_PLAN.md" "QUICK_START.md" "IMPLEMENTATION_STATUS.md" "docs/DEPLOYMENT.md")

for doc in "${DOCS[@]}"; do
    if [ -f "$doc" ]; then
        success "Documentation exists: $doc"
    else
        warning "Missing documentation: $doc"
    fi
done

echo ""
echo "10. Checking Database Models..."
echo "-------------------------------"

# Check for proper model definitions
if grep -q "class User(Base):" api/models/user.py; then
    success "User model defined"
fi

if grep -q "class Document(Base):" api/models/document.py; then
    success "Document model defined"
fi

if grep -q "class AuditLog(Base):" api/models/audit_log.py; then
    success "AuditLog model defined"
fi

if grep -q "class Analysis(Base):" api/models/analysis.py; then
    success "Analysis model defined"
fi

echo ""
echo "11. Checking API Routers..."
echo "--------------------------"

# Check router definitions
if grep -q "router = APIRouter()" api/routers/auth.py; then
    success "Auth router defined"
fi

if grep -q "router = APIRouter()" api/routers/documents.py; then
    success "Documents router defined"
fi

if grep -q "router = APIRouter()" api/routers/agents.py; then
    success "Agents router defined"
fi

if grep -q "router = APIRouter()" api/routers/admin.py; then
    success "Admin router defined"
fi

echo ""
echo "12. Checking AI Agents..."
echo "------------------------"

AGENTS=("contract_review" "compliance" "document_router" "legal_research")

for agent in "${AGENTS[@]}"; do
    if grep -q "class.*Agent" api/agents/${agent}.py; then
        success "Agent defined: $agent"
    else
        error "Agent not properly defined: $agent"
    fi
done

echo ""
echo "============================================================"
echo "VALIDATION SUMMARY"
echo "============================================================"
echo -e "${GREEN}Successes: $SUCCESS${NC}"
echo -e "${YELLOW}Warnings:  $WARNING${NC}"
echo -e "${RED}Errors:    $ERROR${NC}"
echo ""

if [ $ERROR -eq 0 ]; then
    if [ $WARNING -eq 0 ]; then
        echo -e "${GREEN}✅ VALIDATION PASSED - Application is ready!${NC}"
        exit 0
    else
        echo -e "${YELLOW}⚠️  VALIDATION PASSED with warnings${NC}"
        echo "Review warnings before deployment"
        exit 0
    fi
else
    echo -e "${RED}❌ VALIDATION FAILED${NC}"
    echo "Please fix errors before deployment"
    exit 1
fi
