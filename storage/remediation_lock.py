import os
import socket
import time
import random
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError
from scanner.config import AWS_REGION, REMEDIATION_LOCKS_TABLE
from config_loader import load_config
from monitoring.metrics import publish_cloudwatch_metric

class LockContentionError(Exception):
    def __init__(self, resource_id, owner, expires_at):
        self.resource_id = resource_id
        self.owner = owner
        self.expires_at = expires_at
        super().__init__(f"Resource {resource_id} is locked by {owner} until {expires_at}")

@dataclass
class LockResult:
    status: str  # ACQUIRED, DENIED, RELEASED, RECOVERED, FAILED
    reason: str
    owner: str
    expires_at: str
    execution_id: str
    request_id: str = "Unknown"
    hostname: str = "Unknown"

def acquire_lock(resource_id, execution_id, resource_type="EC2", account_id="Unknown", region="Unknown", lock_owner="Unknown", request_id="Unknown", hostname="Unknown"):
    """
    Acquire a distributed lock on a resource using DynamoDB conditional write primitives.
    
    Flow:
    1. Try to PutItem with condition attribute_not_exists(resource_id) - (ACQUIRED)
    2. If check fails, read current lock. If current is active, return status DENIED.
    3. If current is expired, try to conditional PutItem verifying execution_id and expires_at match (RECOVERED).
    4. If conditional PutItem fails due to concurrency, retry up to 3 times with exponential backoff and jitter.
    """
    start_time = time.time()
    total_sleep_time_ms = 0
    
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    table = dynamodb.Table(REMEDIATION_LOCKS_TABLE)
    
    config = load_config()
    timeout_minutes = int(config["remediation"].get("remediation_lock_timeout_minutes", 15))
    
    retries = 3
    for attempt in range(retries):
        if attempt > 0:
            # Exponential backoff with jitter: 25ms, 50ms, etc. with random 0-25ms jitter
            base_sleep = 0.025 * (2 ** (attempt - 1))
            sleep_time = base_sleep + random.uniform(0, 0.025)
            total_sleep_time_ms += int(sleep_time * 1000)
            time.sleep(sleep_time)
            publish_cloudwatch_metric("LockAcquisitionRetries", attempt)
            
        now = datetime.now(timezone.utc)
        locked_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        expiration_dt = now + timedelta(minutes=timeout_minutes)
        expires_at = expiration_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        ttl = int(expiration_dt.timestamp())
        
        # 1. Attempt to acquire an unassigned lock row
        try:
            table.put_item(
                Item={
                    "resource_id": resource_id,
                    "lock_owner": lock_owner,
                    "locked_at": locked_at,
                    "expires_at": expires_at,
                    "ttl": ttl,
                    "execution_id": execution_id,
                    "resource_type": resource_type,
                    "account_id": account_id,
                    "region": region,
                    "request_id": request_id,
                    "hostname": hostname
                },
                ConditionExpression="attribute_not_exists(resource_id)"
            )
            print(f"LOCK_ACQUIRED resource={resource_id} execution={execution_id} owner={lock_owner} request={request_id}")
            publish_cloudwatch_metric("LocksAcquired", 1)
            
            # Record latency & wait duration metrics
            latency_ms = int((time.time() - start_time) * 1000)
            publish_cloudwatch_metric("LockAcquisitionLatencyMs", latency_ms)
            if total_sleep_time_ms > 0:
                publish_cloudwatch_metric("LockWaitDurationMs", total_sleep_time_ms)
                
            return LockResult("ACQUIRED", "Lock acquired successfully.", lock_owner, expires_at, execution_id, request_id, hostname)
        except ClientError as e:
            if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
                publish_cloudwatch_metric("LockDenied", 1)
                return LockResult("FAILED", f"Error during acquisition: {e}", "Unknown", "", execution_id)
        
        # 2. Row exists, check if active or expired
        try:
            response = table.get_item(Key={"resource_id": resource_id})
            item = response.get("Item")
            if not item:
                # The item was deleted in the split-second since PutItem. Loop and retry.
                continue
            
            curr_expires_at_str = item.get("expires_at")
            curr_execution_id = item.get("execution_id", "Unknown")
            curr_owner = item.get("lock_owner", "Unknown")
            curr_request_id = item.get("request_id", "Unknown")
            curr_hostname = item.get("hostname", "Unknown")
            
            if curr_expires_at_str:
                curr_expires_at = datetime.fromisoformat(curr_expires_at_str.replace("Z", "+00:00"))
            else:
                curr_expires_at = now - timedelta(seconds=1)  # Assume expired
                
            # If not expired, this is active contention. Access denied.
            if now < curr_expires_at:
                print(f"LOCK_DENIED resource={resource_id} existing_owner={curr_owner} expires={curr_expires_at_str}")
                publish_cloudwatch_metric("LockDenied", 1)
                publish_cloudwatch_metric("ConcurrentRequestsBlocked", 1)
                return LockResult("DENIED", "Resource is currently locked by another active process.", curr_owner, curr_expires_at_str, curr_execution_id, curr_request_id, curr_hostname)
                
            # 3. Lock is expired. Attempt optimistic lease takeover.
            try:
                table.put_item(
                    Item={
                        "resource_id": resource_id,
                        "lock_owner": lock_owner,
                        "locked_at": locked_at,
                        "expires_at": expires_at,
                        "ttl": ttl,
                        "execution_id": execution_id,
                        "resource_type": resource_type,
                        "account_id": account_id,
                        "region": region,
                        "request_id": request_id,
                        "hostname": hostname
                    },
                    ConditionExpression="execution_id = :old_exec AND expires_at = :old_exp",
                    ExpressionAttributeValues={
                        ":old_exec": curr_execution_id,
                        ":old_exp": curr_expires_at_str
                    }
                )
                print(f"LOCK_RECOVERED resource={resource_id} stale_execution={curr_execution_id} new_execution={execution_id}")
                publish_cloudwatch_metric("LockExpired", 1)
                publish_cloudwatch_metric("LockRecovered", 1)
                publish_cloudwatch_metric("LocksAcquired", 1)
                
                # Record latency & wait duration metrics
                latency_ms = int((time.time() - start_time) * 1000)
                publish_cloudwatch_metric("LockAcquisitionLatencyMs", latency_ms)
                if total_sleep_time_ms > 0:
                    publish_cloudwatch_metric("LockWaitDurationMs", total_sleep_time_ms)
                    
                return LockResult("RECOVERED", f"Stale lock owned by {curr_owner} was recovered.", lock_owner, expires_at, execution_id, request_id, hostname)
            except ClientError as e:
                if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                    # Takeover clashed with another concurrent writer. Loop and retry if attempts remain.
                    continue
                publish_cloudwatch_metric("LockDenied", 1)
                return LockResult("FAILED", f"Error during stale lock recovery update: {e}", "Unknown", "", execution_id)
                
        except Exception as read_err:
            publish_cloudwatch_metric("LockDenied", 1)
            return LockResult("FAILED", f"Error querying lock status: {read_err}", "Unknown", "", execution_id)
            
    publish_cloudwatch_metric("LockDenied", 1)
    return LockResult("DENIED", "Resource lock acquisition denied due to persistent collision retries.", "Unknown", "", execution_id)

