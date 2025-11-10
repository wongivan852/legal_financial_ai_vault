#!/bin/bash
# Health Check Script for Legal AI Vault
# Checks status of all services and GPU health

set -e

echo "=== Legal AI Vault Health Check ==="
echo "Timestamp: $(date)"
echo ""

# Check Docker services
echo "=== Docker Services ==="
docker-compose ps

echo ""
echo "=== GPU Status ==="
nvidia-smi --query-gpu=index,name,driver_version,memory.total,memory.used,memory.free,temperature.gpu,utilization.gpu --format=csv,noheader,nounits

echo ""
echo "=== API Health ==="
API_HEALTH=$(curl -s http://localhost:8000/health || echo "API unreachable")
echo "$API_HEALTH"

echo ""
echo "=== Database Connection ==="
DB_STATUS=$(docker exec legal-ai-postgres pg_isready -U legalai 2>&1)
echo "$DB_STATUS"

echo ""
echo "=== Qdrant Status ==="
QDRANT_HEALTH=$(curl -s http://localhost:6333/health 2>&1 || echo "Qdrant unreachable")
echo "$QDRANT_HEALTH"

echo ""
echo "=== vLLM Services ==="
echo "Contract Review (GPU 0-1):"
curl -s http://localhost:8001/health 2>&1 || echo "Service unreachable"

echo "Compliance (GPU 2):"
curl -s http://localhost:8002/health 2>&1 || echo "Service unreachable"

echo "Router (GPU 3-4):"
curl -s http://localhost:8003/health 2>&1 || echo "Service unreachable"

echo ""
echo "=== Embedding Service (GPU 5) ==="
curl -s http://localhost:8004/health 2>&1 || echo "Service unreachable"

echo ""
echo "=== Disk Usage ==="
df -h | grep -E '(Filesystem|/data|/$)'

echo ""
echo "=== Memory Usage ==="
free -h

echo ""
echo "=== System Load ==="
uptime

echo ""
echo "=== Recent Logs (last 20 lines) ==="
docker-compose logs --tail=20 api

echo ""
echo "=== Health Check Complete ==="
