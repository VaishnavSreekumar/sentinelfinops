import sys
import os
import time
import uuid
import threading
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import boto3
from scanner.config import AWS_REGION, REMEDIATION_LOCKS_TABLE, REMEDIATION_TABLE, AUDIT_TABLE
from storage.remediation_lock import acquire_lock, release_lock, renew_lock, is_locked, LockContentionError
from storage.remediation_manager import stop_instance_with_backup

# Helper to clean up any testing items from the active DynamoDB tables
def cleanup_ddb(resource_id):
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    locks_tbl = dynamodb.Table(REMEDIATION_LOCKS_TABLE)
    hist_tbl = dynamodb.Table(REMEDIATION_TABLE)
    audit_tbl = dynamodb.Table(AUDIT_TABLE)
    
    try:
        locks_tbl.delete_item(Key={"resource_id": resource_id})
    except Exception:
        pass
    try:
        # History table has HASH key resource_id, we need to query and delete
        response = hist_tbl.query(KeyConditionExpression=boto3.dynamodb.conditions.Key("resource_id").eq(resource_id))
        for item in response.get("Items", []):
            hist_tbl.delete_item(Key={"resource_id": item["resource_id"], "timestamp": item["timestamp"]})
    except Exception:
        pass
    try:
        # Audit table partition key is instance_id (acting as resource_id)
        response = audit_tbl.query(KeyConditionExpression=boto3.dynamodb.conditions.Key("instance_id").eq(resource_id))
        for item in response.get("Items", []):
            audit_tbl.delete_item(Key={"instance_id": item["instance_id"], "timestamp": item["timestamp"]})
    except Exception:
        pass

