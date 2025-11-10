"""
Analysis Model - Stores AI agent analysis results
"""

from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from database import Base


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Document reference
    document_id = Column(String, ForeignKey("documents.id"), nullable=False, index=True)

    # Agent information
    agent_type = Column(String, nullable=False, index=True)  # "contract_review", "compliance", etc.
    analysis_type = Column(String)  # "comprehensive", "risk_only", "obligations_only"

    # Analysis results
    result_text = Column(Text, nullable=False)  # Full analysis text
    result_json = Column(Text)  # Structured results as JSON

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)

    # Performance metrics
    tokens_used = Column(Integer)
    latency_seconds = Column(Float)
    chunks_analyzed = Column(Integer, default=1)
    rag_sources_used = Column(Integer, default=0)

    # Status
    status = Column(String, default="completed")  # "completed", "failed", "partial"
    error_message = Column(Text)

    # Relationships
    document = relationship("Document", back_populates="analyses")
    user = relationship("User")

    def __repr__(self):
        return f"<Analysis(id={self.id}, document_id={self.document_id}, agent={self.agent_type})>"

    @property
    def is_successful(self) -> bool:
        """Check if analysis completed successfully"""
        return self.status == "completed"

    @property
    def used_rag(self) -> bool:
        """Check if analysis used RAG (Retrieval-Augmented Generation)"""
        return self.rag_sources_used > 0
