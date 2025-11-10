"""
Base Agent Class
Abstract base class for all AI agents
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
import logging

from services.inference import InferenceService
from services.embedding import EmbeddingService
from services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all AI agents"""

    def __init__(self):
        """Initialize agent with required services"""
        self.inference_service = InferenceService()
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStoreService()

    @property
    @abstractmethod
    def agent_type(self) -> str:
        """Return the agent type identifier"""
        pass

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Return the system prompt for this agent"""
        pass

    @property
    def default_temperature(self) -> float:
        """Default temperature for this agent (can be overridden)"""
        return 0.3

    @property
    def default_max_tokens(self) -> int:
        """Default max tokens for this agent (can be overridden)"""
        return 4096

    @abstractmethod
    async def process(self, **kwargs) -> Dict[str, Any]:
        """
        Process the agent's main task
        Must be implemented by subclasses

        Returns:
            Dictionary with results
        """
        pass

    async def generate_response(
        self,
        prompt: str,
        user_id: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> Dict:
        """
        Generate response using inference service

        Args:
            prompt: User prompt
            user_id: User ID for logging
            system_prompt: Override default system prompt
            max_tokens: Override default max tokens
            temperature: Override default temperature

        Returns:
            Inference result dictionary
        """
        return await self.inference_service.generate(
            prompt=prompt,
            agent_type=self.agent_type,
            user_id=user_id,
            system_prompt=system_prompt or self.system_prompt,
            max_tokens=max_tokens or self.default_max_tokens,
            temperature=temperature or self.default_temperature
        )

    def preprocess_input(self, input_data: Any) -> Any:
        """
        Preprocess input before sending to LLM
        Can be overridden by subclasses

        Args:
            input_data: Raw input data

        Returns:
            Preprocessed data
        """
        return input_data

    def postprocess_output(self, output_data: Dict) -> Dict:
        """
        Postprocess LLM output
        Can be overridden by subclasses

        Args:
            output_data: Raw LLM output

        Returns:
            Processed output
        """
        return output_data

    def validate_input(self, **kwargs) -> bool:
        """
        Validate input parameters
        Can be overridden by subclasses

        Returns:
            True if valid, raises exception otherwise
        """
        return True

    async def get_context_from_rag(
        self,
        query: str,
        collection_name: str,
        limit: int = 3,
        score_threshold: float = 0.7
    ) -> str:
        """
        Get relevant context from vector database (RAG)

        Args:
            query: Query text
            collection_name: Vector collection to search
            limit: Number of results
            score_threshold: Minimum similarity score

        Returns:
            Formatted context string
        """
        try:
            # Generate embedding for query
            query_embedding = self.embedding_service.generate_embedding(query)

            # Search vector store
            results = self.vector_store.search(
                collection_name=collection_name,
                query_embedding=query_embedding,
                limit=limit,
                score_threshold=score_threshold
            )

            if not results:
                return ""

            # Format context
            context_parts = []
            for i, result in enumerate(results, 1):
                context_parts.append(
                    f"### Reference {i} (Score: {result['score']:.3f}):\n{result['text']}\n"
                )

            return "\n".join(context_parts)

        except Exception as e:
            logger.error(f"Error getting RAG context: {e}")
            return ""

    def format_error(self, error: Exception) -> Dict:
        """Format error response"""
        return {
            "status": "error",
            "error_message": str(error),
            "agent_type": self.agent_type
        }
