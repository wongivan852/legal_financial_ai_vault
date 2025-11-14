"""
Ollama Client Service
Handles communication with local Ollama instance for LLM inference.
Replaces vLLM with Ollama for local model deployment.
"""

import httpx
import asyncio
from typing import Optional, Dict, Any, List, AsyncIterator
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for interacting with Ollama API."""

    def __init__(self, base_url: str = "http://localhost:11434"):
        """
        Initialize Ollama client.

        Args:
            base_url: Base URL of Ollama API (default: http://localhost:11434)
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = httpx.Timeout(300.0, connect=10.0)  # 5min generation, 10s connect

    async def health_check(self) -> bool:
        """Check if Ollama service is healthy."""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    async def list_models(self) -> List[Dict[str, Any]]:
        """List all available models in Ollama."""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
                return data.get("models", [])
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
            return []

    async def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        context: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Generate completion using Ollama.

        Args:
            model: Model name (e.g., "llama2", "mistral", "qwen2.5")
            prompt: User prompt
            system: System prompt
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            context: Previous conversation context

        Returns:
            Dict with response, tokens, and timing information
        """
        start_time = datetime.utcnow()

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
            }
        }

        if system:
            payload["system"] = system

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        if context:
            payload["context"] = context

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if stream:
                    return await self._generate_stream(client, payload, start_time)
                else:
                    response = await client.post(
                        f"{self.base_url}/api/generate",
                        json=payload
                    )
                    response.raise_for_status()
                    result = response.json()

                    end_time = datetime.utcnow()
                    latency = (end_time - start_time).total_seconds()

                    return {
                        "response": result.get("response", ""),
                        "model": result.get("model", model),
                        "context": result.get("context", []),
                        "total_duration": result.get("total_duration", 0) / 1e9,  # Convert to seconds
                        "load_duration": result.get("load_duration", 0) / 1e9,
                        "prompt_eval_count": result.get("prompt_eval_count", 0),
                        "eval_count": result.get("eval_count", 0),
                        "latency": latency,
                        "done": result.get("done", True)
                    }
        except httpx.TimeoutException:
            logger.error(f"Ollama request timed out for model {model}")
            raise Exception(f"Request timed out after {self.timeout.read}s")
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise

    async def _generate_stream(
        self,
        client: httpx.AsyncClient,
        payload: Dict[str, Any],
        start_time: datetime
    ) -> AsyncIterator[str]:
        """Handle streaming responses from Ollama."""
        async with client.stream(
            "POST",
            f"{self.base_url}/api/generate",
            json=payload
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    import json
                    try:
                        chunk = json.loads(line)
                        if "response" in chunk:
                            yield chunk["response"]
                    except json.JSONDecodeError:
                        continue

    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Chat completion using Ollama chat endpoint.

        Args:
            model: Model name
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response

        Returns:
            Dict with response and metadata
        """
        start_time = datetime.utcnow()

        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
            }
        }

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload
                )
                response.raise_for_status()
                result = response.json()

                end_time = datetime.utcnow()
                latency = (end_time - start_time).total_seconds()

                message = result.get("message", {})

                return {
                    "response": message.get("content", ""),
                    "role": message.get("role", "assistant"),
                    "model": result.get("model", model),
                    "total_duration": result.get("total_duration", 0) / 1e9,
                    "load_duration": result.get("load_duration", 0) / 1e9,
                    "prompt_eval_count": result.get("prompt_eval_count", 0),
                    "eval_count": result.get("eval_count", 0),
                    "latency": latency,
                    "done": result.get("done", True)
                }
        except Exception as e:
            logger.error(f"Ollama chat failed: {e}")
            raise

    async def embeddings(self, model: str, text: str) -> List[float]:
        """
        Generate embeddings using Ollama.

        Args:
            model: Model name (e.g., "nomic-embed-text", "mxbai-embed-large")
            text: Text to embed

        Returns:
            List of embedding values
        """
        payload = {
            "model": model,
            "prompt": text
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                return result.get("embedding", [])
        except Exception as e:
            logger.error(f"Ollama embeddings failed: {e}")
            raise

    async def pull_model(self, model: str) -> bool:
        """
        Pull a model from Ollama registry.

        Args:
            model: Model name to pull (e.g., "llama2", "mistral")

        Returns:
            True if successful, False otherwise
        """
        payload = {"name": model}

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(600.0)) as client:
                response = await client.post(
                    f"{self.base_url}/api/pull",
                    json=payload
                )
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Failed to pull model {model}: {e}")
            return False

    async def delete_model(self, model: str) -> bool:
        """Delete a model from Ollama."""
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                response = await client.delete(
                    f"{self.base_url}/api/delete",
                    json={"name": model}
                )
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(f"Failed to delete model {model}: {e}")
            return False


class OllamaInferenceService:
    """
    High-level inference service using Ollama.
    Provides agent-specific model routing and management.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        default_model: str = "qwen2.5:14b",
        contract_model: str = "qwen2.5:14b",
        compliance_model: str = "qwen2.5:14b",
        router_model: str = "qwen2.5:7b",
        research_model: str = "qwen2.5:14b",
        embedding_model: str = "nomic-embed-text"
    ):
        """
        Initialize inference service with model routing.

        Args:
            base_url: Ollama API URL
            default_model: Default model for general tasks
            contract_model: Model for contract review
            compliance_model: Model for compliance checking
            router_model: Lightweight model for document routing
            research_model: Model for legal research
            embedding_model: Model for embeddings
        """
        self.client = OllamaClient(base_url)
        self.models = {
            "default": default_model,
            "contract_review": contract_model,
            "compliance": compliance_model,
            "document_router": router_model,
            "legal_research": research_model,
            "embedding": embedding_model
        }

    async def health_check(self) -> Dict[str, bool]:
        """Check health of all configured models."""
        is_healthy = await self.client.health_check()

        if not is_healthy:
            return {"ollama": False}

        available_models = await self.client.list_models()
        model_names = [m.get("name", "") for m in available_models]

        health_status = {"ollama": True}
        for agent_type, model_name in self.models.items():
            health_status[agent_type] = any(model_name in m for m in model_names)

        return health_status

    async def generate(
        self,
        prompt: str,
        agent_type: str,
        user_id: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate response using appropriate model for agent type.

        Args:
            prompt: User prompt
            agent_type: Type of agent (contract_review, compliance, etc.)
            user_id: User ID for logging
            system_prompt: System prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            Dict with response and metadata
        """
        model = self.models.get(agent_type, self.models["default"])

        logger.info(f"Generating with model {model} for agent {agent_type}, user {user_id}")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        result = await self.client.chat(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        return result

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        model = self.models["embedding"]
        return await self.client.embeddings(model, text)
