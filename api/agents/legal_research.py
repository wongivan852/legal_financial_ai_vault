"""
Legal Research Agent
Searches case law and provides legal precedents
"""

from typing import Dict
import logging

from agents.base_agent import BaseAgent
from services.vector_store import COLLECTIONS

logger = logging.getLogger(__name__)


class LegalResearchAgent(BaseAgent):
    """AI Agent for legal research and case law"""

    @property
    def agent_type(self) -> str:
        return "router"  # Uses router GPU since research is less intensive

    @property
    def system_prompt(self) -> str:
        return """You are a legal research specialist with expertise in case law and precedents.
Your role is to:
1. Analyze legal questions and identify relevant case law
2. Provide citations and precedents
3. Explain legal principles and their applications
4. Summarize relevant statutes and regulations

Provide accurate citations and explain the relevance of each precedent."""

    async def process(
        self,
        query: str,
        user_id: str,
        jurisdiction: str = "US"
    ) -> Dict:
        """
        Research legal question

        Args:
            query: Legal research query
            user_id: User ID
            jurisdiction: Legal jurisdiction (default: US)

        Returns:
            Research results with case law references
        """
        logger.info(f"Legal research query: {query[:100]}...")

        try:
            # Get relevant case law from vector database
            case_law_context = await self.get_context_from_rag(
                query=query,
                collection_name=COLLECTIONS["CASE_LAW"],
                limit=5,
                score_threshold=0.6
            )

            # Build research prompt
            prompt = f"""Legal Research Query: {query}
Jurisdiction: {jurisdiction}

{case_law_context if case_law_context else "No specific case law references available."}

Provide:
1. Relevant legal principles
2. Applicable case law and precedents
3. Statutory references
4. Summary and recommendations"""

            # Generate research
            result = await self.generate_response(
                prompt=prompt,
                user_id=user_id,
                max_tokens=3072,
                temperature=0.3
            )

            return {
                "query": query,
                "jurisdiction": jurisdiction,
                "research": result["response"],
                "case_law_references": 5 if case_law_context else 0,
                "tokens_used": result["tokens_used"],
                "latency": result["latency"],
                "timestamp": result["timestamp"],
                "status": "completed"
            }

        except Exception as e:
            logger.error(f"Error in legal research: {e}")
            return self.format_error(e)
