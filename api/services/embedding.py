"""
Embedding Service
Client for text embedding generation using GPU 5
"""

import logging
from typing import List, Union
import aiohttp
import requests

from config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings"""

    def __init__(self):
        """Initialize embedding service"""
        self.embedding_url = settings.EMBEDDING_URL

    async def generate_embedding_async(self, text: str) -> List[float]:
        """
        Generate embedding for text (async)

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        try:
            async with aiohttp.ClientSession() as session:
                payload = {"text": text}

                async with session.post(
                    f"{self.embedding_url}/embed",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:

                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Embedding service error: {response.status} - {error_text}")
                        raise Exception(f"Embedding service error: {response.status}")

                    result = await response.json()
                    embedding = result.get("embedding")

                    if not embedding:
                        raise ValueError("No embedding returned from service")

                    return embedding

        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text (sync)

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        try:
            payload = {"text": text}

            response = requests.post(
                f"{self.embedding_url}/embed",
                json=payload,
                timeout=30
            )

            if response.status_code != 200:
                logger.error(f"Embedding service error: {response.status_code} - {response.text}")
                raise Exception(f"Embedding service error: {response.status_code}")

            result = response.json()
            embedding = result.get("embedding")

            if not embedding:
                raise ValueError("No embedding returned from service")

            return embedding

        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    async def generate_embeddings_batch_async(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (async batch)

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        try:
            async with aiohttp.ClientSession() as session:
                payload = {"texts": texts}

                async with session.post(
                    f"{self.embedding_url}/embed_batch",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:

                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Embedding service error: {response.status} - {error_text}")
                        raise Exception(f"Embedding service error: {response.status}")

                    result = await response.json()
                    embeddings = result.get("embeddings")

                    if not embeddings:
                        raise ValueError("No embeddings returned from service")

                    return embeddings

        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            raise

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (sync batch)

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        try:
            payload = {"texts": texts}

            response = requests.post(
                f"{self.embedding_url}/embed_batch",
                json=payload,
                timeout=60
            )

            if response.status_code != 200:
                logger.error(f"Embedding service error: {response.status_code} - {response.text}")
                raise Exception(f"Embedding service error: {response.status_code}")

            result = response.json()
            embeddings = result.get("embeddings")

            if not embeddings:
                raise ValueError("No embeddings returned from service")

            return embeddings

        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            raise

    async def health_check(self) -> bool:
        """
        Check if embedding service is healthy

        Returns:
            True if healthy, False otherwise
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.embedding_url}/health",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status == 200

        except Exception as e:
            logger.error(f"Embedding service health check failed: {e}")
            return False
