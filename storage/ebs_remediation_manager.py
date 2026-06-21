import boto3
from datetime import datetime, timezone
from scanner.config import AWS_REGION, DRY_RUN
from storage.remediation_manager import (
    record_remediation, get_latest_backup, is_in_maintenance_window,
    get_current_account_id, acquire_remediation_lock, release_remediation_lock,
    is_already_remediated
)
from storage.audit_logger import log_action

def create_snapshot_backup(volume_id, ec2_client):
    try:
        print("Creating snapshot backup...")
        desc = f"SentinelFinOps backup for volume {volume_id}"
        response = ec2_client.create_snapshot(
            VolumeId=volume_id,
            Description=desc
        )
        snapshot_id = response["SnapshotId"]
        print(f"Snapshot created: {snapshot_id}")
        return snapshot_id
    except Exception as e:
        print(f"Error creating snapshot backup: {e}")
        return None

def delete_volume_with_snapshot(volume_id, account_id="Unknown", account_name="Unknown", region="Unknown"):
    lock_acquired = False
    try:
        # 1. Maintenance Window Safety
        if not is_in_maintenance_window():
            print("Outside maintenance window")
            return None

        # 2. Management Account Safety
        curr_acc = get_current_account_id()
        if account_id == curr_acc:
            print("Management account remediation disabled")
            return None

        # 3. Race Condition Protection
        lock_acquired = acquire_remediation_lock(volume_id, account_id)
        if not lock_acquired:
            return None

        # 4. Duplicate Prevention
        if is_already_remediated(volume_id, account_id):
            print("Resource already remediated")
            return None

        # 5. Account Verification & Session Setup
        from scanner.account_session import assume_member_role
        session = assume_member_role(account_id)
        if not session:
            print("Unable to assume role")
            return None
            
        assumed_acc = session.client("sts").get_caller_identity()["Account"]
        if assumed_acc != account_id:
            print("Account verification failed")
            return None

        ec2 = session.client("ec2", region_name=region)
        
        # 6. State Verification (Re-query resource)
        response = ec2.describe_volumes(VolumeIds=[volume_id])
        volume = response["Volumes"][0]
        state = volume.get("State")
        if state != "available":
            print(f"Volume no longer available (state is {state})")
            return None

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

        # 7. Dry Run Mode
        if DRY_RUN:
            print(f"[DRY RUN] Would delete volume {volume_id}")
            return "dry-run-snapshot-id"

        # 8. Create snapshot backup
        snapshot_id = create_snapshot_backup(volume_id, ec2)
        if not snapshot_id:
            raise Exception("Failed to create snapshot backup")

        # Query Cost Explorer BEFORE deleting
        from storage.cost_explorer import get_monthly_cost_for_resource
        actual_cost = get_monthly_cost_for_resource(volume_id)
        if actual_cost > 0.0:
            cost_source = "COST_EXPLORER"
            savings_confidence = "HIGH"
        else:
            print("Falling back to Pricing API")
            from storage.pricing_service import get_ebs_monthly_cost
            actual_cost = get_ebs_monthly_cost(vol_type, size, region)
            if actual_cost > 0.0:
                cost_source = "PRICING_API"
                savings_confidence = "MEDIUM"
            else:
                cost_source = "ESTIMATED"
                savings_confidence = "LOW"
                actual_cost = savings

        # Record PENDING record
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
            savings_confidence=savings_confidence,
            account_id=account_id,
            account_name=account_name,
            region=region
        )

        # Delete volume
        print("Deleting volume...")
        ec2.delete_volume(VolumeId=volume_id)
        print("Volume deleted")

        # Record SUCCESS status
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
            savings_confidence=savings_confidence,
            account_id=account_id,
            account_name=account_name,
            region=region
        )
        print("Remediation recorded")

        # Audit action
        log_action(volume_id, "remediated", account_id, account_name, region)
        return snapshot_id

    except Exception as e:
        print(f"Error during EBS remediation: {e}")
        return None
    finally:
        if lock_acquired:
            release_remediation_lock(volume_id)
