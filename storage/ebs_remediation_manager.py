import boto3
from datetime import datetime, timezone
from scanner.config import AWS_REGION
from storage.remediation_manager import record_remediation, get_latest_backup
from storage.audit_logger import log_action

def create_snapshot_backup(volume_id):
    try:
        print("Creating snapshot backup...")
        ec2 = boto3.client("ec2", region_name=AWS_REGION)
        desc = f"SentinelFinOps backup for volume {volume_id}"
        response = ec2.create_snapshot(
            VolumeId=volume_id,
            Description=desc
        )
        snapshot_id = response["SnapshotId"]
        print(f"Snapshot created: {snapshot_id}")
        return snapshot_id
    except Exception as e:
        print(f"Error creating snapshot backup: {e}")
        return None

def delete_volume_with_snapshot(volume_id):
    try:
        # Check if already remediated
        latest = get_latest_backup(volume_id)
        if latest and latest.get("status") == "SUCCESS" and latest.get("action") == "DELETE_VOLUME":
            print("Volume already remediated")
            return None

        ec2 = boto3.client("ec2", region_name=AWS_REGION)
        # Describe volume to get size and tags
        response = ec2.describe_volumes(VolumeIds=[volume_id])
        volume = response["Volumes"][0]
        
        # Safe state check
        state = volume.get("State")
        if state != "available":
            raise Exception(f"Volume {volume_id} is in state {state}, not available. Safe deletion aborted.")

        size = volume["Size"]
        vol_type = volume["VolumeType"]
        az = volume["AvailabilityZone"]
        
        # Resolve tags for resource_name
        tags = volume.get("Tags", [])
        resource_name = "Unknown"
        for tag in tags:
            if tag.get("Key") == "Name":
                resource_name = tag.get("Value")
                break

        # Estimate savings
        from scanner.ebs_scanner import estimate_ebs_monthly_cost
        savings = estimate_ebs_monthly_cost({"size_gb": size, "volume_type": vol_type})

        # 1. Create snapshot backup
        snapshot_id = create_snapshot_backup(volume_id)
        if not snapshot_id:
            raise Exception("Failed to create snapshot backup")

        # Query Cost Explorer BEFORE deleting the volume
        from storage.cost_explorer import get_monthly_cost_for_resource
        actual_cost = get_monthly_cost_for_resource(volume_id)
        if actual_cost > 0.0:
            cost_source = "COST_EXPLORER"
            savings_confidence = "HIGH"
        else:
            print("Falling back to Pricing API")
            from storage.pricing_service import get_ebs_monthly_cost
            actual_cost = get_ebs_monthly_cost(vol_type, size, AWS_REGION)
            if actual_cost > 0.0:
                cost_source = "PRICING_API"
                savings_confidence = "MEDIUM"
            else:
                cost_source = "ESTIMATED"
                savings_confidence = "LOW"
                actual_cost = savings

        # 2. Record PENDING record (silent)
        timestamp = record_remediation(
            resource_id=volume_id,
            action="DELETE_VOLUME",
            backup_id=snapshot_id,
            status="PENDING",
            resource_name=resource_name,
            estimated_monthly_savings=savings,
            resource_type="EBS",
            backup_type="SNAPSHOT",
            remediation_category="STORAGE",
            volume_type=vol_type,
            availability_zone=az,
            size_gb=size,
            tags=tags,
            actual_monthly_cost_at_remediation=actual_cost,
            cost_source=cost_source,
            savings_confidence=savings_confidence
        )

        # 3. Delete volume
        print("Deleting volume...")
        ec2.delete_volume(VolumeId=volume_id)
        print("Volume deleted")

        # 4. Record SUCCESS status
        print("Recording remediation...")
        record_remediation(
            resource_id=volume_id,
            action="DELETE_VOLUME",
            backup_id=snapshot_id,
            status="SUCCESS",
            timestamp=timestamp,
            resource_name=resource_name,
            estimated_monthly_savings=savings,
            resource_type="EBS",
            backup_type="SNAPSHOT",
            remediation_category="STORAGE",
            volume_type=vol_type,
            availability_zone=az,
            size_gb=size,
            tags=tags,
            actual_monthly_cost_at_remediation=actual_cost,
            cost_source=cost_source,
            savings_confidence=savings_confidence
        )
        print("Remediation recorded")

        # 5. Audit action
        log_action(volume_id, "remediated")

        return snapshot_id

    except Exception as e:
        print(f"Error during EBS remediation: {e}")
        # Record failure if snapshot was created
        if 'snapshot_id' in locals() and snapshot_id:
            try:
                record_remediation(
                    resource_id=volume_id,
                    action="DELETE_VOLUME",
                    backup_id=snapshot_id,
                    status="FAILED",
                    timestamp=timestamp,
                    resource_name=resource_name,
                    estimated_monthly_savings=savings,
                    resource_type="EBS",
                    backup_type="SNAPSHOT",
                    remediation_category="STORAGE",
                    volume_type=vol_type,
                    availability_zone=az,
                    size_gb=size,
                    tags=tags,
                    actual_monthly_cost_at_remediation=actual_cost if 'actual_cost' in locals() else None,
                    cost_source=cost_source if 'cost_source' in locals() else None,
                    savings_confidence=savings_confidence if 'savings_confidence' in locals() else None
                )
            except Exception as inner_e:
                print(f"Error recording failure: {inner_e}")
        return None

