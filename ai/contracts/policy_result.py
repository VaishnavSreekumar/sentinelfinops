"""
PolicyValidationResult governance validation result schemas.
Records output checks performed by the deterministic rules engine firewall.
"""
from typing import List, Optional, Literal
from pydantic import Field
from ai.contracts.base import ContractBase
from ai.contracts.enums import PolicyValidationStatus

class PolicyValidationResult(ContractBase):
    """
    Outcome schema log for deterministic validation policy blocks.
    """
    schema_version: Literal["1.0.0"] = "1.0.0"
    status: PolicyValidationStatus = Field(..., description="Validation status gate check.")
    rule_name: str = Field(..., min_length=1, description="Triggered validator rule label.")
    severity: str = Field(..., min_length=1, description="Configured rule action severity.")
    violations: List[str] = Field(default_factory=list, description="Violations strings list.")
    passed_rules: List[str] = Field(default_factory=list, description="Rules checks evaluated and passed.")
    failed_rules: List[str] = Field(default_factory=list, description="Rules checks evaluated and failed.")
    timestamp: str = Field(..., min_length=1, description="ISO-8601 check timestamp.")
