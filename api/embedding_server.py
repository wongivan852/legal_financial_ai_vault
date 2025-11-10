"""
Embedding Server - GPU 5
Serves text embeddings using bge-large-en-v1.5 model
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import torch
from sentence_transformers import SentenceTransformer
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Embedding Service", version="1.0.0")

# Model configuration
MODEL_PATH = os.getenv("MODEL_PATH", "/models/bge-large-en-v1.5")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Global model instance
model = None


class EmbedRequest(BaseModel):
    """Single embedding request"""
    text: str


class EmbedBatchRequest(BaseModel):
    """Batch embedding request"""
    texts: List[str]


@app.on_event("startup")
async def load_model():
    """Load embedding model on startup"""
    global model

    logger.info(f"Loading embedding model from {MODEL_PATH}")
    logger.info(f"Using device: {DEVICE}")

    try:
        model = SentenceTransformer(MODEL_PATH, device=DEVICE)
        logger.info("Embedding model loaded successfully")
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        raise


@app.post("/embed")
async def embed_text(request: EmbedRequest):
    """
    Generate embedding for single text

    Returns:
        Embedding vector as list of floats
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        embedding = model.encode(request.text, convert_to_tensor=False)
        return {"embedding": embedding.tolist()}

    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/embed_batch")
async def embed_batch(request: EmbedBatchRequest):
    """
    Generate embeddings for multiple texts

    Returns:
        List of embedding vectors
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    try:
        embeddings = model.encode(request.texts, convert_to_tensor=False, batch_size=32)
        return {"embeddings": [emb.tolist() for emb in embeddings]}

    except Exception as e:
        logger.error(f"Error generating batch embeddings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy" if model is not None else "unhealthy",
        "model": MODEL_PATH,
        "device": DEVICE
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("SERVICE_PORT", "8004"))
    uvicorn.run(app, host="0.0.0.0", port=port)
