"""
Enum definitions for SentinelFinOps AI Governance contracts.
Limits values to domain-specific options rather than free-form strings.
"""
from enum import Enum

class CloudProvider(str, Enum):
    """Supported cloud vendor providers."""
    AWS = "AWS"
    GCP = "GCP"
    AZURE = "AZURE"
    OTHER = "OTHER"

class ResourceType(str, Enum):
    """Supported resource type classes."""
    EC2 = "EC2"
    EBS = "EBS"
    RDS = "RDS"
    EKS = "EKS"
    S3 = "S3"
    LAMBDA = "LAMBDA"
    GENERIC = "GENERIC"

class RecommendedAction(str, Enum):
    """Specific cost optimization and governance remediation actions."""
    DELETE_VOLUME = "DELETE_VOLUME"
    TERMINATE_INSTANCE = "TERMINATE_INSTANCE"
    STOP_INSTANCE = "STOP_INSTANCE"
    RESIZE_INSTANCE = "RESIZE_INSTANCE"
    NO_ACTION = "NO_ACTION"

class RiskLevel(str, Enum):
    """Risk tiers associated with remediation actions."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class PolicyValidationStatus(str, Enum):
    """Outcome status validation code for policy gates."""
    PASSED = "PASSED"
    FAILED = "FAILED"
    WARNING = "WARNING"
