from datetime import datetime, timezone
from decimal import Decimal
import os
import socket
import uuid
import boto3
from scanner.config import AWS_REGION, REMEDIATION_TABLE
from storage.audit_logger import log_action
from storage.remediation_lock import acquire_lock, release_lock, renew_lock, LockContentionError
from monitoring.metrics import track_idempotent_skip, publish_cloudwatch_metric


def create_ami_backup(instance_id, region=None):
    target_region = region if region and region != "Unknown" else AWS_REGION
    try:
        print("Creating AMI backup...")
        ec2 = boto3.client("ec2", region_name=target_region)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        name = f"sentinelfinops-backup-{instance_id}-{timestamp}"
        
        response = ec2.create_image(
            InstanceId=instance_id,
            Name=name,
            NoReboot=True
        )
        ami_id = response["ImageId"]
        print(f"AMI created: {ami_id}")
        return ami_id
    except Exception as e:
        print(f"Error creating AMI backup: {e}")
        return None

def record_remediation(resource_id, action, backup_id, status, timestamp=None, 
                       resource_name="Unknown", instance_type=None, subnet_id=None,
                       security_groups=None, iam_profile=None, key_name=None,
                       estimated_monthly_savings=0.0, resource_type="EC2", backup_type="AMI",
                       remediation_category=None, volume_type=None, availability_zone=None,
                       size_gb=None, tags=None, actual_monthly_cost_at_remediation=None, cost_source=None,
                       savings_confidence=None, account_id="Unknown", account_name="Unknown"):
    if not timestamp:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        
    try:
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        table = dynamodb.Table(REMEDIATION_TABLE)
        
        item = {
            "resource_id": resource_id,
            "timestamp": timestamp,
            "resource_type": resource_type,
            "action": action,
            "status": status,
            "resource_name": resource_name
        }
        
        if account_id:
            item["account_id"] = account_id
        if account_name:
            item["account_name"] = account_name
        
        if backup_id:
            item["backup_id"] = backup_id
            item["backup_type"] = backup_type
            
        if instance_type:
            item["instance_type"] = instance_type
            
        if subnet_id:
            item["subnet_id"] = subnet_id
            
        if security_groups:
            item["security_groups"] = security_groups
            
        if iam_profile:
            item["iam_profile"] = iam_profile
            
        if key_name:
            item["key_name"] = key_name
            
        if estimated_monthly_savings is not None:
            item["estimated_monthly_savings"] = Decimal(str(estimated_monthly_savings))
            
        if remediation_category:
            item["remediation_category"] = remediation_category
            
        if volume_type:
            item["volume_type"] = volume_type
            
        if availability_zone:
            item["availability_zone"] = availability_zone
            
        if size_gb is not None:
            item["size_gb"] = Decimal(str(size_gb))
            
        if tags:
            item["tags"] = tags
            
        if actual_monthly_cost_at_remediation is not None:
            item["actual_monthly_cost_at_remediation"] = Decimal(str(actual_monthly_cost_at_remediation))
            
        if cost_source:
            item["cost_source"] = cost_source
            
        if savings_confidence:
            item["savings_confidence"] = savings_confidence
            
        table.put_item(Item=item)
        return timestamp
    except Exception as e:
        print(f"Error recording remediation: {e}")
        raise e

def get_latest_backup(instance_id):
    try:
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        table = dynamodb.Table(REMEDIATION_TABLE)
        from boto3.dynamodb.conditions import Key
        
        response = table.query(
            KeyConditionExpression=Key("resource_id").eq(instance_id),
            ScanIndexForward=False,
            Limit=1
        )
        items = response.get("Items", [])
        if items:
            return items[0]
        return None
    except Exception as e:
        print(f"Error getting latest backup: {e}")
        return None

