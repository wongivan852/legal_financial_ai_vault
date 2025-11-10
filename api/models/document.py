"""
Document Model - Represents uploaded legal documents
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, Boolean, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_size_bytes = Column(BigInteger, nullable=False)
    file_type = Column(String, nullable=False)  # .pdf, .docx, etc.
    mime_type = Column(String)

    # Storage
    storage_path = Column(String, nullable=False)
    encrypted = Column(Boolean, default=True)

    # Metadata
    uploaded_by = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Document classification
    document_type = Column(String, index=True)  # "contract", "brief", "correspondence", etc.
    category = Column(String)  # "M&A", "employment", "real_estate", etc.

    # Processing status
    processed = Column(Boolean, default=False, index=True)
    text_extracted = Column(Boolean, default=False)
    vectorized = Column(Boolean, default=False)

    # Extracted content
    text_content = Column(Text)  # Full text extraction
    page_count = Column(Integer)
    word_count = Column(Integer)

    # Vector database reference
    vector_collection = Column(String)
    vector_id = Column(String)

    # Metadata JSON
    metadata_json = Column(Text)  # Additional metadata as JSON

    # Relationships
    user = relationship("User", back_populates="documents")
    analyses = relationship("Analysis", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document(id={self.id}, filename={self.filename}, type={self.document_type})>"

    @property
    def file_size_mb(self) -> float:
        """Get file size in megabytes"""
        return self.file_size_bytes / (1024 * 1024)

    @property
    def is_fully_processed(self) -> bool:
        """Check if document has been fully processed"""
        return self.processed and self.text_extracted and self.vectorized
