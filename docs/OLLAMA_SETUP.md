# Ollama Integration Guide

This guide explains how to set up and use the Legal/Financial AI Vault with Ollama for local LLM deployment.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Detailed Setup](#detailed-setup)
5. [XML Dataset Import](#xml-dataset-import)
6. [Model Configuration](#model-configuration)
7. [Troubleshooting](#troubleshooting)
8. [Performance Tuning](#performance-tuning)

---

## Overview

The Legal AI Vault now supports **Ollama** as an alternative to vLLM for running large language models locally. This provides several benefits:

- ✅ **Easy Setup**: No GPU cluster configuration required
- ✅ **Local Development**: Run everything on your Mac/Linux machine
- ✅ **Model Flexibility**: Easy to switch between different models
- ✅ **Cost Effective**: No cloud API costs
- ✅ **Privacy**: All data stays on your machine

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Legal AI Vault (Docker)                  │
│  ┌──────────┐  ┌──────────┐  ┌─────────┐  ┌─────────────┐ │
│  │ FastAPI  │  │PostgreSQL│  │ Qdrant  │  │   Redis     │ │
│  └────┬─────┘  └──────────┘  └─────────┘  └─────────────┘ │
│       │                                                      │
└───────┼──────────────────────────────────────────────────────┘
        │
        │ HTTP API calls
        ▼
┌─────────────────────────────────────────────────────────────┐
│              Ollama (Host Machine)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │  qwen2.5:14b │  │  qwen2.5:7b  │  │nomic-embed-text │  │
│  │  (Contract)  │  │  (Router)    │  │  (Embeddings)   │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### System Requirements

**Minimum:**
- **OS**: macOS 11+, Linux (Ubuntu 20.04+, Debian 11+)
- **RAM**: 16 GB
- **Disk**: 30 GB free space
- **CPU**: 4 cores

**Recommended:**
- **OS**: macOS 13+ (Apple Silicon), Linux with NVIDIA GPU
- **RAM**: 32 GB+
- **Disk**: 100 GB SSD
- **GPU**: Apple M1/M2/M3 or NVIDIA GPU (8GB+ VRAM)

### Software Requirements

1. **Docker Desktop** 4.20+ (macOS/Windows) or Docker Engine 24+ (Linux)
2. **Docker Compose** 2.20+
3. **Ollama** 0.1.0+
4. **Python** 3.11+
5. **Git**

---

## Quick Start

### 1. Install Ollama

**macOS:**
```bash
brew install ollama
ollama serve
```

**Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
systemctl start ollama  # If using systemd
```

**Windows:**
Download from [https://ollama.ai/download](https://ollama.ai/download)

### 2. Run Automatic Setup

```bash
cd legal_financial_ai_vault
chmod +x scripts/setup_ollama.sh
./scripts/setup_ollama.sh
```

This script will:
- ✅ Check Ollama installation
- ✅ Pull required models (~13 GB total)
- ✅ Verify model functionality
- ✅ Display configuration instructions

### 3. Configure Environment

Copy and edit the environment file:

```bash
cp .env.example .env
```

Edit `.env` and ensure these settings:

```bash
INFERENCE_BACKEND=ollama
OLLAMA_BASE_URL=http://localhost:11434

# For Docker on macOS/Windows, use:
# OLLAMA_BASE_URL=http://host.docker.internal:11434

# Security keys (generate with: openssl rand -hex 32)
JWT_SECRET=<your-secret-key>
ENCRYPTION_KEY=<your-encryption-key>

# Database credentials
DB_PASSWORD=<secure-password>
```

### 4. Start Services

```bash
docker-compose -f docker-compose.ollama.yml up -d
```

### 5. Create Admin User

```bash
docker exec -it legal-ai-api python scripts/create_admin.py \
  --email admin@example.com \
  --password YourSecurePassword123 \
  --full-name "Admin User"
```

### 6. Verify Installation

```bash
# Check all services
docker-compose -f docker-compose.ollama.yml ps

# Check API health
curl http://localhost:8000/health

# View API docs
open http://localhost:8000/docs  # macOS
```

---

## Detailed Setup

### Step 1: Install and Configure Ollama

#### Installation

Choose your platform:

<details>
<summary><b>macOS (Apple Silicon - Recommended)</b></summary>

```bash
# Install via Homebrew
brew install ollama

# Or download from https://ollama.ai/download
```

**Apple Silicon Performance:**
- M1/M2/M3 chips provide excellent performance
- 14B models run smoothly with 16GB+ RAM
- Unified memory architecture is ideal for LLMs
</details>

<details>
<summary><b>macOS (Intel)</b></summary>

```bash
# Same installation as Apple Silicon
brew install ollama

# Note: Performance will be slower without GPU acceleration
```
</details>

<details>
<summary><b>Linux with NVIDIA GPU</b></summary>

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Verify GPU support
nvidia-smi
```

Ollama will automatically use NVIDIA GPUs if available.
</details>

<details>
<summary><b>Linux (CPU only)</b></summary>

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# CPU inference will be slower but functional
```
</details>

#### Start Ollama Service

**macOS:**
```bash
ollama serve
```

**Linux (systemd):**
```bash
systemctl enable ollama
systemctl start ollama
systemctl status ollama
```

**Verify Ollama is running:**
```bash
curl http://localhost:11434/api/tags
```

### Step 2: Pull Required Models

The application uses three types of models:

#### Contract Review & Analysis (14B model)
```bash
ollama pull qwen2.5:14b
```
- **Size**: ~8.5 GB
- **Purpose**: Contract review, compliance checking, legal research
- **Context**: 32K tokens
- **Recommended RAM**: 16 GB+

#### Document Classification (7B model)
```bash
ollama pull qwen2.5:7b
```
- **Size**: ~4.7 GB
- **Purpose**: Fast document routing and classification
- **Context**: 32K tokens
- **Recommended RAM**: 8 GB+

#### Text Embeddings
```bash
ollama pull nomic-embed-text
```
- **Size**: ~274 MB
- **Purpose**: Generate embeddings for RAG
- **Dimensions**: 768
- **Use**: Semantic search, document similarity

#### Verify Models

```bash
ollama list
```

Expected output:
```
NAME                    ID              SIZE      MODIFIED
qwen2.5:14b             abc123def456    8.5 GB    2 minutes ago
qwen2.5:7b              def456ghi789    4.7 GB    5 minutes ago
nomic-embed-text:latest ghi789jkl012    274 MB    8 minutes ago
```

### Step 3: Configure Application

#### Option A: Using docker-compose.ollama.yml (Recommended)

The `docker-compose.ollama.yml` file is pre-configured for Ollama:

```yaml
services:
  api:
    environment:
      INFERENCE_BACKEND: ollama
      OLLAMA_BASE_URL: http://host.docker.internal:11434  # For Docker
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

#### Option B: Local Development (without Docker)

For running the API locally:

```bash
export INFERENCE_BACKEND=ollama
export OLLAMA_BASE_URL=http://localhost:11434
export DATABASE_URL=postgresql://user:pass@localhost:5432/legal_ai_vault

# Start services
docker-compose up -d postgres qdrant redis

# Run API locally
cd api
uvicorn main:app --reload
```

### Step 4: Database Setup

The database tables are created automatically on first startup. To manually initialize:

```bash
docker exec -it legal-ai-api python -c "
from database import engine, Base
Base.metadata.create_all(bind=engine)
print('Database initialized')
"
```

---

## XML Dataset Import

Your XML legal documents can be imported using the provided scripts.

### Prepare Your Dataset

**Supported formats:**
- `.xml` - Generic XML documents
- `.akn` - Akoma Ntoso legal document standard
- `.xhtml` - XHTML legal documents

**Dataset location:**
- ZIP file: `~/Downloads/download.zip`
- Directory: `~/Documents/legal_docs/`

### Import from ZIP File

```bash
# Navigate to project directory
cd legal_financial_ai_vault

# Run import script
python scripts/import_xml_dataset.py \
  --zip-file ~/Downloads/download.zip \
  --user-email admin@example.com
```

### Import from Directory

```bash
python scripts/import_xml_dataset.py \
  --xml-dir ~/Documents/legal_docs/ \
  --user-email admin@example.com
```

### Import Process

The script will:

1. **Extract** XML files from ZIP (if applicable)
2. **Parse** XML structure and extract content
3. **Encrypt** files and store securely
4. **Create** database records
5. **Generate** embeddings using Ollama
6. **Store** vectors in Qdrant for RAG

### Expected Output

```
=========================================================
Checking Prerequisites
=========================================================

✓ Python 3.11 installed
✓ Ollama service is running
✓ Qdrant vector database is running

=========================================================
Importing XML Dataset
=========================================================

ℹ ZIP file: /Users/yourname/Downloads/download.zip
ℹ Size: 245.67 MB
ℹ Ollama URL: http://localhost:11434
ℹ User: admin@example.com

Processing file 123/456...

=========================================================
Import Results
=========================================================

Total files:      456
Processed:        450
Failed:           2
Skipped:          4

✓ Created 450 documents
```

### XML Parsing

The script intelligently parses different XML formats:

**Akoma Ntoso (Legal Document Standard):**
```xml
<akomaNtoso>
  <meta>
    <identification>
      <FRBRWork>
        <FRBRdate date="2024-01-01"/>
      </FRBRWork>
    </identification>
  </meta>
  <body>
    <section>
      <heading>Article 1</heading>
      <content>
        <p>Contract provisions...</p>
      </content>
    </section>
  </body>
</akomaNtoso>
```

**Generic Legal XML:**
```xml
<contract>
  <title>Service Agreement</title>
  <parties>
    <party role="client">Acme Corp</party>
    <party role="provider">Legal Services Inc</party>
  </parties>
  <clauses>
    <clause id="1">
      <heading>Scope of Services</heading>
      <text>...</text>
    </clause>
  </clauses>
</contract>
```

The parser extracts:
- Title/heading
- Metadata (dates, parties, etc.)
- Structured sections
- Full text content

---

## Model Configuration

### Changing Models

You can use different Ollama models by updating `.env`:

```bash
# For better performance on resource-constrained systems
OLLAMA_CONTRACT_MODEL=llama2:13b
OLLAMA_ROUTER_MODEL=llama2:7b

# For maximum quality
OLLAMA_CONTRACT_MODEL=qwen2.5:32b
OLLAMA_ROUTER_MODEL=qwen2.5:14b

# For embeddings alternatives
OLLAMA_EMBEDDING_MODEL=mxbai-embed-large  # 1024 dimensions
```

**Note:** If you change the embedding model, update the vector dimension in the code:

```python
# api/services/vector_store.py
vector_size = 1024  # For mxbai-embed-large
vector_size = 768   # For nomic-embed-text (default)
```

### Model Performance

| Model | Size | RAM | Tokens/sec | Quality | Use Case |
|-------|------|-----|------------|---------|----------|
| qwen2.5:7b | 4.7GB | 8GB | ~30-50 | Good | Classification, routing |
| qwen2.5:14b | 8.5GB | 16GB | ~15-25 | Excellent | Contract analysis, compliance |
| qwen2.5:32b | 19GB | 32GB | ~8-15 | Outstanding | Complex legal research |
| llama2:7b | 3.8GB | 8GB | ~40-60 | Good | General purpose |
| llama2:13b | 7.3GB | 16GB | ~20-30 | Very Good | General purpose |

*Performance measured on M2 Max with 32GB unified memory*

### Temperature Settings

Different agents use different temperatures (configured in `api/config.py`):

```python
# Contract Review - Low temperature for consistency
DEFAULT_TEMPERATURE = 0.2

# Legal Research - Medium temperature for creativity
RESEARCH_TEMPERATURE = 0.5

# Document Classification - Very low for deterministic results
ROUTER_TEMPERATURE = 0.1
```

---

## Troubleshooting

### Issue: Ollama not accessible from Docker

**Symptoms:**
```
Error: Connection refused to http://localhost:11434
```

**Solution for macOS/Windows:**
```bash
# In docker-compose.ollama.yml, use:
OLLAMA_BASE_URL: http://host.docker.internal:11434

# And add:
extra_hosts:
  - "host.docker.internal:host-gateway"
```

**Solution for Linux:**
```bash
# Use host network mode OR
# Find your host IP:
ip addr show docker0 | grep inet

# Update .env:
OLLAMA_BASE_URL=http://172.17.0.1:11434  # Use your actual IP
```

### Issue: Model loading is slow

**Symptoms:**
- First request takes 30+ seconds
- Subsequent requests are fast

**Explanation:**
This is normal - models are loaded into memory on first use.

**Solutions:**
```bash
# Pre-load models
ollama run qwen2.5:14b "test"
ollama run qwen2.5:7b "test"
ollama run nomic-embed-text

# Or enable keep-alive (models stay in memory)
# In ~/.ollama/config:
{
  "keep_alive": "1h"
}
```

### Issue: Out of memory errors

**Symptoms:**
```
Error: failed to allocate memory
```

**Solutions:**

1. **Use smaller models:**
```bash
OLLAMA_CONTRACT_MODEL=qwen2.5:7b  # Instead of 14b
```

2. **Reduce context length:**
```python
# In agent prompts, limit document size
max_context = 10000  # characters
```

3. **Enable swap (not recommended for production):**
```bash
# macOS
sudo sysctl vm.swappiness=10

# Linux
sudo sysctl vm.swappiness=60
```

### Issue: XML import fails

**Symptoms:**
```
Error: No module named 'lxml'
```

**Solution:**
```bash
pip install lxml httpx
```

**Symptoms:**
```
Error: User with email admin@example.com not found
```

**Solution:**
```bash
# Create admin user first
docker exec -it legal-ai-api python scripts/create_admin.py \
  --email admin@example.com \
  --password password123
```

### Issue: Embeddings dimension mismatch

**Symptoms:**
```
Error: Vector dimension mismatch (expected 768, got 1024)
```

**Solution:**
```bash
# Delete and recreate Qdrant collection
curl -X DELETE http://localhost:6333/collections/legal_documents

# Restart import
python scripts/import_xml_dataset.py --zip-file ~/Downloads/download.zip
```

---

## Performance Tuning

### GPU Acceleration

**NVIDIA GPUs (Linux):**

Ollama automatically uses CUDA if available:

```bash
# Verify GPU usage
nvidia-smi

# Monitor during inference
watch -n 1 nvidia-smi
```

**Apple Silicon (macOS):**

Metal acceleration is automatic. Monitor with:

```bash
# Check memory usage
sudo powermetrics --samplers gpu_power

# Activity Monitor > GPU tab
```

### Parallelization

For multiple concurrent requests, Ollama handles queuing automatically. To optimize:

```bash
# Increase Ollama's concurrent request limit
export OLLAMA_NUM_PARALLEL=4

# Restart Ollama
ollama serve
```

### Batch Processing

For large document imports, process in batches:

```python
# scripts/import_xml_dataset.py
# Adjust batch size
BATCH_SIZE = 10  # Process 10 documents before committing
```

### Caching

Enable Redis caching for repeated queries:

```python
# api/services/ollama_client.py
# Implement response caching
@cache(ttl=3600)  # 1 hour cache
async def generate(...):
    ...
```

---

## Next Steps

1. **Test the API**:
   ```bash
   curl http://localhost:8000/api/documents
   ```

2. **Import your dataset**:
   ```bash
   python scripts/import_xml_dataset.py --zip-file ~/Downloads/download.zip
   ```

3. **Analyze a contract**:
   ```bash
   curl -X POST http://localhost:8000/api/agents/contract-review \
     -H "Content-Type: application/json" \
     -d '{"document_id": "<your-doc-id>"}'
   ```

4. **Explore API documentation**:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

5. **Monitor performance**:
   - Grafana: http://localhost:3001
   - Prometheus: http://localhost:9090

---

## Additional Resources

- [Ollama Documentation](https://github.com/ollama/ollama/tree/main/docs)
- [Qwen2.5 Model Card](https://huggingface.co/Qwen/Qwen2.5-14B-Instruct)
- [Akoma Ntoso Specification](http://docs.oasis-open.org/legaldocml/akn-core/v1.0/akn-core-v1.0.html)
- [Legal AI Vault API Documentation](http://localhost:8000/docs)

---

## Support

For issues and questions:
- GitHub Issues: [legal_financial_ai_vault/issues](https://github.com/wongivan852/legal_financial_ai_vault/issues)
- Documentation: `docs/` directory
- API Docs: http://localhost:8000/docs