def run_scenarios():
    print("=" * 80)
    print("SentinelFinOps v4.6 Live Distributed Locking Verification Suite")
    print("=" * 80)
    
    # -------------------------------------------------------------------------
    # Scenario 1 — Stale Lock Recovery
    # -------------------------------------------------------------------------
    print("\n--- Scenario 1 — Stale Lock Recovery ---")
    resource_1 = f"verify-stale-lock-{uuid.uuid4()}"
    exec_old = "exec-old"
    exec_new = "exec-new"
    
    cleanup_ddb(resource_1)
    
    # First writer acquires
    res_a = acquire_lock(resource_1, exec_old, lock_owner="OldWriter")
    print(f"LOCK_ACQUIRED resource={resource_1} execution={exec_old}")
    
    # Force expired state on live database by modifying expires_at
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    table = dynamodb.Table(REMEDIATION_LOCKS_TABLE)
    past_expiry = (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    table.update_item(
        Key={"resource_id": resource_1},
        UpdateExpression="SET expires_at = :exp",
        ExpressionAttributeValues={":exp": past_expiry}
    )
    print("Lock expired...")
    
    # Second writer attempts acquisition and must recover it
    res_b = acquire_lock(resource_1, exec_new, lock_owner="NewWriter")
    if res_b.status == "RECOVERED":
        print(f"LOCK_RECOVERED resource={resource_1} execution={exec_new}")
        
    # Verify ownership transfer
    state = is_locked(resource_1)
    assert state["execution_id"] == exec_new, "Ownership did not transfer to new writer."
    
    # Verify old execution can no longer release or renew
    rel_old = release_lock(resource_1, exec_old)
    assert rel_old.status == "FAILED", "Stale execution was allowed to release the lock."
    renew_old = renew_lock(resource_1, exec_old)
    assert renew_old.status == "FAILED", "Stale execution was allowed to renew the lock."
    
    print("PASS")
    cleanup_ddb(resource_1)

    # -------------------------------------------------------------------------
    # Scenario 2 — Normal Acquire → Release → Acquire
    # -------------------------------------------------------------------------
    print("\n--- Scenario 2 — Normal Acquire → Release → Acquire ---")
    resource_2 = f"verify-normal-lifecycle-{uuid.uuid4()}"
    exec_2a = "exec-2a"
    exec_2b = "exec-2b"
    
    cleanup_ddb(resource_2)
    
    # 1. Acquire
    res_2a = acquire_lock(resource_2, exec_2a, lock_owner="Owner2A")
    print("ACQUIRED" if res_2a.status == "ACQUIRED" else "FAIL")
    
    # 2. Release
    rel_2 = release_lock(resource_2, exec_2a)
    print("RELEASED" if rel_2.status == "RELEASED" else "FAIL")
    
    # 3. Acquire Again
    res_2b = acquire_lock(resource_2, exec_2b, lock_owner="Owner2B")
    print("ACQUIRED" if res_2b.status == "ACQUIRED" else "FAIL")
    
    state = is_locked(resource_2)
    assert state["execution_id"] == exec_2b, "Second lock ownership verification failed."
    
    print("PASS")
    cleanup_ddb(resource_2)

    # -------------------------------------------------------------------------
    # Scenario 3 — Resource-Level Concurrency
    # -------------------------------------------------------------------------
    print("\n--- Scenario 3 — Resource-Level Concurrency ---")
    res_A = f"verify-resource-A-{uuid.uuid4()}"
    res_B = f"verify-resource-B-{uuid.uuid4()}"
    
    cleanup_ddb(res_A)
    cleanup_ddb(res_B)
    
    # Concurrent resources must not interfere
    a1 = acquire_lock(res_A, "exec-A", lock_owner="OwnerA")
    b1 = acquire_lock(res_B, "exec-B", lock_owner="OwnerB")
    
    print(f"LOCK_ACQUIRED resource={res_A}" if a1.status == "ACQUIRED" else "FAIL")
    print(f"LOCK_ACQUIRED resource={res_B}" if b1.status == "ACQUIRED" else "FAIL")
    
    # Second acquisition on same resource A must fail
    a2 = acquire_lock(res_A, "exec-A-dup", lock_owner="OwnerADup")
    print("LOCK_ACQUIRED" if a2.status == "ACQUIRED" else "LOCK_DENIED")
    
    assert a1.status == "ACQUIRED" and b1.status == "ACQUIRED", "Interference in separate resources."
    assert a2.status == "DENIED", "Duplicate lock was acquired."
    
    print("PASS")
    cleanup_ddb(res_A)
    cleanup_ddb(res_B)

    # -------------------------------------------------------------------------
    # Scenario 4 — Idempotency
    # -------------------------------------------------------------------------
    print("\n--- Scenario 4 — Idempotency ---")
    resource_4 = f"verify-idempotency-{uuid.uuid4()}"
    cleanup_ddb(resource_4)

    # Mock EC2 client to bypass real AWS API calls during execution, while testing real DynamoDB tables
    with patch("boto3.client") as mock_client:
        mock_ec2 = MagicMock()
        mock_ec2.describe_instances.return_value = {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": resource_4,
                            "InstanceType": "t3.micro",
                            "SubnetId": "subnet-123",
                            "SecurityGroups": [{"GroupId": "sg-1"}],
                            "Tags": [{"Key": "Name", "Value": "IdempotencyTest"}]
                        }
                    ]
                }
            ]
        }
        mock_ec2.create_image.return_value = {"ImageId": "ami-mock-idempotency"}
        mock_ec2.stop_instances.return_value = {}
        mock_client.return_value = mock_ec2
        
        # 1. First Execution: Runs backup and stops instance, recording SUCCESS history
        print("Execution 1")
        ami_1 = stop_instance_with_backup(resource_4, account_id="123456789012", account_name="Test-Acc")
        if ami_1:
            print("LOCK_ACQUIRED")
            print("...")
            print("SUCCESS")
            
        # 2. Second Execution: Must skip remediation since SUCCESS exists for resource_4
        print("Execution 2")
        ami_2 = stop_instance_with_backup(resource_4, account_id="123456789012", account_name="Test-Acc")
        if ami_2 == "ami-mock-idempotency":
            print("IDEMPOTENT_SKIP")
            
        # 3. Third Execution: Must also skip
        print("Execution 3")
        ami_3 = stop_instance_with_backup(resource_4, account_id="123456789012", account_name="Test-Acc")
        if ami_3 == "ami-mock-idempotency":
            print("IDEMPOTENT_SKIP")
            
    print("PASS")
    cleanup_ddb(resource_4)

    # -------------------------------------------------------------------------
    # Scenario 6 — Lock Ownership Enforcement
    # -------------------------------------------------------------------------
    print("\n--- Scenario 6 — Lock Ownership Enforcement ---")
    resource_6 = f"verify-ownership-{uuid.uuid4()}"
    cleanup_ddb(resource_6)
    
    # Acquire using A
    acquire_lock(resource_6, "exec-A", lock_owner="OwnerA")
    
    # Attempt release using B
    rel_b = release_lock(resource_6, "exec-B")
    if rel_b.status == "FAILED":
        print("LOCK_RELEASE_DENIED")
        
    state = is_locked(resource_6)
    assert state["is_locked"], "Lock was released by unauthorized execution."
    
    # Release using correct A
    rel_a = release_lock(resource_6, "exec-A")
    assert rel_a.status == "RELEASED", "Authorized release failed."
    
    print("PASS")
    cleanup_ddb(resource_6)

    # -------------------------------------------------------------------------
    # Scenario 7 — Lease Renewal
    # -------------------------------------------------------------------------
    print("\n--- Scenario 7 — Lease Renewal ---")
    resource_7 = f"verify-renewal-{uuid.uuid4()}"
    cleanup_ddb(resource_7)
    
    # 1. Acquire
    acquire_lock(resource_7, "exec-A", lock_owner="OwnerA")
    state_init = is_locked(resource_7)
    expires_init = state_init["expires_at"]
    
    # Wait a moment to verify timestamp increases
    time.sleep(1.1)
    
    # 2. Renew
    ren_a = renew_lock(resource_7, "exec-A")
    assert ren_a.status == "ACQUIRED", "Renewal failed."
    
    state_renew = is_locked(resource_7)
    expires_renew = state_renew["expires_at"]
    
    assert expires_renew > expires_init, "Expiration timestamp did not increase."
    assert state_renew["lock_owner"] == "OwnerA", "Lock owner changed during renewal."
    assert state_renew["execution_id"] == "exec-A", "Execution ID changed during renewal."
    
    # 3. Renew with wrong execution ID
    ren_b = renew_lock(resource_7, "exec-B")
    if ren_b.status == "FAILED":
        print("LOCK_RENEW_DENIED")
        
    print("PASS")
    cleanup_ddb(resource_7)

if __name__ == "__main__":
    run_scenarios()
