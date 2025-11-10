"""
Compliance Monitoring Agent
Checks documents against regulatory requirements
"""

from typing import Dict, List
import logging
from sqlalchemy.orm import Session

from agents.base_agent import BaseAgent
from models.document import Document

logger = logging.getLogger(__name__)


class ComplianceAgent(BaseAgent):
    """AI Agent for compliance checking"""

    @property
    def agent_type(self) -> str:
        return "compliance"

    @property
    def system_prompt(self) -> str:
        return """You are an expert compliance analyst specializing in legal and financial regulations.
Your role is to:
1. Identify regulatory compliance issues
2. Assess risks related to non-compliance
3. Recommend corrective actions
4. Reference relevant regulations and standards

Focus on major regulations like GDPR, SOX, HIPAA, and industry-specific requirements.
Provide clear risk scores and actionable recommendations."""

    async def process(
        self,
        document_id: str,
        user_id: str,
        db: Session,
        regulations: List[str] = None
    ) -> Dict:
        """
        Check document for compliance issues

        Args:
            document_id: Document ID
            user_id: User ID
            db: Database session
            regulations: List of regulations to check (e.g., ["GDPR", "SOX"])

        Returns:
            Compliance analysis results
        """
        logger.info(f"Starting compliance check - Doc: {document_id}")

        try:
            # Get document
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise ValueError(f"Document not found: {document_id}")

            doc_text = document.text_content or ""

            # Build prompt
            regulations_str = ", ".join(regulations) if regulations else "all major regulations"
            prompt = f"""Analyze this document for compliance with {regulations_str}.

Document:
{doc_text[:20000]}

Provide:
1. Compliance Risk Score (1-10, where 10 is highest risk)
2. Specific compliance issues identified
3. Relevant regulation references
4. Recommended corrective actions"""

            # Generate analysis
            result = await self.generate_response(
                prompt=prompt,
                user_id=user_id,
                max_tokens=3072,
                temperature=0.2
            )

            return {
                "document_id": document_id,
                "regulations_checked": regulations or ["general"],
                "analysis": result["response"],
                "tokens_used": result["tokens_used"],
                "latency": result["latency"],
                "timestamp": result["timestamp"],
                "status": "completed"
            }

        except Exception as e:
            logger.error(f"Error in compliance check: {e}")
            return self.format_error(e)
