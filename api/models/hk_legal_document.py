"""
Hong Kong Legal Document Model
Stores Hong Kong legislation chapters and instruments
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from database import Base


class HKLegalDocument(Base):
    """Model for Hong Kong Legal Documents (Legislation and Instruments)"""

    __tablename__ = "hk_legal_documents"

    # Primary identifiers
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Document identification (from XML metadata)
    doc_number = Column(String, nullable=False, index=True)  # e.g., "A101", "Cap. 1"
    doc_name = Column(String, nullable=False, index=True)
    doc_type = Column(String, nullable=False, index=True)  # "instrument" or "ordinance"
    doc_status = Column(String)  # "In effect", "Repealed", etc.

    # Dublin Core metadata
    identifier = Column(String, unique=True)  # /hk/capA101!en
    language = Column(String, index=True)  # "en", "zh-Hant", "zh-Hans"
    subject = Column(String)  # "legislation"
    publisher = Column(String)  # "DoJ"
    rights = Column(String)
    effective_date = Column(DateTime)  # Converted from dc:date

    # Document content
    title = Column(Text)
    preamble = Column(Text)
    full_text = Column(Text, nullable=False)
    word_count = Column(Integer)

    # Document structure (stored as JSON)
    structure = Column(JSON)  # Table of contents, chapters, sections hierarchy
    sections = Column(JSON)   # Array of section objects
    chapters = Column(JSON)   # Array of chapter objects

    # Processing metadata
    source_file = Column(String, nullable=False)  # Original XML file path
    imported_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed = Column(Boolean, default=False)
    vectorized = Column(Boolean, default=False)

    # Vector database reference
    vector_collection = Column(String)  # "hk_legislation"
    vector_ids = Column(JSON)  # Array of vector IDs (for chunked documents)

    # Search optimization
    search_keywords = Column(Text)  # Extracted keywords for full-text search

    def __repr__(self):
        return f"<HKLegalDocument(doc_number={self.doc_number}, type={self.doc_type}, lang={self.language})>"

    @property
    def display_name(self) -> str:
        """Human-readable document name"""
        return f"{self.doc_name} ({self.doc_number})"

    @property
    def is_bilingual_available(self) -> bool:
        """Check if document has translations"""
        # This would need a query to check for other language versions
        return True  # Placeholder

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'doc_number': self.doc_number,
            'doc_name': self.doc_name,
            'doc_type': self.doc_type,
            'doc_status': self.doc_status,
            'identifier': self.identifier,
            'language': self.language,
            'title': self.title,
            'effective_date': self.effective_date.isoformat() if self.effective_date else None,
            'word_count': self.word_count,
            'imported_at': self.imported_at.isoformat(),
            'processed': self.processed,
            'vectorized': self.vectorized
        }


class HKLegalSection(Base):
    """
    Individual sections from HK legal documents
    For more granular searching and retrieval
    """

    __tablename__ = "hk_legal_sections"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Parent document reference
    document_id = Column(String, nullable=False, index=True)
    doc_number = Column(String, nullable=False, index=True)

    # Section identification
    section_id = Column(String, nullable=False)  # XML element ID
    section_number = Column(String, index=True)
    section_heading = Column(String)

    # Hierarchy
    chapter_id = Column(String)
    chapter_heading = Column(String)
    parent_section_id = Column(String)

    # Content
    content = Column(Text, nullable=False)
    word_count = Column(Integer)

    # Subsections (stored as JSON)
    subsections = Column(JSON)

    # Vector reference
    vector_id = Column(String)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<HKLegalSection(doc={self.doc_number}, section={self.section_number})>"

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'document_id': self.document_id,
            'doc_number': self.doc_number,
            'section_number': self.section_number,
            'section_heading': self.section_heading,
            'chapter_heading': self.chapter_heading,
            'content': self.content,
            'word_count': self.word_count
        }
