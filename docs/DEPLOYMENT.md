# Legal/Financial AI Vault - Deployment Guide

Complete guide for deploying the Legal AI Vault on a 6-GPU server.

---

## Prerequisites

### Hardware Requirements
- **Server:** 6x NVIDIA GPUs (A100, A6000, or RTX 4090)
- **RAM:** 128GB minimum (256GB recommended)
- **Storage:** 4TB NVMe SSD
- **Network:** 10Gbps network card
- **OS:** Ubuntu 22.04 LTS Server

### Software Requirements
- Docker 24.x
- Docker Compose v2
- NVIDIA Driver 525.x or later
- NVIDIA Container Toolkit
- Git

---

## Step 1: System Preparation

### 1.1 Update System
```bash
sudo apt update && sudo apt upgrade -y
sudo reboot
```

### 1.2 Install NVIDIA Drivers
```bash
# Install drivers
sudo apt install -y nvidia-driver-525 nvidia-utils-525

# Verify installation
nvidia-smi

# Should show all 6 GPUs
```

### 1.3 Install Docker
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install -y docker-compose-plugin

# Verify installation
docker --version
docker compose version
```

### 1.4 Install NVIDIA Container Toolkit
```bash
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt update
sudo apt install -y nvidia-container-toolkit

# Configure Docker
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Test GPU access
docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi
```

---

## Step 2: Download AI Models

### 2.1 Create Model Directory
```bash
sudo mkdir -p /data/models
sudo chown -R $USER:$USER /data
```

### 2.2 Install Hugging Face CLI
```bash
pip install huggingface-hub
```

### 2.3 Download Models
```bash
cd /data/models

# Download Qwen2.5-14B-Instruct (~28GB)
huggingface-cli download Qwen/Qwen2.5-14B-Instruct --local-dir qwen2.5-14b-instruct

# Download Qwen2.5-7B-Instruct (~14GB)
huggingface-cli download Qwen/Qwen2.5-7B-Instruct --local-dir qwen2.5-7b-instruct

# Download BGE-Large-EN-v1.5 (~1.3GB)
huggingface-cli download BAAI/bge-large-en-v1.5 --local-dir bge-large-en-v1.5

# Verify downloads
ls -lh /data/models/
```

**Note:** This will take 1-3 hours depending on internet speed. Total size: ~43GB

---

## Step 3: Clone Repository

```bash
cd /opt
sudo git clone https://github.com/wongivan852/legal_financial_ai_vault.git
sudo chown -R $USER:$USER legal_financial_ai_vault
cd legal_financial_ai_vault
```

---

## Step 4: Configuration

### 4.1 Create Environment File
```bash
cp .env.example .env.production

# Generate secure secrets
JWT_SECRET=$(openssl rand -hex 32)
ENCRYPTION_KEY=$(openssl rand -hex 32)
GRAFANA_PASSWORD=$(openssl rand -base64 16)
REDIS_PASSWORD=$(openssl rand -base64 16)

# Edit .env.production with generated secrets
nano .env.production
```

### 4.2 Required Environment Variables
```bash
# Application
APP_NAME=Legal AI Vault
VERSION=1.0.0
DEBUG=false
ENVIRONMENT=production

# Security (USE GENERATED VALUES!)
JWT_SECRET=<generated-jwt-secret>
ENCRYPTION_KEY=<generated-encryption-key>

# Database
DB_USER=legalai
DB_PASSWORD=<choose-secure-password>
DB_NAME=legal_ai_vault

# Redis
REDIS_PASSWORD=<generated-redis-password>

# Grafana
GRAFANA_PASSWORD=<generated-grafana-password>

# vLLM & Embedding endpoints (leave as-is)
VLLM_CONTRACT_URL=http://vllm-contract:8001/v1
VLLM_COMPLIANCE_URL=http://vllm-compliance:8002/v1
VLLM_ROUTER_URL=http://vllm-router:8003/v1
EMBEDDING_URL=http://embedding-service:8004
```

### 4.3 Create Data Directories
```bash
sudo mkdir -p /data/{documents,vectors,backups}
sudo mkdir -p /var/log/legal-ai
sudo chown -R $USER:$USER /data /var/log/legal-ai
```

### 4.4 SSL Certificate (Self-Signed for Testing)
```bash
cd nginx/ssl

# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout server.key \
  -out server.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=legal-ai.client.internal"

# For production, use proper CA-signed certificate
```

---

## Step 5: Build and Deploy

### 5.1 Build Docker Images
```bash
cd /opt/legal_financial_ai_vault

# Build API image
docker compose build api

# Build embedding service
docker compose build embedding-service
```

### 5.2 Start Services
```bash
# Start databases first
docker compose up -d postgres qdrant redis

# Wait for databases to be ready (30 seconds)
sleep 30

# Start GPU services (this will take 2-5 minutes for model loading)
docker compose up -d vllm-contract vllm-compliance vllm-router embedding-service

# Wait for GPU services to load models
echo "Waiting for GPU services to load models (this may take 3-5 minutes)..."
sleep 180

# Start API and monitoring
docker compose up -d api prometheus grafana

# Start Nginx
docker compose up -d nginx
```

### 5.3 Verify Deployment
```bash
# Check all services are running
docker compose ps

