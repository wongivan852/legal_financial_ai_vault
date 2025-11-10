"""
Agent Schemas - Pydantic models for AI agent operations
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class ContractAnalysisRequest(BaseModel):
    """Request for contract analysis"""
    document_id: str
    analysis_type: str = Field(default="comprehensive", pattern="^(comprehensive|risk_only|obligations_only)$")


class ContractComparisonRequest(BaseModel):
    """Request to compare two contracts"""
    document_id_1: str
    document_id_2: str


class ComplianceCheckRequest(BaseModel):
    """Request for compliance check"""
    document_id: str
    regulations: Optional[List[str]] = None


class LegalResearchRequest(BaseModel):
    """Request for legal research"""
    query: str = Field(..., min_length=10, max_length=2000)
    jurisdiction: str = "US"


class AgentResponse(BaseModel):
    """Generic agent response"""
    status: str
    agent_type: str
    analysis: Optional[str] = None
    tokens_used: Optional[int] = None
    latency: Optional[float] = None
    timestamp: Optional[str] = None
    error_message: Optional[str] = None


class AnalysisListResponse(BaseModel):
    """List of analyses"""
    analyses: list
    total: int
