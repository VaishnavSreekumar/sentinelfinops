"""
Telemetry telemetry logs logging contract.
Enforces cost and latency monitoring metadata on AI gateway requests.
"""
from typing import Literal
from uuid import UUID, uuid4
from pydantic import Field
from ai.contracts.base import ContractBase
from ai.contracts.enums import PolicyValidationStatus

class TelemetryRecord(ContractBase):
    """
    Schema log for query transaction telemetry logs.
    """
    schema_version: Literal["1.0.0"] = "1.0.0"
    request_id: UUID = Field(default_factory=uuid4, description="Gateway transaction request ID.")
    execution_id: UUID = Field(default_factory=uuid4, description="Platform workflow execution identifier.")
    resource_id: str = Field(..., min_length=1, description="Evaluated resource ID.")
    timestamp: str = Field(..., min_length=1, description="ISO-8601 creation date.")
    provider_name: str = Field(..., min_length=1, description="Gateway provider target (e.g. bedrock, openai).")
    provider_model: str = Field(..., min_length=1, description="Specific model invoked.")
    prompt_name: str = Field(..., min_length=1, description="System prompt template ID.")
    prompt_version: str = Field(..., min_length=1, description="Template version tag.")
    cache_hit: bool = Field(..., description="Flag indicating if query hit cache.")
    latency_seconds: float = Field(..., ge=0.0, description="Incurred execution duration.")
    input_tokens: int = Field(..., ge=0, description="Tokens consumed on request prompts.")
    output_tokens: int = Field(..., ge=0, description="Tokens generated on output.")
    calculated_cost: float = Field(..., ge=0.0, description="Calculated billing cost.")
    retry_attempts: int = Field(default=0, ge=0, description="Gateway retry count.")
    validation_status: PolicyValidationStatus = Field(..., description="Validation outcome state.")
