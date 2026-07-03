"""
HistorySummary Pydantic contract definition.
Details alerts history, manual overrides, and prior actions.
"""
from typing import Optional
from pydantic import Field
from ai.contracts.base import ContractBase

class HistorySummary(ContractBase):
    """
    Remediation state, alert logs, and execution histories.
    """
    alert_state: str = Field(default="NEW", description="Active alert lifecycle state (NEW, ALERTED, etc).")
    alert_count_30_days: int = Field(default=0, ge=0, description="Number of times alerts fired in 30 days.")
    manual_snoozes_30_days: int = Field(default=0, ge=0, description="Count of manual actions snoozes in 30 days.")
    last_updated: Optional[str] = Field(default=None, description="ISO-8601 date of state modification.")
