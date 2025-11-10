#!/bin/bash
# Backup Script for Legal AI Vault
# Backs up database, documents, and configurations

set -e

BACKUP_DIR="/data/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="$BACKUP_DIR/backup_$TIMESTAMP"

echo "Starting backup at $(date)"

# Create backup directory
mkdir -p "$BACKUP_PATH"

# Backup PostgreSQL database
echo "Backing up database..."
docker exec legal-ai-postgres pg_dump -U legalai legal_ai_vault | gzip > "$BACKUP_PATH/database.sql.gz"

# Backup documents
echo "Backing up documents..."
tar -czf "$BACKUP_PATH/documents.tar.gz" /data/documents/

# Backup Qdrant vector database
echo "Backing up vector database..."
tar -czf "$BACKUP_PATH/qdrant.tar.gz" /data/vectors/

# Backup configurations
echo "Backing up configurations..."
tar -czf "$BACKUP_PATH/configs.tar.gz" \
    /opt/legal-ai-vault/.env.production \
    /opt/legal-ai-vault/docker-compose.yml \
    /opt/legal-ai-vault/nginx/

# Create backup metadata
cat > "$BACKUP_PATH/metadata.txt" << EOF
Backup Date: $(date)
Timestamp: $TIMESTAMP
Database: PostgreSQL
Documents: /data/documents
Vectors: Qdrant
Configurations: Included
EOF

# Calculate sizes
du -sh "$BACKUP_PATH"/* > "$BACKUP_PATH/sizes.txt"

echo "Backup completed at $(date)"
echo "Backup location: $BACKUP_PATH"

# Cleanup old backups (keep last 30 days)
echo "Cleaning up old backups..."
find "$BACKUP_DIR" -name "backup_*" -type d -mtime +30 -exec rm -rf {} \;

echo "Backup script finished successfully"
