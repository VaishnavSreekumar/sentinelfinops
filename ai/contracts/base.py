"""
Base contract class defining default configuration guarantees.
Ensures validation settings are consistent across the platform.
"""
from pydantic import BaseModel, ConfigDict

class ContractBase(BaseModel):
    """
    Base configuration class for all SentinelFinOps AI contracts.
    Enforces immutability, strict type checking, and forbids extra fields.
    """
    model_config = ConfigDict(
        frozen=True,
        strict=True,
        extra="forbid",
        validate_assignment=False
    )
