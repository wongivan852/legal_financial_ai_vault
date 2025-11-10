"""
Vector Store Service
Handles interactions with Qdrant vector database for RAG
"""

import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

from config import settings

logger = logging.getLogger(__name__)


class VectorStoreService:
    """Service for managing vector embeddings in Qdrant"""

    def __init__(self):
        """Initialize Qdrant client"""
        self.client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None,
        )
        self.embedding_dimension = 1024  # bge-large-en-v1.5 produces 1024-dim vectors

    def create_collection(self, collection_name: str, overwrite: bool = False):
        """
        Create a new collection in Qdrant

        Args:
            collection_name: Name of the collection
            overwrite: If True, delete existing collection first
        """
        try:
            if overwrite:
                self.client.delete_collection(collection_name=collection_name)

            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dimension,
                    distance=Distance.COSINE
                )
            )

            logger.info(f"Collection created: {collection_name}")

        except Exception as e:
            logger.error(f"Error creating collection {collection_name}: {e}")
            raise

    def collection_exists(self, collection_name: str) -> bool:
        """Check if collection exists"""
        try:
            collections = self.client.get_collections().collections
            return any(c.name == collection_name for c in collections)
        except Exception as e:
            logger.error(f"Error checking collection existence: {e}")
            return False

    def add_document(
        self,
        collection_name: str,
        document_id: str,
        text: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add document to vector store

        Args:
            collection_name: Name of the collection
            document_id: Unique document ID
            text: Document text content
            embedding: Vector embedding
            metadata: Additional metadata

        Returns:
            Vector ID
        """
        try:
            # Ensure collection exists
            if not self.collection_exists(collection_name):
                self.create_collection(collection_name)

            payload = {
                "document_id": document_id,
                "text": text,
                **(metadata or {})
            }

            point = PointStruct(
                id=document_id,
                vector=embedding,
                payload=payload
            )

            self.client.upsert(
                collection_name=collection_name,
                points=[point]
            )

            logger.info(f"Document added to {collection_name}: {document_id}")
            return document_id

        except Exception as e:
            logger.error(f"Error adding document to vector store: {e}")
            raise

    def add_documents_batch(
        self,
        collection_name: str,
        documents: List[Dict[str, Any]]
    ):
        """
        Add multiple documents to vector store in batch

        Args:
            collection_name: Name of the collection
            documents: List of documents with 'id', 'embedding', 'text', and optional metadata
        """
        try:
            if not self.collection_exists(collection_name):
                self.create_collection(collection_name)

            points = []
            for doc in documents:
                payload = {
                    "document_id": doc["id"],
                    "text": doc["text"],
                    **doc.get("metadata", {})
                }

                point = PointStruct(
                    id=doc["id"],
                    vector=doc["embedding"],
                    payload=payload
                )
                points.append(point)

            self.client.upsert(
                collection_name=collection_name,
                points=points
            )

            logger.info(f"Added {len(points)} documents to {collection_name}")

        except Exception as e:
            logger.error(f"Error adding batch documents: {e}")
            raise

    def search(
        self,
        collection_name: str,
        query_embedding: List[float],
        limit: int = 5,
        score_threshold: Optional[float] = None,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents

        Args:
            collection_name: Name of the collection
            query_embedding: Query vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score
            filter_conditions: Additional filters

        Returns:
            List of matching documents with scores
        """
        try:
            search_params = {
                "collection_name": collection_name,
                "query_vector": query_embedding,
                "limit": limit,
            }

            if score_threshold:
                search_params["score_threshold"] = score_threshold

            if filter_conditions:
                # Build Qdrant filter
                conditions = []
                for key, value in filter_conditions.items():
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value)
                        )
                    )
                search_params["query_filter"] = Filter(must=conditions)

            results = self.client.search(**search_params)

            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": result.id,
                    "score": result.score,
                    "text": result.payload.get("text"),
                    "metadata": {k: v for k, v in result.payload.items() if k not in ["text", "document_id"]}
                })

            return formatted_results

        except Exception as e:
            logger.error(f"Error searching vector store: {e}")
            raise

    def search_by_text(
        self,
        collection_name: str,
        query_text: str,
        embedding_service,
        limit: int = 5,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Search using text query (will be embedded first)

        Args:
            collection_name: Name of the collection
            query_text: Query text
            embedding_service: Service to generate embeddings
            limit: Maximum number of results
            score_threshold: Minimum similarity score

        Returns:
            List of matching documents
        """
        # Generate embedding for query text
        query_embedding = embedding_service.generate_embedding(query_text)

        return self.search(
            collection_name=collection_name,
            query_embedding=query_embedding,
            limit=limit,
            score_threshold=score_threshold
        )

    def delete_document(self, collection_name: str, document_id: str):
        """
        Delete document from vector store

        Args:
            collection_name: Name of the collection
            document_id: Document ID to delete
        """
        try:
            self.client.delete(
                collection_name=collection_name,
                points_selector=[document_id]
            )

            logger.info(f"Document deleted from {collection_name}: {document_id}")

        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            raise

    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """
        Get information about a collection

        Args:
            collection_name: Name of the collection

        Returns:
            Collection information
        """
        try:
            collection_info = self.client.get_collection(collection_name=collection_name)

            return {
                "name": collection_name,
                "vectors_count": collection_info.vectors_count,
                "points_count": collection_info.points_count,
                "status": collection_info.status
            }

        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return {}

    def list_collections(self) -> List[str]:
        """List all collections"""
        try:
            collections = self.client.get_collections().collections
            return [c.name for c in collections]
        except Exception as e:
            logger.error(f"Error listing collections: {e}")
            return []


# Predefined collection names
COLLECTIONS = {
    "LEGAL_CONTRACTS": "legal_contracts",
    "CASE_LAW": "case_law",
    "LEGAL_DOCUMENTS": "legal_documents",
    "REGULATIONS": "regulations"
}
