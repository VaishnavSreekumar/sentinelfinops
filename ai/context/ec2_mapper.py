"""
EC2 resource mapper strategy implementation.
Translates ScanContext properties into standard ResourceContextV1.
"""
from ai.context.base import ContextMapper
from ai.contracts.scan_context import ScanContext
from ai.contracts.resource_context import ResourceContextV1
from ai.context.tag_normalizer import TagNormalizer
from ai.contracts.enums import CloudProvider, ResourceType

class EC2Mapper(ContextMapper):
    """
    Mapping strategy implementation for AWS EC2 instance contexts.
    """
    @property
    def supported_resource_type(self) -> ResourceType:
        return ResourceType.EC2

    def map(self, scan_context: ScanContext) -> ResourceContextV1:
        raw = scan_context.raw_resource
        tags = TagNormalizer.to_flat_dict(raw.get("tags") or raw.get("Tags"))
        
        # Build standard lifecycle info
        lifecycle = {
            "instance_type": raw.get("instance_type") or raw.get("InstanceType", "unknown"),
            "launch_time": raw.get("launch_time") or raw.get("LaunchTime", "unknown")
        }
        
        # Extract the metrics fields
        metrics_dict = {
            "cpu_mean_7_days": scan_context.metrics.cpu_mean_7_days,
            "cpu_max_7_days": scan_context.metrics.cpu_max_7_days,
            "network_in_bytes_mean_7_days": scan_context.metrics.network_in_bytes_mean_7_days,
            "io_read_ops_7_days": scan_context.metrics.io_read_ops_7_days
        }

        history_dict = {
            "alert_state": scan_context.history_summary.alert_state,
            "alert_count_30_days": scan_context.history_summary.alert_count_30_days,
            "manual_snoozes_30_days": scan_context.history_summary.manual_snoozes_30_days,
            "last_updated": scan_context.history_summary.last_updated
        }
        
        return ResourceContextV1(
            schema_version="1.0.0",
            resource_id=scan_context.resource_id,
            resource_type=scan_context.resource_type,
            cloud_provider=CloudProvider.AWS,
            account_id=scan_context.account_id,
            account_name=scan_context.account_name,
            region=scan_context.region,
            state=raw.get("state") or "running",
            tags=tags,
            metrics_summary=metrics_dict,
            lifecycle_details=lifecycle,
            history_summary=history_dict
        )
