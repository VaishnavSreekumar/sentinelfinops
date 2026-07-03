"""
Unit tests for AI governance enums.
"""
import unittest
from ai.contracts.enums import (
    CloudProvider,
    ResourceType,
    RecommendedAction,
    RiskLevel,
    PolicyValidationStatus,
)

class TestEnums(unittest.TestCase):
    def test_cloud_provider_values(self):
        self.assertEqual(CloudProvider.AWS, "AWS")
        self.assertEqual(CloudProvider.GCP, "GCP")
        self.assertEqual(CloudProvider.AZURE, "AZURE")
        self.assertEqual(CloudProvider.OTHER, "OTHER")

    def test_resource_type_values(self):
        self.assertEqual(ResourceType.EC2, "EC2")
        self.assertEqual(ResourceType.EBS, "EBS")
        self.assertEqual(ResourceType.RDS, "RDS")
        self.assertEqual(ResourceType.EKS, "EKS")
        self.assertEqual(ResourceType.S3, "S3")
        self.assertEqual(ResourceType.LAMBDA, "LAMBDA")
        self.assertEqual(ResourceType.GENERIC, "GENERIC")

    def test_recommended_action_values(self):
        self.assertEqual(RecommendedAction.DELETE_VOLUME, "DELETE_VOLUME")
        self.assertEqual(RecommendedAction.TERMINATE_INSTANCE, "TERMINATE_INSTANCE")
        self.assertEqual(RecommendedAction.STOP_INSTANCE, "STOP_INSTANCE")
        self.assertEqual(RecommendedAction.RESIZE_INSTANCE, "RESIZE_INSTANCE")
        self.assertEqual(RecommendedAction.NO_ACTION, "NO_ACTION")

    def test_risk_level_values(self):
        self.assertEqual(RiskLevel.LOW, "LOW")
        self.assertEqual(RiskLevel.MEDIUM, "MEDIUM")
        self.assertEqual(RiskLevel.HIGH, "HIGH")
        self.assertEqual(RiskLevel.CRITICAL, "CRITICAL")

    def test_policy_validation_status_values(self):
        self.assertEqual(PolicyValidationStatus.PASSED, "PASSED")
        self.assertEqual(PolicyValidationStatus.FAILED, "FAILED")
        self.assertEqual(PolicyValidationStatus.WARNING, "WARNING")

if __name__ == "__main__":
    unittest.main()
