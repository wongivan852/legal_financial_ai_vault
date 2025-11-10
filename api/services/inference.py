"""
Inference Service - Handles communication with vLLM endpoints
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional
import logging
from datetime import datetime

from config import settings

logger = logging.getLogger(__name__)


class InferenceService:
    """Manages LLM inference requests across GPU services"""

    def __init__(self):
        self.endpoints = {
            "contract_review": settings.VLLM_CONTRACT_URL,
            "compliance": settings.VLLM_COMPLIANCE_URL,
            "router": settings.VLLM_ROUTER_URL
        }

    async def generate(
        self,
        prompt: str,
        agent_type: str,
        user_id: str,
        max_tokens: int = None,
        temperature: float = None,
        system_prompt: Optional[str] = None
    ) -> Dict:
        """
        Generate response from specified agent

        Args:
            prompt: User query
            agent_type: One of "contract_review", "compliance", "router"
            user_id: User identifier for audit logging
            max_tokens: Maximum response length
            temperature: Sampling temperature
            system_prompt: Optional system instruction

        Returns:
            Dict with 'response', 'tokens_used', 'latency'
        """

        if agent_type not in self.endpoints:
            raise ValueError(f"Unknown agent type: {agent_type}")

        endpoint = self.endpoints[agent_type]
        start_time = datetime.utcnow()

        # Prepare request payload (OpenAI-compatible format)
        payload = {
            "model": agent_type,
            "messages": [],
            "max_tokens": max_tokens or settings.DEFAULT_MAX_TOKENS,
            "temperature": temperature or settings.DEFAULT_TEMPERATURE,
            "stream": False
        }

        # Add system prompt if provided
        if system_prompt:
            payload["messages"].append({
                "role": "system",
                "content": system_prompt
            })

        # Add user prompt
        payload["messages"].append({
            "role": "user",
            "content": prompt
        })

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{endpoint}/chat/completions",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=settings.INFERENCE_TIMEOUT_SECONDS)
                ) as response:

                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Inference error: {response.status} - {error_text}")
                        raise Exception(f"Inference failed: {response.status}")

                    result = await response.json()

                    # Extract response
                    response_text = result["choices"][0]["message"]["content"]
                    tokens_used = result["usage"]["total_tokens"]

                    # Calculate latency
                    latency = (datetime.utcnow() - start_time).total_seconds()

                    logger.info(
                        f"Inference complete - Agent: {agent_type}, "
                        f"Tokens: {tokens_used}, Latency: {latency:.2f}s"
                    )

                    return {
                        "response": response_text,
                        "tokens_used": tokens_used,
                        "latency": latency,
                        "agent": agent_type,
                        "timestamp": start_time.isoformat()
                    }

        except asyncio.TimeoutError:
            logger.error(f"Inference timeout for agent: {agent_type}")
            raise Exception("Inference request timed out")

        except Exception as e:
            logger.error(f"Inference error: {e}", exc_info=True)
            raise

    async def generate_streaming(
        self,
        prompt: str,
        agent_type: str,
        user_id: str,
        max_tokens: int = None,
        temperature: float = None,
        system_prompt: Optional[str] = None
    ):
        """
        Generate response with streaming (yields chunks as they arrive)

        Args:
            prompt: User query
            agent_type: Agent type
            user_id: User ID
            max_tokens: Max tokens
            temperature: Temperature
            system_prompt: System prompt

        Yields:
            Response chunks
        """

        if agent_type not in self.endpoints:
            raise ValueError(f"Unknown agent type: {agent_type}")

        endpoint = self.endpoints[agent_type]

        payload = {
            "model": agent_type,
            "messages": [],
            "max_tokens": max_tokens or settings.DEFAULT_MAX_TOKENS,
            "temperature": temperature or settings.DEFAULT_TEMPERATURE,
            "stream": True
        }

        if system_prompt:
            payload["messages"].append({
                "role": "system",
                "content": system_prompt
            })

        payload["messages"].append({
            "role": "user",
            "content": prompt
        })

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{endpoint}/chat/completions",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=settings.INFERENCE_TIMEOUT_SECONDS)
                ) as response:

                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Streaming inference error: {response.status} - {error_text}")
                        raise Exception(f"Streaming inference failed: {response.status}")

                    async for line in response.content:
                        if line:
                            yield line

        except Exception as e:
            logger.error(f"Streaming inference error: {e}")
            raise

    async def health_check(self) -> Dict:
        """Check health of all GPU services"""

        health_status = {}

        for agent_type, endpoint in self.endpoints.items():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{endpoint}/health",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        health_status[agent_type] = {
                            "status": "healthy" if response.status == 200 else "unhealthy",
                            "endpoint": endpoint
                        }
            except Exception as e:
                health_status[agent_type] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "endpoint": endpoint
                }

        return health_status

    async def get_model_info(self, agent_type: str) -> Dict:
        """
        Get model information from vLLM endpoint

        Args:
            agent_type: Agent type

        Returns:
            Model information
        """
        if agent_type not in self.endpoints:
            raise ValueError(f"Unknown agent type: {agent_type}")

        endpoint = self.endpoints[agent_type]

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{endpoint}/v1/models",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:

                    if response.status != 200:
                        return {}

                    result = await response.json()
                    return result

        except Exception as e:
            logger.error(f"Error getting model info: {e}")
            return {}
