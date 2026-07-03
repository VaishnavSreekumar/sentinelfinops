"""
EBS resource mapper strategy implementation.
Translates ScanContext properties into standard ResourceContextV1.
"""
from ai.context.base import ContextMapper
from ai.contracts.scan_context import ScanContext
from ai.contracts.resource_context import ResourceContextV1
from ai.context.tag_normalizer import TagNormalizer
from ai.contracts.enums import CloudProvider, ResourceType

class EBSMapper(ContextMapper):
    """
    Mapping strategy implementation for AWS EBS volume contexts.
    """
    @property
    def supported_resource_type(self) -> ResourceType:
        return ResourceType.EBS

    def map(self, scan_context: ScanContext) -> ResourceContextV1:
        raw = scan_context.raw_resource
        tags = TagNormalizer.to_flat_dict(raw.get("tags") or raw.get("Tags"))
        
        lifecycle = {
            "volume_type": raw.get("volume_type") or raw.get("VolumeType", "gp3"),
            "size_gb": raw.get("size_gb") or raw.get("Size", 0),
            "availability_zone": raw.get("availability_zone") or raw.get("AvailabilityZone", "unknown")
        }

        # Extract the metrics fields (savings estimation parameters)
        metrics_dict = {
            "cpu_mean_7_days": scan_context.metrics.cpu_mean_7_days,
            "cpu_max_7_days": scan_context.metrics.cpu_max_7_days,
            "network_in_bytes_mean_7_days": scan_context.metrics.network_in_bytes_mean_7_days,
            "io_read_ops_7_days": scan_context.metrics.io_read_ops_7_days,
            "current_cost": scan_context.cost_summary.current_cost,
            "projected_savings": scan_context.cost_summary.projected_savings
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
            state="available",
            tags=tags,
            metrics_summary=metrics_dict,
            lifecycle_details=lifecycle,
            history_summary=history_dict
        )