def release_lock(resource_id, execution_id):
    """
    Atomically release the lock, verifying that the current caller holds it.
    """
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    table = dynamodb.Table(REMEDIATION_LOCKS_TABLE)
    
    try:
        table.delete_item(
            Key={"resource_id": resource_id},
            ConditionExpression="execution_id = :exec_id",
            ExpressionAttributeValues={
                ":exec_id": execution_id
            }
        )
        print(f"LOCK_RELEASED resource={resource_id} execution={execution_id}")
        publish_cloudwatch_metric("LockReleased", 1)
        return LockResult("RELEASED", "Lock released successfully.", "Unknown", "", execution_id)
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            print(f"LOCK_RELEASE_DENIED resource={resource_id} execution={execution_id} reason=ownership_mismatch")
            return LockResult("FAILED", "Release denied: Lock ownership mismatch or lock does not exist.", "Unknown", "", execution_id)
        return LockResult("FAILED", f"Error during lock release: {e}", "Unknown", "", execution_id)

def renew_lock(resource_id, execution_id, timeout_minutes=None):
    """
    Extend lock expiration if the caller still holds ownership (heartbeat).
    """
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    table = dynamodb.Table(REMEDIATION_LOCKS_TABLE)
    
    now = datetime.now(timezone.utc)
    if timeout_minutes is None:
        config = load_config()
        timeout_minutes = int(config["remediation"].get("remediation_lock_timeout_minutes", 15))
        
    expiration_dt = now + timedelta(minutes=timeout_minutes)
    new_expires_at = expiration_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    new_ttl = int(expiration_dt.timestamp())
    
    try:
        table.update_item(
            Key={"resource_id": resource_id},
            UpdateExpression="SET expires_at = :new_expires, #ttl_attr = :new_ttl",
            ConditionExpression="execution_id = :exec_id",
            ExpressionAttributeNames={
                "#ttl_attr": "ttl"
            },
            ExpressionAttributeValues={
                ":new_expires": new_expires_at,
                ":new_ttl": new_ttl,
                ":exec_id": execution_id
            }
        )
        print(f"LOCK_RENEWED resource={resource_id} execution={execution_id} new_expiry={new_expires_at}")
        return LockResult("ACQUIRED", "Lock extended successfully.", "Unknown", new_expires_at, execution_id)
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return LockResult("FAILED", "Lock renewal denied: ownership mismatch or lock expired.", "Unknown", "", execution_id)
        return LockResult("FAILED", f"Error during lock renewal: {e}", "Unknown", "", execution_id)

def is_locked(resource_id):
    """
    Query current lock state, returning detailed state information.
    """
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    table = dynamodb.Table(REMEDIATION_LOCKS_TABLE)
    
    try:
        response = table.get_item(Key={"resource_id": resource_id})
        item = response.get("Item")
        if not item:
            return {
                "is_locked": False,
                "lock_owner": "None",
                "execution_id": "None",
                "expires_at": "None",
                "status": "FREE"
            }
            
        expires_at_str = item.get("expires_at")
        owner = item.get("lock_owner", "Unknown")
        exec_id = item.get("execution_id", "Unknown")
        req_id = item.get("request_id", "Unknown")
        host = item.get("hostname", "Unknown")
        
        if expires_at_str:
            expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
        else:
            expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            
        now = datetime.now(timezone.utc)
        if now < expires_at:
            status = "ACTIVE"
        else:
            status = "EXPIRED"
            
        return {
            "is_locked": (status == "ACTIVE"),
            "lock_owner": owner,
            "execution_id": exec_id,
            "request_id": req_id,
            "hostname": host,
            "expires_at": expires_at_str,
            "status": status
        }
    except Exception as e:
        print(f"Error querying lock: {e}")
        return {
            "is_locked": False,
            "lock_owner": "Error",
            "execution_id": "Error",
            "expires_at": "Error",
            "status": "FAILED"
        }
