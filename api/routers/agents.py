"""
AI Agents Router - Contract review, compliance, research endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models.user import User
from models.document import Document
from models.analysis import Analysis
from schemas.agent_schema import (
    ContractAnalysisRequest,
    ContractComparisonRequest,
    ComplianceCheckRequest,
    LegalResearchRequest,
    AgentResponse,
    AnalysisListResponse
)
from security.auth import get_current_user
from security.rbac import Permission, check_permission, check_resource_ownership
from services.audit import AuditService
from agents.contract_review import ContractReviewAgent
from agents.compliance import ComplianceAgent
from agents.legal_research import LegalResearchAgent
from agents.document_router import DocumentRouterAgent

router = APIRouter()


@router.post("/contract-review", response_model=AgentResponse)
async def analyze_contract(
    request: ContractAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyze a contract document

    Analyzes contracts for risks, obligations, and key terms
    """
    check_permission(current_user, Permission.USE_AGENTS)

    # Verify document exists and user has access
    document = db.query(Document).filter(Document.id == request.document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    check_resource_ownership(current_user, document.uploaded_by)

    try:
        # Run contract review agent
        agent = ContractReviewAgent()
        result = await agent.process(
            document_id=request.document_id,
            user_id=current_user.id,
            db=db,
            analysis_type=request.analysis_type
        )

        # Save analysis to database
        if result.get("status") == "completed":
            analysis = Analysis(
                document_id=request.document_id,
                agent_type="contract_review",
                analysis_type=request.analysis_type,
                result_text=result["analysis"],
                created_by=current_user.id,
                tokens_used=result.get("tokens_used"),
                latency_seconds=result.get("latency"),
                chunks_analyzed=result.get("chunks_analyzed", 1),
                rag_sources_used=result.get("rag_sources", 0),
                status="completed"
            )
            db.add(analysis)
            db.commit()

            # Log inference
            AuditService.log_inference(
                db=db,
                user=current_user,
                agent_type="contract_review",
                prompt=f"Analyze contract {request.document_id}",
                response=result["analysis"][:500],  # First 500 chars
                tokens_used=result.get("tokens_used", 0),
                latency=result.get("latency", 0),
                document_id=request.document_id
            )

        return AgentResponse(**result, agent_type="contract_review")

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/contract-comparison", response_model=AgentResponse)
async def compare_contracts(
    request: ContractComparisonRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Compare two contracts"""
    check_permission(current_user, Permission.USE_AGENTS)

    # Verify both documents exist and user has access
    doc1 = db.query(Document).filter(Document.id == request.document_id_1).first()
    doc2 = db.query(Document).filter(Document.id == request.document_id_2).first()

    if not doc1 or not doc2:
        raise HTTPException(status_code=404, detail="One or both documents not found")

    check_resource_ownership(current_user, doc1.uploaded_by)
    check_resource_ownership(current_user, doc2.uploaded_by)

    try:
        agent = ContractReviewAgent()
        result = await agent.compare_contracts(
            document_id_1=request.document_id_1,
            document_id_2=request.document_id_2,
            user_id=current_user.id,
            db=db
        )

        # Log inference
        if result.get("status") == "completed":
            AuditService.log_inference(
                db=db,
                user=current_user,
                agent_type="contract_review",
                prompt=f"Compare contracts {request.document_id_1} vs {request.document_id_2}",
                response=result["comparison"][:500],
                tokens_used=result.get("tokens_used", 0),
                latency=result.get("latency", 0)
            )

        return AgentResponse(
            status=result.get("status", "completed"),
            agent_type="contract_review",
            analysis=result.get("comparison"),
            tokens_used=result.get("tokens_used"),
            latency=result.get("latency"),
            timestamp=result.get("timestamp")
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/compliance-check", response_model=AgentResponse)
async def check_compliance(
    request: ComplianceCheckRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check document for compliance issues

    Analyzes documents against regulatory requirements
    """
    check_permission(current_user, Permission.USE_AGENTS)

    # Verify document exists
    document = db.query(Document).filter(Document.id == request.document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    check_resource_ownership(current_user, document.uploaded_by)

    try:
        # Run compliance agent
        agent = ComplianceAgent()
        result = await agent.process(
            document_id=request.document_id,
            user_id=current_user.id,
            db=db,
            regulations=request.regulations
        )

        # Save analysis
        if result.get("status") == "completed":
            analysis = Analysis(
                document_id=request.document_id,
                agent_type="compliance",
                result_text=result["analysis"],
                created_by=current_user.id,
                tokens_used=result.get("tokens_used"),
                latency_seconds=result.get("latency"),
                status="completed"
            )
            db.add(analysis)
            db.commit()

            # Log inference
            AuditService.log_inference(
                db=db,
                user=current_user,
                agent_type="compliance",
                prompt=f"Compliance check {request.document_id}",
                response=result["analysis"][:500],
                tokens_used=result.get("tokens_used", 0),
                latency=result.get("latency", 0),
                document_id=request.document_id
            )

        return AgentResponse(**result, agent_type="compliance")

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/legal-research", response_model=AgentResponse)
async def research_legal_question(
    request: LegalResearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Conduct legal research

    Searches case law and provides legal precedents
    """
    check_permission(current_user, Permission.USE_AGENTS)

    try:
        # Run legal research agent
        agent = LegalResearchAgent()
        result = await agent.process(
            query=request.query,
            user_id=current_user.id,
            jurisdiction=request.jurisdiction
        )

        # Log inference
        if result.get("status") == "completed":
            AuditService.log_inference(
                db=db,
                user=current_user,
                agent_type="legal_research",
                prompt=request.query,
                response=result["research"][:500],
                tokens_used=result.get("tokens_used", 0),
                latency=result.get("latency", 0)
            )

        return AgentResponse(
            status=result.get("status", "completed"),
            agent_type="legal_research",
            analysis=result.get("research"),
            tokens_used=result.get("tokens_used"),
            latency=result.get("latency"),
            timestamp=result.get("timestamp")
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/classify-document", response_model=AgentResponse)
async def classify_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Classify document type

    Determines document category and recommends appropriate analysis
    """
    check_permission(current_user, Permission.USE_AGENTS)

    # Verify document exists
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    check_resource_ownership(current_user, document.uploaded_by)

    try:
        # Run document router agent
        agent = DocumentRouterAgent()
        result = await agent.process(
            document_id=document_id,
            user_id=current_user.id,
            db=db
        )

        # Log inference
        if result.get("status") == "completed":
            AuditService.log_inference(
                db=db,
                user=current_user,
                agent_type="document_router",
                prompt=f"Classify document {document_id}",
                response=result["classification"][:500],
                tokens_used=result.get("tokens_used", 0),
                latency=result.get("latency", 0),
                document_id=document_id
            )

        return AgentResponse(
            status=result.get("status", "completed"),
            agent_type="document_router",
            analysis=result.get("classification"),
            tokens_used=result.get("tokens_used"),
            latency=result.get("latency"),
            timestamp=result.get("timestamp")
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/analyses/{document_id}", response_model=AnalysisListResponse)
async def get_document_analyses(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all analyses for a document"""
    check_permission(current_user, Permission.VIEW_AGENT_RESULTS)

    # Verify document exists and user has access
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    check_resource_ownership(current_user, document.uploaded_by)

    # Get all analyses
    analyses = db.query(Analysis).filter(
        Analysis.document_id == document_id
    ).order_by(Analysis.created_at.desc()).all()

    return AnalysisListResponse(
        analyses=[
            {
                "id": a.id,
                "agent_type": a.agent_type,
                "analysis_type": a.analysis_type,
                "created_at": a.created_at.isoformat(),
                "status": a.status,
                "tokens_used": a.tokens_used
            }
            for a in analyses
        ],
        total=len(analyses)
    )


@router.get("/")
async def list_available_agents():
    """List available AI agents"""
    return {
        "agents": [
            {
                "name": "contract_review",
                "description": "Analyzes contracts for risks, obligations, and key terms",
                "endpoint": "/api/agents/contract-review",
                "gpu": "0-1",
                "model": "Qwen2.5-14B-Instruct"
            },
            {
                "name": "compliance",
                "description": "Checks documents for regulatory compliance",
                "endpoint": "/api/agents/compliance-check",
                "gpu": "2",
                "model": "Qwen2.5-14B-Instruct"
            },
            {
                "name": "document_router",
                "description": "Classifies documents and recommends analysis type",
                "endpoint": "/api/agents/classify-document",
                "gpu": "3-4",
                "model": "Qwen2.5-7B-Instruct"
            },
            {
                "name": "legal_research",
                "description": "Searches case law and provides legal precedents",
                "endpoint": "/api/agents/legal-research",
                "gpu": "3-4",
                "model": "Qwen2.5-7B-Instruct"
            }
        ]
    }
