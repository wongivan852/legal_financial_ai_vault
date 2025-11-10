"""
Document Router Agent
Classifies documents into categories and routes to appropriate agents
"""

from typing import Dict
import logging
from sqlalchemy.orm import Session

from agents.base_agent import BaseAgent
from models.document import Document

logger = logging.getLogger(__name__)


class DocumentRouterAgent(BaseAgent):
    """AI Agent for document classification and routing"""

    @property
    def agent_type(self) -> str:
        return "router"

    @property
    def system_prompt(self) -> str:
        return """You are a document classification specialist.
Classify legal documents into categories and recommend the appropriate analysis type.

Document Categories:
- contract: Legal contracts and agreements
- brief: Legal briefs and case documents
- correspondence: Letters and communications
- regulation: Regulatory documents
- financial: Financial statements and reports
- compliance: Compliance and audit documents

Analysis Recommendations:
- contract_review: For contracts and agreements
- compliance_check: For compliance-related documents
- legal_research: For case law and precedents
- general_analysis: For other documents

Provide classification with confidence scores."""

    async def process(
        self,
        document_id: str,
        user_id: str,
        db: Session
    ) -> Dict:
        """
        Classify document and recommend analysis

        Args:
            document_id: Document ID
            user_id: User ID
            db: Database session

        Returns:
            Classification and routing results
        """
        logger.info(f"Classifying document: {document_id}")

        try:
            # Get document
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise ValueError(f"Document not found: {document_id}")

            # Use first 5000 characters for classification
            doc_text = (document.text_content or "")[:5000]

            prompt = f"""Classify this document and recommend analysis type.

Document excerpt:
{doc_text}

Provide:
1. Document Category (contract, brief, correspondence, regulation, financial, compliance)
2. Confidence Score (0.0-1.0)
3. Recommended Analysis Type
4. Brief reasoning"""

            # Generate classification
            result = await self.generate_response(
                prompt=prompt,
                user_id=user_id,
                max_tokens=512,
                temperature=0.1  # Very low temperature for consistent classification
            )

            return {
                "document_id": document_id,
                "classification": result["response"],
                "tokens_used": result["tokens_used"],
                "latency": result["latency"],
                "timestamp": result["timestamp"],
                "status": "completed"
            }

        except Exception as e:
            logger.error(f"Error in document classification: {e}")
            return self.format_error(e)
