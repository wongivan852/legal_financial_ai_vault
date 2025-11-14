# Ollama Integration - Quick Start

This document provides a quick overview of the new Ollama integration for the Legal/Financial AI Vault.

## What's New

The Legal AI Vault now supports **Ollama** as an alternative to vLLM, enabling:

✅ **Local Deployment** - Run LLMs on your Mac/Linux machine
✅ **Easy Setup** - No GPU cluster configuration required
✅ **XML Dataset Support** - Import legal documents in XML format
✅ **Flexible Models** - Easy to switch between different Ollama models
✅ **Cost Effective** - No cloud API costs
✅ **Complete Privacy** - All data stays on your machine

## Quick Start (3 Minutes)

### 1. Install Ollama

**macOS:**
```bash
brew install ollama
ollama serve
```

**Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### 2. Setup Models

```bash
./scripts/setup_ollama.sh
```

This automatically pulls required models (~13GB total):
- `qwen2.5:14b` - Contract analysis
- `qwen2.5:7b` - Document classification
- `nomic-embed-text` - Embeddings

### 3. Configure & Start

```bash
# Copy environment template
cp .env.example .env

# Edit .env and set:
# INFERENCE_BACKEND=ollama
# OLLAMA_BASE_URL=http://localhost:11434

# Start services
docker-compose -f docker-compose.ollama.yml up -d
```

### 4. Create Admin User

```bash
docker exec -it legal-ai-api python scripts/create_admin.py \
  --email admin@example.com \
  --password YourPassword123
```

### 5. Import XML Dataset

```bash
python scripts/import_xml_dataset.py \
  --zip-file ~/Downloads/download.zip \
  --user-email admin@example.com
```

## What Was Added

### New Files

**Services:**
- `api/services/ollama_client.py` - Ollama API client with full async support
  - Health checks, model listing
  - Chat and completion endpoints
  - Embeddings generation
  - Streaming support
  - Model management (pull/delete)

**Scripts:**
- `scripts/xml_ingestion.py` - XML document parser and ingestion engine
  - Supports Akoma Ntoso legal XML standard
  - Generic XML parsing with intelligent extraction
  - Automatic encryption and vectorization
  - Batch processing for large datasets

- `scripts/import_xml_dataset.py` - User-friendly import wrapper
  - ZIP file extraction
  - Progress tracking
  - Prerequisite checking
  - Colored terminal output

- `scripts/setup_ollama.sh` - Automated Ollama setup
  - Checks Ollama installation
  - Pulls required models
  - Verifies model functionality
  - Displays configuration guide

**Infrastructure:**
- `docker-compose.ollama.yml` - Docker Compose for Ollama deployment
  - Connects to host Ollama instance
  - No GPU container configuration needed
  - Uses `host.docker.internal` for macOS/Windows

**Documentation:**
- `docs/OLLAMA_SETUP.md` - Comprehensive setup guide (60+ pages)
  - Installation instructions for all platforms
  - XML import guide
  - Model configuration
  - Troubleshooting
  - Performance tuning

### Updated Files

**Configuration:**
- `api/config.py` - Added Ollama settings
  - `INFERENCE_BACKEND` - Choose vLLM or Ollama
  - Ollama model configuration
  - XML file type support

- `.env.example` - Ollama environment variables
  - Model names
  - API endpoints
  - Backend selection

## Architecture

```
┌───────────────────────────────────────────────┐
│         Legal AI Vault (Docker)               │
│  ┌─────────┐ ┌──────┐ ┌────────┐ ┌────────┐ │
│  │FastAPI  │ │Postgres│ │Qdrant │ │ Redis  │ │
│  └────┬────┘ └────────┘ └────────┘ └────────┘ │
└───────┼───────────────────────────────────────┘
        │ HTTP (port 11434)
        ▼
┌───────────────────────────────────────────────┐
│         Ollama (Host Machine)                 │
│  ┌────────────┐ ┌──────────┐ ┌─────────────┐ │
│  │qwen2.5:14b │ │qwen2.5:7b│ │nomic-embed  │ │
│  └────────────┘ └──────────┘ └─────────────┘ │
└───────────────────────────────────────────────┘
```

## XML Dataset Support

### Supported Formats

- **`.xml`** - Generic XML documents
- **`.akn`** - Akoma Ntoso legal document standard
- **`.xhtml`** - XHTML legal documents

### XML Parsing Features

The ingestion pipeline intelligently handles:

1. **Akoma Ntoso** - International legal document standard
   - Extracts metadata (dates, jurisdiction, parties)
   - Preserves document structure (sections, articles, clauses)
   - Handles legal-specific elements

2. **Generic Legal XML** - Custom formats
   - Finds titles, headings, parties
   - Extracts sections and clauses
   - Preserves hierarchical structure

