"""
Document Schemas - Pydantic models for document operations
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DocumentUploadResponse(BaseModel):
    """Response after document upload"""
    id: str
    filename: str
    file_size_mb: float
    file_type: str
    uploaded_at: datetime
    status: str = "processing"


class DocumentResponse(BaseModel):
    """Full document response"""
    id: str
    filename: str
    original_filename: str
    file_size_bytes: int
    file_type: str
    document_type: Optional[str]
    category: Optional[str]
    uploaded_by: str
    uploaded_at: datetime
    processed: bool
    text_extracted: bool
    vectorized: bool
    page_count: Optional[int]
    word_count: Optional[int]

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Response for document list"""
    documents: list[DocumentResponse]
    total: int
    page: int
    page_size: int


class DocumentClassifyRequest(BaseModel):
    """Request to classify document"""
    document_id: str


class DocumentMetadata(BaseModel):
    """Document metadata"""
    document_type: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[list[str]] = None
