"""
Recommendation contract models for optimizer reasoning engines.
Provides stable definitions for optimization feedback structures.
"""
from datetime import datetime
from typing import Dict, List, Any, Literal
from uuid import UUID, uuid4
from pydantic import Field
from ai.contracts.base import ContractBase
from ai.contracts.enums import RecommendedAction

class RecommendationBase(ContractBase):
    """
    Base contract for reasoning output results from model providers.
    """
    recommendation_id: UUID = Field(default_factory=uuid4, description="Unique tracking identifier.")
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z", description="ISO-8601 generation date time.")
    model: str = Field(..., min_length=1, description="Provider model ID tag.")
    prompt_version: str = Field(..., min_length=1, description="Active prompt template version.")
    resource_id: str = Field(..., min_length=1, description="Resource identifier.")
    recommended_action: RecommendedAction = Field(..., description="Calculated action proposed.")
    reasoning: str = Field(..., min_length=1, description="Reasoning narrative context.")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Model confidence score.")
    risk_assessment: Dict[str, Any] = Field(..., description="Identified risk parameters.")
    projected_monthly_savings: float = Field(..., ge=0.0, description="Savings estimation.")
    explanation_steps: List[str] = Field(default_factory=list, description="Reasoning checkpoints list.")
    citations: List[str] = Field(default_factory=list, description="Evidence metric citations.")
    confidence_reason: str = Field(..., min_length=1, description="Why confidence rating was set.")
    assumptions: List[str] = Field(default_factory=list, description="Model contextual assumptions.")

class RecommendationV1(RecommendationBase):
    """
    Recommendation version 1 interface.
    """
    schema_version: Literal["1.0.0"] = "1.0.0"

class RecommendationV2(RecommendationBase):
    """
    Recommendation version 2 interface supporting alternative configurations.
    """
    schema_version: Literal["2.0.0"] = "2.0.0"
    alternative_actions: List[str] = Field(default_factory=list, description="Secondary alternatives choices.")
    operational_impact: str = Field(default="NONE", description="Operational impact explanation.")
