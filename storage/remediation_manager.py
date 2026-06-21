from datetime import datetime, timezone
from decimal import Decimal
import boto3
from scanner.config import AWS_REGION, REMEDIATION_TABLE
from storage.audit_logger import log_action

def create_ami_backup(instance_id):
    try:
        print("Creating AMI backup...")
        ec2 = boto3.client("ec2", region_name=AWS_REGION)
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
                       size_gb=None, tags=None):
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

def stop_instance_with_backup(instance_id):
    try:
        ec2 = boto3.client("ec2", region_name=AWS_REGION)
        
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
        ami_id = create_ami_backup(instance_id)
        if not ami_id:
            raise Exception("Failed to create AMI backup")
            
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
            remediation_category="COMPUTE"
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
            remediation_category="COMPUTE"
        )
        print("Remediation recorded")

        
        # Audit logging integration
        log_action(instance_id, "remediated")
        
        return ami_id
    except Exception as e:
        print(f"Error during auto-remediation: {e}")
        return None

def restore_instance_from_backup(instance_id):
    print("Restoring instance...")
    print("restore_instance_from_backup is not implemented yet")
    raise NotImplementedError("restore_instance_from_backup is not implemented yet")
