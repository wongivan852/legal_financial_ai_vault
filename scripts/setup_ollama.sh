#!/bin/bash

# Setup script for Ollama integration with Legal AI Vault
# This script helps configure Ollama and pull required models

set -e

echo "========================================="
echo "Legal AI Vault - Ollama Setup"
echo "========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Ollama is installed
echo -e "${YELLOW}[1/6] Checking Ollama installation...${NC}"
if ! command -v ollama &> /dev/null; then
    echo -e "${RED}Error: Ollama is not installed${NC}"
    echo "Please install Ollama from: https://ollama.ai/download"
    echo ""
    echo "On macOS: brew install ollama"
    echo "On Linux: curl https://ollama.ai/install.sh | sh"
    exit 1
fi

echo -e "${GREEN}✓ Ollama is installed${NC}"
OLLAMA_VERSION=$(ollama --version 2>&1 | head -n 1)
echo "  Version: $OLLAMA_VERSION"
echo ""

# Check if Ollama service is running
echo -e "${YELLOW}[2/6] Checking Ollama service...${NC}"
if ! curl -s http://localhost:11434/api/tags > /dev/null; then
    echo -e "${RED}Error: Ollama service is not running${NC}"
    echo "Please start Ollama:"
    echo "  On macOS: ollama serve"
    echo "  On Linux with systemd: systemctl start ollama"
    exit 1
fi

echo -e "${GREEN}✓ Ollama service is running${NC}"
echo ""

# List available models
echo -e "${YELLOW}[3/6] Checking available models...${NC}"
AVAILABLE_MODELS=$(ollama list 2>&1)
echo "$AVAILABLE_MODELS"
echo ""

# Required models
MODELS=(
    "qwen2.5:14b:Contract Review & Compliance"
    "qwen2.5:7b:Document Classification"
    "nomic-embed-text:Embeddings"
)

# Check and pull required models
echo -e "${YELLOW}[4/6] Pulling required models...${NC}"
echo "This may take a while depending on your internet connection."
echo ""

for MODEL_INFO in "${MODELS[@]}"; do
    IFS=':' read -r MODEL TAG PURPOSE <<< "$MODEL_INFO"
    FULL_NAME="${MODEL}:${TAG}"

    echo -e "${YELLOW}Checking ${FULL_NAME} (${PURPOSE})...${NC}"

    if echo "$AVAILABLE_MODELS" | grep -q "$FULL_NAME"; then
        echo -e "${GREEN}✓ ${FULL_NAME} already available${NC}"
    else
        echo -e "${YELLOW}Pulling ${FULL_NAME}...${NC}"
        if ollama pull "$FULL_NAME"; then
            echo -e "${GREEN}✓ ${FULL_NAME} pulled successfully${NC}"
        else
            echo -e "${RED}✗ Failed to pull ${FULL_NAME}${NC}"
            echo "  You can pull it manually later: ollama pull ${FULL_NAME}"
        fi
    fi
    echo ""
done

# Verify models
echo -e "${YELLOW}[5/6] Verifying models...${NC}"
FINAL_MODELS=$(ollama list)
echo "$FINAL_MODELS"
echo ""

# Test model
echo -e "${YELLOW}[6/6] Testing model inference...${NC}"
TEST_RESPONSE=$(ollama run qwen2.5:7b "Say 'OK' if you're working" --verbose 2>&1 | head -n 1)
if [[ "$TEST_RESPONSE" == *"OK"* ]] || [[ "$TEST_RESPONSE" == *"ok"* ]]; then
    echo -e "${GREEN}✓ Model inference test passed${NC}"
else
    echo -e "${YELLOW}Warning: Model test gave unexpected response${NC}"
    echo "  Response: $TEST_RESPONSE"
fi
echo ""

# Show model info
echo "========================================="
echo "Model Information:"
echo "========================================="
echo ""
echo "Contract Review Model: qwen2.5:14b"
echo "  - Purpose: Contract analysis and compliance checking"
echo "  - Size: ~8.5GB"
echo "  - Context: 32K tokens"
echo ""
echo "Router Model: qwen2.5:7b"
echo "  - Purpose: Document classification"
echo "  - Size: ~4.7GB"
echo "  - Context: 32K tokens"
echo ""
echo "Embedding Model: nomic-embed-text"
echo "  - Purpose: Text embeddings for RAG"
echo "  - Size: ~274MB"
echo "  - Dimensions: 768"
echo ""

# Show next steps
echo "========================================="
echo "Next Steps:"
echo "========================================="
echo ""
echo "1. Update .env file with Ollama configuration:"
echo "   INFERENCE_BACKEND=ollama"
echo "   OLLAMA_BASE_URL=http://localhost:11434"
echo ""
echo "2. Start the application:"
echo "   docker-compose -f docker-compose.ollama.yml up -d"
echo ""
echo "3. Import your XML dataset:"
echo "   python scripts/import_xml_dataset.py \\"
echo "     --zip-file ~/Downloads/download.zip \\"
echo "     --user-email admin@example.com"
echo ""
echo "4. Access the API:"
echo "   http://localhost:8000/docs"
echo ""
echo -e "${GREEN}✓ Ollama setup complete!${NC}"
echo ""

# Optional: Show Ollama model directory
if [ -d "$HOME/.ollama/models" ]; then
    MODELS_SIZE=$(du -sh "$HOME/.ollama/models" | cut -f1)
    echo "Models directory: $HOME/.ollama/models (Size: $MODELS_SIZE)"
    echo ""
fi
