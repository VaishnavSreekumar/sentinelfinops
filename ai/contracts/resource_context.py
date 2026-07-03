"""
ResourceContext configuration contract model.
Standardizes metadata parameters across different resource scanning engines.
"""
from typing import Dict, Any, Literal
from pydantic import Field
from ai.contracts.base import ContractBase
from ai.contracts.enums import CloudProvider, ResourceType

class ResourceContextV1(ContractBase):
    """
    Canonical representation of a cloud resource context for reasoning.
    """
    schema_version: Literal["1.0.0"] = "1.0.0"
    resource_id: str = Field(..., min_length=1, description="Unique ID of the resource.")
    resource_type: ResourceType = Field(..., description="Target type of resource.")
    cloud_provider: CloudProvider = Field(default=CloudProvider.AWS, description="Cloud provider vendor.")
    account_id: str = Field(..., min_length=1, description="Target Cloud Account ID.")
    account_name: str = Field(..., min_length=1, description="Cloud account readable label.")
    region: str = Field(..., min_length=1, description="Cloud provider region.")
    state: str = Field(..., min_length=1, description="Resource lifecycle state.")
    tags: Dict[str, str] = Field(default_factory=dict, description="Metadata tags list.")
    metrics_summary: Dict[str, Any] = Field(default_factory=dict, description="Aggregated metric values.")
    lifecycle_details: Dict[str, Any] = Field(default_factory=dict, description="Launch parameters and config attributes.")
    history_summary: Dict[str, Any] = Field(default_factory=dict, description="Historical alert metadata logs.")
