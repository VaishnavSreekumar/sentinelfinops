import boto3
import time
from datetime import datetime, timezone
from decimal import Decimal
from botocore.exceptions import ClientError
from scanner.config import (
    AWS_REGION, REMEDIATION_TABLE, REMEDIATION_LOCKS_TABLE,
    DRY_RUN, MAINTENANCE_WINDOW_START, MAINTENANCE_WINDOW_END
)
from storage.audit_logger import log_action

def is_in_maintenance_window():
    start_str = MAINTENANCE_WINDOW_START
    end_str = MAINTENANCE_WINDOW_END
    if not start_str or not end_str:
        return True
        
    try:
        now = datetime.now(timezone.utc).time()
        start_time = datetime.strptime(start_str, "%H:%M").time()
        end_time = datetime.strptime(end_str, "%H:%M").time()
        
        if start_time <= end_time:
            return start_time <= now <= end_time
        else:
            return now >= start_time or now <= end_time
    except Exception as e:
        print(f"Error parsing maintenance window times: {e}")
        return True

def acquire_remediation_lock(resource_id, account_id):
    try:
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        table = dynamodb.Table(REMEDIATION_LOCKS_TABLE)
        
        response = table.get_item(Key={"resource_id": resource_id})
        item = response.get("Item")
        now_epoch = int(time.time())
        
        if item:
            expires_at = int(item.get("expires_at", 0))
            if now_epoch > expires_at:
                print("Stale lock found. Deleting lock.")
                table.delete_item(Key={"resource_id": resource_id})
            else:
                print("Remediation already in progress")
                return False
                
        table.put_item(
            Item={
                "resource_id": resource_id,
                "account_id": account_id,
                "status": "PENDING",
                "created_at": now_epoch,
                "expires_at": now_epoch + 900  # 15 minutes
            },
            ConditionExpression="attribute_not_exists(resource_id)"
        )
        return True
    except ClientError as ce:
        if ce.response["Error"]["Code"] == "ConditionalCheckFailedException":
            print("Remediation already in progress")
            return False
        print(f"Error acquiring remediation lock: {ce}")
        return False
    except Exception as e:
        print(f"Error acquiring remediation lock: {e}")
        return False

def release_remediation_lock(resource_id):
    try:
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        table = dynamodb.Table(REMEDIATION_LOCKS_TABLE)
        table.delete_item(Key={"resource_id": resource_id})
    except Exception as e:
        print(f"Error releasing remediation lock: {e}")

def is_already_remediated(resource_id, account_id):
    try:
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        table = dynamodb.Table(REMEDIATION_TABLE)
        from boto3.dynamodb.conditions import Key
        response = table.query(
            KeyConditionExpression=Key("resource_id").eq(resource_id)
        )
        for item in response.get("Items", []):
            if item.get("account_id") == account_id and item.get("status") == "SUCCESS":
                return True
        return False
    except Exception as e:
        print(f"Error checking duplicate remediation: {e}")
        return False

def get_current_account_id():
    try:
        return boto3.client("sts").get_caller_identity()["Account"]
    except Exception as e:
        print(f"Error fetching current account identity: {e}")
        return None

def create_ami_backup(instance_id, ec2_client):
    try:
        print("Creating AMI backup...")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        name = f"sentinelfinops-backup-{instance_id}-{timestamp}"
        
        response = ec2_client.create_image(
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
                       savings_confidence=None, account_id="Unknown", account_name="Unknown", region="Unknown"):
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
            "resource_name": resource_name,
            "account_id": account_id,
            "account_name": account_name,
            "region": region
        }
        
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

def get_latest_backup(resource_id):
    try:
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        table = dynamodb.Table(REMEDIATION_TABLE)
        from boto3.dynamodb.conditions import Key
        
        response = table.query(
            KeyConditionExpression=Key("resource_id").eq(resource_id),
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

def stop_instance_with_backup(instance_id, account_id="Unknown", account_name="Unknown", region="Unknown"):
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
        lock_acquired = acquire_remediation_lock(instance_id, account_id)
        if not lock_acquired:
            return None

        # 4. Duplicate Prevention
        if is_already_remediated(instance_id, account_id):
            print("Resource already remediated")
            return None

        # 5. Account Verification & Session Setup
        from scanner.account_session import assume_member_role
        session = assume_member_role(account_id)
        if not session:
            print("Unable to assume role")
            return None
            
        # Verify that session belongs to targeted account
        assumed_acc = session.client("sts").get_caller_identity()["Account"]
        if assumed_acc != account_id:
            print("Account verification failed")
            return None

        ec2 = session.client("ec2", region_name=region)
        
        # 6. State Verification (Re-query resource)
        response = ec2.describe_instances(InstanceIds=[instance_id])
        instance = response["Reservations"][0]["Instances"][0]
        state = instance.get("State", {}).get("Name")
        if state != "running":
            print(f"Instance no longer running (state is {state})")
            return None
            
        instance_type = instance.get("InstanceType")
        subnet_id = instance.get("SubnetId")
        security_groups = [sg.get("GroupId") for sg in instance.get("SecurityGroups", [])]
        iam_profile = instance.get("IamInstanceProfile", {}).get("Arn")
        key_name = instance.get("KeyName")
        
        tags = instance.get("Tags", [])
        resource_name = "Unknown"
        for tag in tags:
            if tag.get("Key") == "Name":
                resource_name = tag.get("Value")
                break
                
        # Resolve monthly cost/savings
        from engine.cost_engine import monthly_cost
        savings = monthly_cost(instance_type)
        
        # 7. Dry Run Mode
        if DRY_RUN:
            print(f"[DRY RUN] Would stop instance {instance_id}")
            return "dry-run-ami-id"

        # 8. Create AMI backup
        ami_id = create_ami_backup(instance_id, ec2)
        if not ami_id:
            raise Exception("Failed to create AMI backup")
            
        # Query Cost Explorer BEFORE stopping
        from storage.cost_explorer import get_monthly_cost_for_resource
        actual_cost = get_monthly_cost_for_resource(instance_id)
        if actual_cost > 0.0:
            cost_source = "COST_EXPLORER"
            savings_confidence = "HIGH"
        else:
            print("Falling back to Pricing API")
            from storage.pricing_service import get_ec2_monthly_cost
            actual_cost = get_ec2_monthly_cost(instance_type, region)
            if actual_cost > 0.0:
                cost_source = "PRICING_API"
                savings_confidence = "MEDIUM"
            else:
                cost_source = "ESTIMATED"
                savings_confidence = "LOW"
                actual_cost = savings
            
        # Record backup in DynamoDB as PENDING
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
            account_name=account_name,
            region=region
        )
        
        # Stop instance
        print("Stopping instance...")
        ec2.stop_instances(InstanceIds=[instance_id])
        print("Instance stopped")
        
        # Record success
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
            account_name=account_name,
            region=region
        )
        print("Remediation recorded")
        
        # Audit logging integration
        log_action(instance_id, "remediated", account_id, account_name, region)
        return ami_id

    except Exception as e:
        print(f"Error during auto-remediation: {e}")
        return None
    finally:
        if lock_acquired:
            release_remediation_lock(instance_id)

def restore_instance_from_backup(instance_id):
    print("Restoring instance...")
    print("restore_instance_from_backup is not implemented yet")
    raise NotImplementedError("restore_instance_from_backup is not implemented yet")
