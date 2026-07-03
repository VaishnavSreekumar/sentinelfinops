"""
Unit tests for ResourceContext contracts.
"""
import unittest
from pydantic import ValidationError
from ai.contracts.resource_context import ResourceContextV1
from ai.contracts.enums import CloudProvider, ResourceType

class TestResourceContext(unittest.TestCase):
    def setUp(self):
        self.valid_data = {
            "resource_id": "i-09ab82910fa",
            "resource_type": ResourceType.EC2,
            "cloud_provider": CloudProvider.AWS,
            "account_id": "123456789012",
            "account_name": "prod-environment",
            "region": "ap-south-1",
            "state": "Running",
            "tags": {"Name": "web-server", "Env": "Prod"},
            "metrics_summary": {"cpu_mean_7_days": 1.25},
            "lifecycle_details": {"size": "t3.micro"},
            "history_summary": {"alert_count": 0}
        }

    def test_instantiation_success(self):
        context = ResourceContextV1(**self.valid_data)
        self.assertEqual(context.resource_id, "i-09ab82910fa")
        self.assertEqual(context.schema_version, "1.0.0")
        self.assertEqual(context.cloud_provider, CloudProvider.AWS)
        self.assertEqual(context.tags["Name"], "web-server")

    def test_instantiation_defaults(self):
        # cloud_provider defaults to AWS
        data = self.valid_data.copy()
        del data["cloud_provider"]
        context = ResourceContextV1(**data)
        self.assertEqual(context.cloud_provider, CloudProvider.AWS)

    def test_validation_missing_required(self):
        data = self.valid_data.copy()
        del data["resource_id"]
        with self.assertRaises(ValidationError):
            ResourceContextV1(**data)

    def test_validation_invalid_type(self):
        data = self.valid_data.copy()
        data["resource_type"] = "InvalidType"
        with self.assertRaises(ValidationError):
            ResourceContextV1(**data)

    def test_forbid_extra_fields(self):
        data = self.valid_data.copy()
        data["extra_param"] = "unallowed-field"
        with self.assertRaises(ValidationError):
            ResourceContextV1(**data)

    def test_immutability(self):
        context = ResourceContextV1(**self.valid_data)
        with self.assertRaises(ValidationError):
            # Pydantic v2 raises ValidationError on attempt to modify frozen model fields
            context.resource_id = "new-id"

    def test_strict_type_enforcement(self):
        data = self.valid_data.copy()
        # tags requires Dict[str, str], passing list should raise ValidationError
        data["tags"] = ["not-a-dict"]
        with self.assertRaises(ValidationError):
            ResourceContextV1(**data)

if __name__ == "__main__":
    unittest.main()
