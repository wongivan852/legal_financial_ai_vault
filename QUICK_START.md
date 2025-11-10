# Legal/Financial AI Vault - Quick Start Guide

This guide helps you get started quickly with the development plan.

---

## Prerequisites Checklist

Before you begin, ensure you have:

- ✅ Ubuntu 22.04 LTS Server with 6x NVIDIA GPUs
- ✅ Minimum 128GB RAM (256GB recommended)
- ✅ 4TB SSD storage
- ✅ Root or sudo access
- ✅ Internet connection for downloads

---

## Day 1: Initial Setup (4-6 hours)

### 1. Install NVIDIA Drivers & Docker

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install NVIDIA drivers
sudo apt install -y nvidia-driver-525 nvidia-utils-525

# Reboot to load drivers
sudo reboot

# After reboot, verify GPUs
nvidia-smi

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install -y docker-compose-plugin

# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo systemctl restart docker

# Test GPU access in Docker
docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi
```

### 2. Create Directory Structure

```bash
# Create main directory
sudo mkdir -p /opt/legal-ai-vault
cd /opt/legal-ai-vault

# Create subdirectories
sudo mkdir -p api/{models,routers,services,agents,security,schemas}
sudo mkdir -p frontend/src/{components,pages,services,hooks}
sudo mkdir -p nginx/{ssl,conf.d}
sudo mkdir -p dify/config
sudo mkdir -p vllm
sudo mkdir -p scripts
sudo mkdir -p monitoring/{grafana/dashboards,alerts}
sudo mkdir -p docs

# Create data directories
sudo mkdir -p /data/{models,documents,vectors,backups}
sudo chmod 700 /data
sudo chown -R $USER:$USER /opt/legal-ai-vault /data
```

### 3. Download AI Models

```bash
# Install Git LFS for large file downloads
sudo apt install -y git-lfs
git lfs install

# Download Qwen models (This will take 1-2 hours)
cd /data/models

# Option 1: Using Hugging Face CLI
pip install huggingface-hub
huggingface-cli download Qwen/Qwen2.5-14B-Instruct --local-dir qwen2.5-14b-instruct
huggingface-cli download Qwen/Qwen2.5-7B-Instruct --local-dir qwen2.5-7b-instruct

# Option 2: Using git (if HF CLI not available)
git clone https://huggingface.co/Qwen/Qwen2.5-14B-Instruct qwen2.5-14b-instruct
git clone https://huggingface.co/Qwen/Qwen2.5-7B-Instruct qwen2.5-7b-instruct

# Download embedding model
git clone https://huggingface.co/BAAI/bge-large-en-v1.5 bge-large-en-v1.5

# Verify downloads
ls -lh /data/models/
```

---

## Day 2-3: Database & Core Setup (8-12 hours)

### 4. Set Up PostgreSQL with Docker

```bash
cd /opt/legal-ai-vault

# Create docker-compose-dev.yml for development
cat > docker-compose-dev.yml << 'EOF'
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: legal-ai-postgres-dev
    environment:
      POSTGRES_DB: legal_ai_vault
      POSTGRES_USER: legalai
      POSTGRES_PASSWORD: changeme_dev_password
    volumes:
      - postgres_dev_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped

  qdrant:
    image: qdrant/qdrant:v1.8.0
    container_name: legal-ai-qdrant-dev
    volumes:
      - qdrant_dev_data:/qdrant/storage
    ports:
      - "6333:6333"
    restart: unless-stopped

volumes:
  postgres_dev_data:
  qdrant_dev_data:
EOF

# Start database services
docker compose -f docker-compose-dev.yml up -d

# Verify they're running
docker ps
```

### 5. Initialize Python Backend

```bash
cd /opt/legal-ai-vault/api

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Create requirements.txt
cat > requirements.txt << 'EOF'
fastapi==0.110.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
alembic==1.13.1
pydantic==2.6.0
pydantic-settings==2.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9
aiohttp==3.9.3
asyncpg==0.29.0
psycopg2-binary==2.9.9
qdrant-client==1.7.3
PyPDF2==3.0.1
python-docx==1.1.0
pdfplumber==0.10.3
sentence-transformers==2.3.1
cryptography==42.0.2
python-json-logger==2.0.7
prometheus-fastapi-instrumentator==7.0.0
slowapi==0.1.9
pytest==8.0.0
pytest-asyncio==0.23.4
EOF

# Install dependencies
pip install -r requirements.txt

# Create basic directory structure
mkdir -p models routers services agents security schemas
touch models/__init__.py routers/__init__.py services/__init__.py
touch agents/__init__.py security/__init__.py schemas/__init__.py
```

### 6. Create Environment Configuration

```bash
cd /opt/legal-ai-vault

# Create .env.development
cat > .env.development << 'EOF'
# Application
APP_NAME=Legal AI Vault
VERSION=1.0.0
DEBUG=true

