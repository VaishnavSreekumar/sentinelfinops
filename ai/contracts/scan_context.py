"""
ScanContext Pydantic contract definition.
Data payload container aggregating raw metadata and metrics before context mapping.
"""
from typing import Dict, Any, Literal
from uuid import UUID, uuid4
from pydantic import Field
from ai.contracts.base import ContractBase
from ai.contracts.enums import ResourceType
from ai.contracts.metrics_summary import MetricsSummary
from ai.contracts.cost_summary import CostSummary
from ai.contracts.owner_info import OwnerInfo
from ai.contracts.history_summary import HistorySummary

class ScanContext(ContractBase):
    """
    Payload containing metadata and metrics generated during resource scanning.
    """
    schema_version: Literal["1.0.0"] = "1.0.0"
    execution_id: UUID = Field(default_factory=uuid4, description="Unique identifier for the current scan execution.")
    resource_id: str = Field(..., min_length=1, description="Resource identifier under analysis.")
    resource_type: ResourceType = Field(..., description="Target category of the resource.")
    raw_resource: Dict[str, Any] = Field(default_factory=dict, description="Raw dictionary returned by cloud providers.")
    metrics: MetricsSummary = Field(default_factory=MetricsSummary, description="Aggregated metric readings.")
    cost_summary: CostSummary = Field(default_factory=CostSummary, description="Direct billing parameters.")
    owner_info: OwnerInfo = Field(default_factory=OwnerInfo, description="User or team attribution details.")
    history_summary: HistorySummary = Field(default_factory=HistorySummary, description="Remediation alert state logs.")
    account_id: str = Field(..., min_length=1, description="Account identifier containing the resource.")
    account_name: str = Field(..., min_length=1, description="Name label of the target account.")
    region: str = Field(..., min_length=1, description="Target cloud deployment region.")
