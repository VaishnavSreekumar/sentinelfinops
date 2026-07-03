"""
CostSummary Pydantic contract definition.
Defines billing and direct monthly cost calculations.
"""
from pydantic import Field
from ai.contracts.base import ContractBase

class CostSummary(ContractBase):
    """
    Details of cost estimates and billing parameters.
    """
    current_cost: float = Field(default=0.0, ge=0.0, description="Current direct pricing cost.")
    estimated_monthly_cost: float = Field(default=0.0, ge=0.0, description="Estimated monthly billing cost.")
    projected_savings: float = Field(default=0.0, ge=0.0, description="Projected monthly cost savings.")
    currency: str = Field(default="USD", description="Billing currency classification.")
    pricing_source: str = Field(default="Generic", description="Source of cost calculation data.")