# Check GPU usage
nvidia-smi

# Check logs
docker compose logs -f --tail=50 api

# Test API health
curl http://localhost:8000/health
```

---

## Step 6: Initialize Application

### 6.1 Create Admin User
```bash
cd /opt/legal_financial_ai_vault

# Run admin creation script
python scripts/create_admin.py admin@example.com SecurePassword123 "System Administrator"
```

### 6.2 Test Authentication
```bash
# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"SecurePassword123"}'

# Should return JWT token
```

---

## Step 7: Access Applications

### 7.1 API Documentation
- **Swagger UI:** https://legal-ai.client.internal/api/docs
- **ReDoc:** https://legal-ai.client.internal/api/redoc

### 7.2 Monitoring
- **Grafana:** https://legal-ai.client.internal/monitoring
  - Username: `admin`
  - Password: `<GRAFANA_PASSWORD from .env>`

### 7.3 Health Checks
- **API Health:** http://localhost:8000/health
- **System Health:** Run `./scripts/health_check.sh`

---

## Step 8: Configure Firewall

```bash
# Enable firewall
sudo ufw enable

# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTPS only (Nginx handles all traffic)
sudo ufw allow 443/tcp

# Optional: Allow HTTP for redirect
sudo ufw allow 80/tcp

# Check status
sudo ufw status
```

---

## Step 9: Setup Automated Backups

### 9.1 Make Backup Script Executable
```bash
chmod +x /opt/legal_financial_ai_vault/scripts/backup.sh
```

### 9.2 Setup Cron Job
```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /opt/legal_financial_ai_vault/scripts/backup.sh >> /var/log/legal-ai/backup.log 2>&1
```

---

## Step 10: Monitoring Setup

### 10.1 Access Grafana
1. Navigate to: https://legal-ai.client.internal/monitoring
2. Login with admin credentials
3. Add Prometheus data source:
   - URL: `http://prometheus:9090`
   - Save & Test

### 10.2 Import Dashboards
1. Create dashboard for:
   - GPU metrics (utilization, memory, temperature)
   - API performance (requests/sec, latency, errors)
   - System metrics (CPU, RAM, disk)

---

## Maintenance

### Daily Tasks
- Monitor `/var/log/legal-ai/` for errors
- Check `nvidia-smi` for GPU health
- Review Grafana dashboards

### Weekly Tasks
- Run `./scripts/health_check.sh`
- Review audit logs via admin panel
- Check disk space usage

### Monthly Tasks
- Update system packages
- Review and rotate logs
- Test backup restoration
- Security audit

---

## Troubleshooting

### Issue: GPU Not Detected in Docker
```bash
# Restart Docker with NVIDIA runtime
sudo systemctl restart docker

# Test again
docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi
```

### Issue: vLLM Service Won't Start
```bash
# Check logs
docker compose logs vllm-contract

# Common issues:
# - Model not found: Check /data/models/
# - GPU memory: Reduce --gpu-memory-utilization
# - CUDA version: Update NVIDIA drivers
```

### Issue: API Returns 500 Errors
```bash
# Check API logs
docker compose logs api

# Check database connection
docker exec legal-ai-postgres pg_isready -U legalai

# Restart API
docker compose restart api
```

### Issue: Out of Disk Space
```bash
# Check usage
df -h

# Clean up old Docker images
docker system prune -a

# Clean up old backups
find /data/backups -type d -mtime +30 -exec rm -rf {} \;
```

### Issue: High GPU Temperature
```bash
# Check temperature
nvidia-smi --query-gpu=temperature.gpu --format=csv

# If > 85°C:
# - Check server cooling
# - Reduce --gpu-memory-utilization in docker-compose.yml
# - Add throttling if needed
```

---

## Upgrading

### Upgrade Procedure
```bash
cd /opt/legal_financial_ai_vault

# Pull latest changes
git pull

# Backup current installation
./scripts/backup.sh

# Rebuild images
docker compose build

# Stop services
docker compose down

# Start with new images
docker compose up -d

# Check logs
docker compose logs -f --tail=100 api
```

---

## Uninstall

### Complete Removal
```bash
# Stop and remove containers
cd /opt/legal_financial_ai_vault
docker compose down -v

# Remove images
docker system prune -a

# Remove data (CAUTION!)
sudo rm -rf /data/documents
sudo rm -rf /data/vectors
# Keep backups: /data/backups

# Remove application
sudo rm -rf /opt/legal_financial_ai_vault
```

---

## Performance Tuning

### GPU Memory Optimization
Edit `docker-compose.yml`:
```yaml
# Reduce memory if needed
--gpu-memory-utilization 0.85  # Was 0.90
```

### Database Connection Pooling
Edit `api/database.py`:
```python
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=20,  # Increase for more concurrent users
    max_overflow=40
)
```

### Nginx Worker Processes
Edit `nginx/nginx.conf`:
```nginx
worker_processes 8;  # Match CPU cores
worker_connections 2048;  # Increase for high traffic
```

---

## Support

For issues:
1. Check logs: `docker compose logs <service>`
2. Run health check: `./scripts/health_check.sh`
3. Review troubleshooting section above
4. Check GitHub issues

---

**Last Updated:** 2025-11-10
**Version:** 1.0.0
