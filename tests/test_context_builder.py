"""
Unit tests for ContextBuilder and Context Mapping strategy classes.
"""
import unittest
from uuid import uuid4
from pydantic import ValidationError
from ai.contracts.enums import ResourceType, CloudProvider, RecommendedAction, PolicyValidationStatus
from ai.contracts.metrics_summary import MetricsSummary
from ai.contracts.cost_summary import CostSummary
from ai.contracts.owner_info import OwnerInfo
from ai.contracts.history_summary import HistorySummary
from ai.contracts.scan_context import ScanContext
from ai.contracts.resource_context import ResourceContextV1
from ai.context.base import ContextMapper
from ai.context.registry import MapperRegistry
from ai.context.tag_normalizer import TagNormalizer
from ai.context.ec2_mapper import EC2Mapper
from ai.context.ebs_mapper import EBSMapper
from ai.context_builder import ContextBuilder

class DummyMapper(ContextMapper):
    @property
    def supported_resource_type(self) -> ResourceType:
        return ResourceType.RDS

    def map(self, scan_context: ScanContext) -> ResourceContextV1:
        return ResourceContextV1(
            schema_version="1.0.0",
            resource_id=scan_context.resource_id,
            resource_type=scan_context.resource_type,
            cloud_provider=CloudProvider.AWS,
            account_id=scan_context.account_id,
            account_name=scan_context.account_name,
            region=scan_context.region,
            state="running",
            tags={},
            metrics_summary={},
            lifecycle_details={},
            history_summary={}
        )

class TestContextBuilder(unittest.TestCase):
    def setUp(self):
        self.metrics = MetricsSummary(
            cpu_mean_7_days=1.5,
            cpu_max_7_days=12.0,
            network_in_bytes_mean_7_days=5000.0,
            io_read_ops_7_days=100.0
        )
        self.cost = CostSummary(
            current_cost=100.0,
            estimated_monthly_cost=100.0,
            projected_savings=80.0,
            currency="USD",
            pricing_source="PricingAPI"
        )
        self.owner = OwnerInfo(
            owner_arn="arn:aws:iam::123456789012:user/owner",
            team="Payments",
            email="payments@company.com",
            cloudtrail_actor="payments-role",
            confidence="HIGH"
        )
        self.history = HistorySummary(
            alert_state="ALERTED",
            alert_count_30_days=2,
            manual_snoozes_30_days=0,
            last_updated="2026-07-03T12:00:00Z"
        )

    def test_tag_normalizer_list(self):
        tags_list = [{"Key": "Name", "Value": "WebServer"}, {"Key": "Env", "Value": "Prod"}]
        result = TagNormalizer.to_flat_dict(tags_list)
        self.assertEqual(result, {"Name": "WebServer", "Env": "Prod"})

    def test_tag_normalizer_dict(self):
        tags_dict = {"Name": "Database", "Env": "Staging"}
        result = TagNormalizer.to_flat_dict(tags_dict)
        self.assertEqual(result, {"Name": "Database", "Env": "Staging"})

    def test_tag_normalizer_empty(self):
        self.assertEqual(TagNormalizer.to_flat_dict(None), {})
        self.assertEqual(TagNormalizer.to_flat_dict([]), {})

    def test_mapper_registry_valid(self):
        registry = MapperRegistry()
        mapper = DummyMapper()
        registry.register(mapper)
        
        resolved = registry.get_mapper(ResourceType.RDS)
        self.assertIs(resolved, mapper)

    def test_mapper_registry_invalid_type(self):
        registry = MapperRegistry()
        with self.assertRaises(TypeError):
            registry.register("not-a-mapper")

    def test_mapper_registry_missing_key(self):
        registry = MapperRegistry()
        with self.assertRaises(KeyError):
            registry.get_mapper(ResourceType.EC2)

    def test_ec2_mapper_translation(self):
        scan_ctx = ScanContext(
            resource_id="i-0987654321",
            resource_type=ResourceType.EC2,
            raw_resource={
                "InstanceId": "i-0987654321",
                "InstanceType": "t3.medium",
                "Tags": [{"Key": "Name", "Value": "ComputeNode"}],
                "state": "running"
            },
            metrics=self.metrics,
            cost_summary=self.cost,
            owner_info=self.owner,
            history_summary=self.history,
            account_id="123456789012",
            account_name="prod",
            region="us-east-1"
        )
        
        mapper = EC2Mapper()
        context = mapper.map(scan_ctx)
        
        self.assertEqual(context.resource_id, "i-0987654321")
        self.assertEqual(context.resource_type, ResourceType.EC2)
        self.assertEqual(context.tags["Name"], "ComputeNode")
        self.assertEqual(context.metrics_summary["cpu_mean_7_days"], 1.5)
        self.assertEqual(context.lifecycle_details["instance_type"], "t3.medium")
        self.assertEqual(context.history_summary["alert_state"], "ALERTED")

    def test_ebs_mapper_translation(self):
        scan_ctx = ScanContext(
            resource_id="vol-0987654321",
            resource_type=ResourceType.EBS,
            raw_resource={
                "VolumeId": "vol-0987654321",
                "Size": 100,
                "VolumeType": "gp3",
                "AvailabilityZone": "us-east-1a",
                "Tags": [{"Key": "Env", "Value": "Prod"}]
            },
            metrics=self.metrics,
            cost_summary=self.cost,
            owner_info=self.owner,
            history_summary=self.history,
            account_id="123456789012",
            account_name="prod",
            region="us-east-1"
        )
        
        mapper = EBSMapper()
        context = mapper.map(scan_ctx)
        
        self.assertEqual(context.resource_id, "vol-0987654321")
        self.assertEqual(context.resource_type, ResourceType.EBS)
        self.assertEqual(context.tags["Env"], "Prod")
        self.assertEqual(context.lifecycle_details["volume_type"], "gp3")
        self.assertEqual(context.lifecycle_details["size_gb"], 100)
        self.assertEqual(context.metrics_summary["current_cost"], 100.0)

    def test_context_builder_routing(self):
        registry = MapperRegistry()
        ec2_mapper = EC2Mapper()
        ebs_mapper = EBSMapper()
        registry.register(ec2_mapper)
        registry.register(ebs_mapper)
        
        builder = ContextBuilder(registry)
        
        scan_ctx = ScanContext(
            resource_id="i-0987654321",
            resource_type=ResourceType.EC2,
            raw_resource={
                "InstanceId": "i-0987654321",
                "InstanceType": "t3.medium",
                "Tags": [{"Key": "Name", "Value": "ComputeNode"}]
            },
            metrics=self.metrics,
            cost_summary=self.cost,
            owner_info=self.owner,
            history_summary=self.history,
            account_id="123456789012",
            account_name="prod",
            region="us-east-1"
        )
        
        context = builder.build_context(scan_ctx)
        self.assertEqual(context.resource_id, "i-0987654321")
        self.assertEqual(context.lifecycle_details["instance_type"], "t3.medium")

    def test_context_builder_invalid_parameter(self):
        registry = MapperRegistry()
        builder = ContextBuilder(registry)
        with self.assertRaises(TypeError):
            builder.build_context("not-a-scan-context")

if __name__ == "__main__":
    unittest.main()
