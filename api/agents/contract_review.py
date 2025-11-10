"""
Contract Review Agent
Analyzes contracts for risks, obligations, and key terms
"""

from typing import Dict, Optional
import logging
from sqlalchemy.orm import Session

from agents.base_agent import BaseAgent
from services.document_processor import DocumentProcessor
from services.vector_store import COLLECTIONS
from models.document import Document

logger = logging.getLogger(__name__)


class ContractReviewAgent(BaseAgent):
    """AI Agent for contract analysis"""

    @property
    def agent_type(self) -> str:
        return "contract_review"

    @property
    def system_prompt(self) -> str:
        return """You are an expert legal AI assistant specializing in contract review.
Your role is to analyze contracts and identify:
1. Key obligations and deadlines
2. Potential legal risks or unfavorable terms
3. Missing clauses or ambiguous language
4. Recommended actions or clarifications

Provide clear, structured analysis with specific clause references.
Use professional legal terminology but remain accessible."""

    @property
    def default_temperature(self) -> float:
        return 0.2  # Low temperature for consistency in contract analysis

    async def process(
        self,
        document_id: str,
        user_id: str,
        db: Session,
        analysis_type: str = "comprehensive"
    ) -> Dict:
        """
        Analyze a contract document

        Args:
            document_id: ID of uploaded document
            user_id: User requesting analysis
            db: Database session
            analysis_type: "comprehensive" | "risk_only" | "obligations_only"

        Returns:
            Dict with analysis results
        """
        logger.info(f"Starting contract analysis - Doc: {document_id}, Type: {analysis_type}")

        try:
            # Validate input
            if analysis_type not in ["comprehensive", "risk_only", "obligations_only"]:
                raise ValueError(f"Invalid analysis type: {analysis_type}")

            # 1. Retrieve document
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise ValueError(f"Document not found: {document_id}")

            # 2. Get document text
            if document.text_content:
                doc_text = document.text_content
            else:
                # Extract text if not already done
                doc_processor = DocumentProcessor()
                doc_text = doc_processor.extract_text(document.storage_path, document.file_type)

                # Update document with extracted text
                document.text_content = doc_text
                document.text_extracted = True
                document.word_count = doc_processor.count_words(doc_text)
                db.commit()

            # 3. Check document length and chunk if necessary
            if len(doc_text) > 30000:  # ~7500 tokens
                chunks = DocumentProcessor.chunk_document(doc_text, chunk_size=20000)
                logger.info(f"Document chunked into {len(chunks)} parts")
            else:
                chunks = [doc_text]

            # 4. Retrieve similar contract clauses from vector database (RAG)
            rag_context = await self.get_context_from_rag(
                query=doc_text[:1000],  # Use first 1000 chars for similarity
                collection_name=COLLECTIONS["LEGAL_CONTRACTS"],
                limit=3,
                score_threshold=0.7
            )

            # 5. Build analysis prompt
            prompt = self._build_analysis_prompt(
                document_text=chunks[0],  # Start with first chunk
                analysis_type=analysis_type,
                rag_context=rag_context
            )

            # 6. Run inference
            result = await self.generate_response(
                prompt=prompt,
                user_id=user_id
            )

            # 7. Structure results
            analysis = {
                "document_id": document_id,
                "analysis_type": analysis_type,
                "analysis": result["response"],
                "tokens_used": result["tokens_used"],
                "latency": result["latency"],
                "timestamp": result["timestamp"],
                "chunks_analyzed": len(chunks),
                "rag_sources": 3 if rag_context else 0,
                "status": "completed"
            }

            # 8. If multi-chunk, analyze remaining chunks
            if len(chunks) > 1:
                additional_analyses = []
                for i, chunk in enumerate(chunks[1:], start=2):
                    logger.info(f"Analyzing chunk {i}/{len(chunks)}")
                    chunk_result = await self._analyze_chunk(chunk, user_id)
                    additional_analyses.append(chunk_result)

                analysis["additional_sections"] = additional_analyses

            logger.info(f"Contract analysis complete - Doc: {document_id}")
            return analysis

        except Exception as e:
            logger.error(f"Error in contract analysis: {e}", exc_info=True)
            return self.format_error(e)

    def _build_analysis_prompt(
        self,
        document_text: str,
        analysis_type: str,
        rag_context: Optional[str] = None
    ) -> str:
        """Build the analysis prompt with context"""

        prompt_parts = []

        # Add RAG context if available
        if rag_context:
            prompt_parts.append("### Reference Clauses (from similar contracts):")
            prompt_parts.append(rag_context)
            prompt_parts.append("\n---\n")

        # Add main document
        prompt_parts.append("### Contract to Analyze:")
        prompt_parts.append(document_text)
        prompt_parts.append("\n---\n")

        # Add specific instructions based on analysis type
        if analysis_type == "risk_only":
            prompt_parts.append("\n### Focus your analysis on identifying legal risks and unfavorable terms.")
        elif analysis_type == "obligations_only":
            prompt_parts.append("\n### Focus your analysis on listing all obligations and deadlines.")
        else:
            prompt_parts.append("\n### Provide a comprehensive analysis covering risks, obligations, and recommendations.")

        return "\n".join(prompt_parts)

    async def _analyze_chunk(self, chunk: str, user_id: str) -> Dict:
        """Analyze a single document chunk"""

        result = await self.generate_response(
            prompt=f"Continue analyzing this contract section:\n\n{chunk}",
            user_id=user_id,
            max_tokens=2048
        )

        return {
            "analysis": result["response"],
            "tokens_used": result["tokens_used"]
        }

    async def compare_contracts(
        self,
        document_id_1: str,
        document_id_2: str,
        user_id: str,
        db: Session
    ) -> Dict:
        """Compare two contracts and highlight differences"""

        logger.info(f"Comparing contracts: {document_id_1} vs {document_id_2}")

        try:
            # Retrieve both documents
            doc1 = db.query(Document).filter(Document.id == document_id_1).first()
            doc2 = db.query(Document).filter(Document.id == document_id_2).first()

            if not doc1 or not doc2:
                raise ValueError("One or both documents not found")

            # Get document texts
            doc1_text = doc1.text_content or ""
            doc2_text = doc2.text_content or ""

            # Build comparison prompt
            prompt = f"""Compare these two contracts and identify:
1. Key differences in terms and conditions
2. Differences in obligations or liabilities
3. Which contract is more favorable and why

### Contract A:
{doc1_text[:15000]}

### Contract B:
{doc2_text[:15000]}

Provide a detailed comparison with specific clause references."""

            result = await self.generate_response(
                prompt=prompt,
                user_id=user_id,
                max_tokens=4096,
                temperature=0.3
            )

            return {
                "document_1": document_id_1,
                "document_2": document_id_2,
                "comparison": result["response"],
                "tokens_used": result["tokens_used"],
                "timestamp": result["timestamp"],
                "status": "completed"
            }

        except Exception as e:
            logger.error(f"Error comparing contracts: {e}")
            return self.format_error(e)

    async def extract_key_terms(
        self,
        document_id: str,
        user_id: str,
        db: Session
    ) -> Dict:
        """Extract key terms and conditions from contract"""

        logger.info(f"Extracting key terms from document: {document_id}")

        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise ValueError(f"Document not found: {document_id}")

            doc_text = document.text_content or ""

            prompt = f"""Extract and summarize the following key terms from this contract:
1. Parties involved
2. Contract duration and dates
3. Payment terms
4. Termination clauses
5. Liability limitations
6. Governing law and jurisdiction

Contract:
{doc_text[:20000]}

Provide a structured summary with clear sections."""

            result = await self.generate_response(
                prompt=prompt,
                user_id=user_id,
                max_tokens=2048,
                temperature=0.2
            )

            return {
                "document_id": document_id,
                "key_terms": result["response"],
                "tokens_used": result["tokens_used"],
                "timestamp": result["timestamp"],
                "status": "completed"
            }

        except Exception as e:
            logger.error(f"Error extracting key terms: {e}")
            return self.format_error(e)
