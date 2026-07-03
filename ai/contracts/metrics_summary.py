"""
MetricsSummary Pydantic contract definition.
Defines standard CPU and IO metrics collected during discovery.
"""
from typing import Optional
from pydantic import Field
from ai.contracts.base import ContractBase

class MetricsSummary(ContractBase):
    """
    Standard metrics summary values collected during scans.
    """
    cpu_mean_7_days: Optional[float] = Field(default=None, ge=0.0, description="Mean CPU utilization percentage over 7 days.")
    cpu_max_7_days: Optional[float] = Field(default=None, ge=0.0, description="Peak CPU utilization percentage over 7 days.")
    network_in_bytes_mean_7_days: Optional[float] = Field(default=None, ge=0.0, description="Mean network ingress in bytes.")
    io_read_ops_7_days: Optional[float] = Field(default=None, ge=0.0, description="Mean read operations over 7 days.")
