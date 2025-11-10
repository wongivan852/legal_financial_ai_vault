"""
Document Management Router - Upload, list, delete documents
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from pathlib import Path
import uuid
import shutil

from database import get_db
from models.user import User
from models.document import Document
from schemas.document_schema import DocumentUploadResponse, DocumentResponse, DocumentListResponse
from security.auth import get_current_user
from security.rbac import Permission, check_permission, check_resource_ownership
from security.encryption import encryption_service, hash_file
from services.audit import AuditService
from services.document_processor import DocumentProcessor
from services.embedding import EmbeddingService
from services.vector_store import VectorStoreService, COLLECTIONS
from config import settings

router = APIRouter()


def process_document_background(document_id: str, file_path: str, file_type: str):
    """Background task to process document"""
    from database import SessionLocal

    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return

        # Extract text
        processor = DocumentProcessor()
        text = processor.extract_text(file_path, file_type)

        # Update document
        document.text_content = text
        document.text_extracted = True
        document.word_count = processor.count_words(text)

        if file_type == '.pdf':
            document.page_count = processor.count_pages_pdf(file_path)

        # Generate embedding and store in vector database
        embedding_service = EmbeddingService()
        vector_store = VectorStoreService()

        # Use first 5000 chars for embedding
        embedding = embedding_service.generate_embedding(text[:5000])

        # Store in vector database
        vector_id = vector_store.add_document(
            collection_name=COLLECTIONS["LEGAL_DOCUMENTS"],
            document_id=document_id,
            text=text[:5000],
            embedding=embedding,
            metadata={
                "filename": document.filename,
                "document_type": document.document_type,
                "uploaded_by": document.uploaded_by
            }
        )

        document.vectorized = True
        document.vector_collection = COLLECTIONS["LEGAL_DOCUMENTS"]
        document.vector_id = vector_id
        document.processed = True

        db.commit()

    except Exception as e:
        print(f"Error processing document: {e}")
        document.processed = False
        db.commit()
    finally:
        db.close()


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a document

    Requires: Analyst or Admin role
    """
    # Check permission
    check_permission(current_user, Permission.UPLOAD_DOCUMENTS)

    # Validate file type
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file_ext} not allowed. Allowed types: {settings.ALLOWED_FILE_TYPES}"
        )

    # Check file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Seek back to start

    max_size_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE_MB}MB"
        )

    # Create document record
    document_id = str(uuid.uuid4())
    filename = f"{document_id}{file_ext}"

    # Create user directory if not exists
    user_dir = Path(settings.DOCUMENT_STORAGE_PATH) / current_user.id
    user_dir.mkdir(parents=True, exist_ok=True)

    # Save file temporarily
    temp_path = user_dir / f"temp_{filename}"
    encrypted_path = user_dir / f"{filename}.enc"

    try:
        # Save uploaded file
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Get file hash
        file_hash = hash_file(temp_path)

        # Encrypt file
        encryption_service.encrypt_file(temp_path, encrypted_path)

        # Delete temp file
        temp_path.unlink()

        # Create database record
        document = Document(
            id=document_id,
            filename=filename,
            original_filename=file.filename,
            file_size_bytes=file_size,
            file_type=file_ext,
            mime_type=file.content_type,
            storage_path=str(encrypted_path),
            encrypted=True,
            uploaded_by=current_user.id
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        # Log upload
        AuditService.log_document_action(
            db=db,
            user=current_user,
            action_type="upload",
            document_id=document_id,
            metadata={
                "filename": file.filename,
                "size_mb": round(file_size / (1024 * 1024), 2),
                "file_hash": file_hash
            }
        )

        # Schedule background processing
        background_tasks.add_task(
            process_document_background,
            document_id,
            str(temp_path),  # Will re-decrypt in background
            file_ext
        )

        return DocumentUploadResponse(
            id=document.id,
            filename=document.original_filename,
            file_size_mb=document.file_size_bytes / (1024 * 1024),
            file_type=document.file_type,
            uploaded_at=document.uploaded_at,
            status="processing"
        )

    except Exception as e:
        # Cleanup on error
        if temp_path.exists():
            temp_path.unlink()
        if encrypted_path.exists():
            encrypted_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading document: {str(e)}"
        )


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    page: int = 1,
    page_size: int = 50,
    document_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List documents

    Users see only their own documents unless they are admins
    """
    check_permission(current_user, Permission.VIEW_DOCUMENTS)

    # Build query
    query = db.query(Document)

    # Filter by user unless admin
    if not current_user.is_admin:
        query = query.filter(Document.uploaded_by == current_user.id)

    # Filter by document type if provided
    if document_type:
        query = query.filter(Document.document_type == document_type)

    # Get total count
    total = query.count()

    # Paginate
    offset = (page - 1) * page_size
    documents = query.order_by(Document.uploaded_at.desc()).offset(offset).limit(page_size).all()

    return DocumentListResponse(
        documents=[DocumentResponse.from_orm(doc) for doc in documents],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get document details"""
    check_permission(current_user, Permission.VIEW_DOCUMENTS)

    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Check ownership unless admin
    check_resource_ownership(current_user, document.uploaded_by)

    return DocumentResponse.from_orm(document)


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a document"""
    check_permission(current_user, Permission.DELETE_DOCUMENTS)

    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Check ownership
    check_resource_ownership(current_user, document.uploaded_by)

    try:
        # Delete physical file
        file_path = Path(document.storage_path)
        if file_path.exists():
            file_path.unlink()

        # Delete from vector database
        if document.vectorized and document.vector_collection:
            vector_store = VectorStoreService()
            vector_store.delete_document(document.vector_collection, document_id)

        # Delete database record
        db.delete(document)
        db.commit()

        # Log deletion
        AuditService.log_document_action(
            db=db,
            user=current_user,
            action_type="delete",
            document_id=document_id
        )

        return {"message": "Document deleted successfully"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting document: {str(e)}"
        )


@router.get("/{document_id}/text")
async def get_document_text(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get extracted text from document"""
    check_permission(current_user, Permission.VIEW_DOCUMENTS)

    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    check_resource_ownership(current_user, document.uploaded_by)

    if not document.text_extracted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text not yet extracted from document"
        )

    return {
        "document_id": document_id,
        "text": document.text_content,
        "word_count": document.word_count,
        "page_count": document.page_count
    }