# Security
JWT_SECRET=your-secret-key-here-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
ENCRYPTION_KEY=your-encryption-key-here-32-bytes

# Database
DATABASE_URL=postgresql://legalai:changeme_dev_password@localhost:5432/legal_ai_vault

# Vector Database
QDRANT_HOST=localhost
QDRANT_PORT=6333

# vLLM Endpoints (will be configured later)
VLLM_CONTRACT_URL=http://localhost:8001/v1
VLLM_COMPLIANCE_URL=http://localhost:8002/v1
VLLM_ROUTER_URL=http://localhost:8003/v1
EMBEDDING_URL=http://localhost:8004

# File Storage
DOCUMENT_STORAGE_PATH=/data/documents
MAX_UPLOAD_SIZE_MB=100

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000

# Audit Logging
AUDIT_LOG_PATH=/var/log/legal-ai/audit.log
AUDIT_LOG_RETENTION_DAYS=2555

# Inference Settings
DEFAULT_MAX_TOKENS=4096
DEFAULT_TEMPERATURE=0.3
INFERENCE_TIMEOUT_SECONDS=120
EOF

# Generate secure secrets (for production)
echo "JWT_SECRET=$(openssl rand -hex 32)" >> .env.production
echo "ENCRYPTION_KEY=$(openssl rand -hex 32)" >> .env.production
```

---

## Development Workflow

### Starting Development

```bash
# Terminal 1: Start databases
cd /opt/legal-ai-vault
docker compose -f docker-compose-dev.yml up

# Terminal 2: Start FastAPI backend (once developed)
cd /opt/legal-ai-vault/api
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 3: Start React frontend (once developed)
cd /opt/legal-ai-vault/frontend
npm start
```

### Running Tests

```bash
cd /opt/legal-ai-vault/api
source venv/bin/activate
pytest tests/ -v --cov=.
```

### Checking Logs

```bash
# API logs
tail -f /var/log/legal-ai/api.log

# Audit logs
tail -f /var/log/legal-ai/audit.log

# Docker logs
docker logs -f legal-ai-postgres-dev
docker logs -f legal-ai-qdrant-dev
```

---

## Next Steps

Follow the **DEVELOPMENT_PLAN.md** phases in order:

1. ✅ **Phase 1** - You're here! Environment setup complete
2. 📝 **Phase 2** - Database models (Start with `api/models/user.py`)
3. 🔐 **Phase 3** - Authentication (Start with `api/security/auth.py`)
4. 📄 **Phase 4** - Document processing
5. 🚀 **Phase 5** - vLLM services
6. 🤖 **Phase 6** - AI agents
7. ... and so on

---

## Useful Commands

### Docker Management
```bash
# Stop all services
docker compose down

# Remove all data (CAUTION!)
docker compose down -v

# View logs
docker compose logs -f [service_name]

# Restart a service
docker compose restart [service_name]
```

### Database Management
```bash
# Connect to PostgreSQL
docker exec -it legal-ai-postgres-dev psql -U legalai -d legal_ai_vault

# Backup database
docker exec legal-ai-postgres-dev pg_dump -U legalai legal_ai_vault > backup.sql

# Restore database
cat backup.sql | docker exec -i legal-ai-postgres-dev psql -U legalai -d legal_ai_vault
```

### GPU Monitoring
```bash
# Watch GPU usage in real-time
watch -n 1 nvidia-smi

# Detailed GPU info
nvidia-smi -q
```

---

## Troubleshooting

### GPUs not visible in Docker
```bash
# Restart Docker with NVIDIA runtime
sudo systemctl restart docker

# Check NVIDIA container runtime
docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi
```

### Port already in use
```bash
# Find what's using the port
sudo lsof -i :8000

# Kill the process
sudo kill -9 <PID>
```

### Out of disk space
```bash
# Check disk usage
df -h

# Clean Docker system
docker system prune -a

# Clean old logs
sudo journalctl --vacuum-time=7d
```

### Can't connect to database
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Check PostgreSQL logs
docker logs legal-ai-postgres-dev

# Verify connection
psql postgresql://legalai:changeme_dev_password@localhost:5432/legal_ai_vault
```

---

## Resources

- **FastAPI Documentation:** https://fastapi.tiangolo.com/
- **vLLM Documentation:** https://docs.vllm.ai/
- **Qdrant Documentation:** https://qdrant.tech/documentation/
- **React Documentation:** https://react.dev/
- **Qwen Model:** https://huggingface.co/Qwen

---

## Getting Help

If you encounter issues:

1. Check the **TROUBLESHOOTING.md** guide (create during Phase 12)
2. Review logs in `/var/log/legal-ai/`
3. Check Docker logs: `docker compose logs`
4. Verify GPU status: `nvidia-smi`
5. Search GitHub issues for similar problems

---

**Ready to start? Follow Phase 2 of DEVELOPMENT_PLAN.md!**