3. **Fallback Parser** - Any XML structure
   - Extracts all text content
   - Maintains basic metadata

### Import Process

1. **Extract** - Unzip XML files
2. **Parse** - Extract structure and content
3. **Encrypt** - Secure storage with Fernet encryption
4. **Embed** - Generate vectors with Ollama
5. **Index** - Store in Qdrant for RAG

## Model Configuration

### Default Models

| Purpose | Model | Size | RAM | Use Case |
|---------|-------|------|-----|----------|
| Contract Review | qwen2.5:14b | 8.5GB | 16GB | Deep analysis, compliance |
| Compliance Check | qwen2.5:14b | 8.5GB | 16GB | Regulatory review |
| Document Router | qwen2.5:7b | 4.7GB | 8GB | Fast classification |
| Legal Research | qwen2.5:14b | 8.5GB | 16GB | Case law, precedent |
| Embeddings | nomic-embed-text | 274MB | 2GB | RAG, similarity search |

### Alternative Models

You can use different models by updating `.env`:

```bash
# Lighter models for constrained systems
OLLAMA_CONTRACT_MODEL=llama2:13b
OLLAMA_ROUTER_MODEL=llama2:7b

# Larger models for maximum quality
OLLAMA_CONTRACT_MODEL=qwen2.5:32b
OLLAMA_ROUTER_MODEL=qwen2.5:14b
```

## System Requirements

### Minimum
- **RAM**: 16 GB
- **Disk**: 30 GB free
- **CPU**: 4 cores

### Recommended
- **RAM**: 32 GB+
- **Disk**: 100 GB SSD
- **GPU**: Apple M1/M2/M3 or NVIDIA (8GB+ VRAM)

## Performance

### Inference Speed (M2 Max, 32GB)

| Model | Tokens/sec | Latency (first token) |
|-------|------------|----------------------|
| qwen2.5:14b | 15-25 | ~2-3s |
| qwen2.5:7b | 30-50 | ~1-2s |
| nomic-embed-text | N/A | ~100ms |

### Import Speed

- **Small dataset** (100 files, 50MB): ~5-10 minutes
- **Medium dataset** (1000 files, 500MB): ~30-60 minutes
- **Large dataset** (10000 files, 5GB): ~3-6 hours

*Times vary based on hardware and model performance*

## Migration from vLLM

If you're migrating from vLLM:

1. **Update configuration:**
   ```bash
   # In .env
   INFERENCE_BACKEND=ollama  # Change from 'vllm'
   ```

2. **Use Ollama Docker Compose:**
   ```bash
   docker-compose -f docker-compose.ollama.yml up -d
   ```

3. **No code changes required** - The application automatically detects the backend

4. **Models are backwards compatible** - Same Qwen2.5 models, different runtime

## Troubleshooting

### Can't connect to Ollama from Docker

**Solution for macOS/Windows:**
```bash
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

**Solution for Linux:**
```bash
# Find Docker bridge IP
ip addr show docker0 | grep inet
# Use that IP: http://172.17.0.1:11434
```

### Models loading slowly

This is normal on first request. To pre-load:
```bash
ollama run qwen2.5:14b "test"
ollama run qwen2.5:7b "test"
```

### Out of memory

Use smaller models:
```bash
OLLAMA_CONTRACT_MODEL=qwen2.5:7b  # Instead of 14b
```

## Next Steps

1. **Read full documentation:** `docs/OLLAMA_SETUP.md`
2. **Import your dataset:** See XML import section above
3. **Test the API:** http://localhost:8000/docs
4. **Monitor performance:** http://localhost:3001 (Grafana)

## API Examples

### Contract Analysis
```bash
curl -X POST http://localhost:8000/api/agents/contract-review \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-token>" \
  -d '{
    "document_id": "your-doc-id",
    "analysis_type": "comprehensive"
  }'
```

### Legal Research
```bash
curl -X POST http://localhost:8000/api/agents/legal-research \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-token>" \
  -d '{
    "query": "precedent for breach of contract",
    "jurisdiction": "US"
  }'
```

## Compatibility

✅ **Fully compatible** with existing vLLM deployment
✅ **Same API endpoints** - No client changes needed
✅ **Same database schema** - Shared PostgreSQL database
✅ **Same models** - Qwen2.5 available in both backends

You can run both backends simultaneously and switch between them via configuration.

## Support

- **Full Documentation**: `docs/OLLAMA_SETUP.md`
- **API Reference**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **GitHub Issues**: https://github.com/wongivan852/legal_financial_ai_vault/issues

---

**Ready to get started?** Run `./scripts/setup_ollama.sh` and follow the prompts!
