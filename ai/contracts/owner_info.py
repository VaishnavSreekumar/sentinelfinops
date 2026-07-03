"""
OwnerInfo Pydantic contract definition.
Structures owner tags and attribution levels.
"""
from typing import Optional
from pydantic import Field
from ai.contracts.base import ContractBase

class OwnerInfo(ContractBase):
    """
    Ownership and attribution parameters.
    """
    owner_arn: Optional[str] = Field(default=None, description="Attributed owner IAM user/role ARN.")
    team: Optional[str] = Field(default=None, description="Assigned owner team identifier.")
    email: Optional[str] = Field(default=None, description="Direct owner contact email address.")
    cloudtrail_actor: Optional[str] = Field(default=None, description="AWS principal that launched the resource.")
    confidence: str = Field(default="LOW", description="Confidence level of owner attribution.")