def stop_instance_with_backup(instance_id, account_id="Unknown", account_name="Unknown", region="Unknown", execution_id=None, request_id=None):
    # Decoupled Idempotency Check (resource_id + action + account_id)
    latest = get_latest_backup(instance_id)
    if latest and latest.get("status") == "SUCCESS" and latest.get("action") == "STOP_INSTANCE" and latest.get("account_id", "Unknown") == account_id:
        print(f"Idempotency Guard: Resource {instance_id} was already successfully stop-remediated in account {account_id}.")
        track_idempotent_skip()
        return latest.get("backup_id")

    own_lock = False
    if not execution_id:
        execution_id = str(uuid.uuid4())
        own_lock = True
        
    if not request_id:
        request_id = os.environ.get("AWS_LAMBDA_REQUEST_ID") or f"cli-{uuid.uuid4()}"
        
    hostname = socket.gethostname()
    target_region = region if region and region != "Unknown" else AWS_REGION
    
    # Concurrency Lock Acquisition
    lock_res = acquire_lock(
        resource_id=instance_id,
        execution_id=execution_id,
        resource_type="EC2",
        account_id=account_id,
        region=target_region,
        lock_owner="Orchestrator-Remediation",
        request_id=request_id,
        hostname=hostname
    )
    
    if lock_res.status not in ("ACQUIRED", "RECOVERED"):
        print(f"LOCK_DENIED resource={instance_id} execution={execution_id} owner={lock_res.owner} expires={lock_res.expires_at}")
        log_action(instance_id, "skip_remediation", account_id, account_name, region, skip_reason="Resource lock denied: already being remediated.")
        raise LockContentionError(instance_id, lock_res.owner, lock_res.expires_at)
        
    try:
        ec2 = boto3.client("ec2", region_name=target_region)
        
        # Describe instance metadata
        response = ec2.describe_instances(InstanceIds=[instance_id])
        instance = response["Reservations"][0]["Instances"][0]
        
        instance_type = instance.get("InstanceType")
        subnet_id = instance.get("SubnetId")
        security_groups = [sg.get("GroupId") for sg in instance.get("SecurityGroups", [])]
        iam_profile = instance.get("IamInstanceProfile", {}).get("Arn")
        key_name = instance.get("KeyName")
        
        # Resolve resource name from tags
        tags = instance.get("Tags", [])
        resource_name = "Unknown"
        for tag in tags:
            if tag.get("Key") == "Name":
                resource_name = tag.get("Value")
                break
                
        # Resolve monthly cost/savings
        from engine.cost_engine import monthly_cost
        savings = monthly_cost(instance_type)
        
        # 1. Create AMI backup
        ami_id = create_ami_backup(instance_id, region=target_region)
        if not ami_id:
            raise Exception("Failed to create AMI backup")
            
        # Heartbeat: Optimistic lock lease renewal right after backup succeeds
        renew_lock(instance_id, execution_id)
            
        # Query Cost Explorer BEFORE stopping the instance
        from storage.cost_explorer import get_monthly_cost_for_resource
        actual_cost = get_monthly_cost_for_resource(instance_id)
        if actual_cost > 0.0:
            cost_source = "COST_EXPLORER"
            savings_confidence = "HIGH"
        else:
            print("Falling back to Pricing API")
            from storage.pricing_service import get_ec2_monthly_cost
            actual_cost = get_ec2_monthly_cost(instance_type, target_region)
            if actual_cost > 0.0:
                cost_source = "PRICING_API"
                savings_confidence = "MEDIUM"
            else:
                cost_source = "ESTIMATED"
                savings_confidence = "LOW"
                actual_cost = savings
            
        # 2. Record backup in DynamoDB as PENDING (silent)
        timestamp = record_remediation(
            resource_id=instance_id,
            action="STOP_INSTANCE",
            backup_id=ami_id,
            status="PENDING",
            resource_name=resource_name,
            instance_type=instance_type,
            subnet_id=subnet_id,
            security_groups=security_groups,
            iam_profile=iam_profile,
            key_name=key_name,
            estimated_monthly_savings=savings,
            remediation_category="COMPUTE",
            actual_monthly_cost_at_remediation=actual_cost,
            cost_source=cost_source,
            savings_confidence=savings_confidence,
            account_id=account_id,
            account_name=account_name
        )
        
        # 3. Stop instance
        print("Stopping instance...")
        ec2.stop_instances(InstanceIds=[instance_id])
        print("Instance stopped")
        
        # 4. Record success/completion
        print("Recording remediation...")
        record_remediation(
            resource_id=instance_id,
            action="STOP_INSTANCE",
            backup_id=ami_id,
            status="SUCCESS",
            timestamp=timestamp,
            resource_name=resource_name,
            instance_type=instance_type,
            subnet_id=subnet_id,
            security_groups=security_groups,
            iam_profile=iam_profile,
            key_name=key_name,
            estimated_monthly_savings=savings,
            remediation_category="COMPUTE",
            actual_monthly_cost_at_remediation=actual_cost,
            cost_source=cost_source,
            savings_confidence=savings_confidence,
            account_id=account_id,
            account_name=account_name
        )
        print("Remediation recorded")
        
        # Audit logging integration
        log_action(instance_id, "remediated", account_id, account_name, target_region)
        
        return ami_id
    except Exception as e:
        print(f"Error during auto-remediation: {e}")
        return None
    finally:
        if own_lock:
            release_lock(instance_id, execution_id)

def restore_instance_from_backup(instance_id):
    print("Restoring instance...")
    print("restore_instance_from_backup is not implemented yet")
    raise NotImplementedError("restore_instance_from_backup is not implemented yet")
