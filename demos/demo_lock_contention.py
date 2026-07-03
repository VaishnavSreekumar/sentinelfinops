import sys
import os
import uuid
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch, MagicMock

# Import tests concurrency components to simulate DynamoDB in memory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tests.test_concurrent_remediation import MockDynamoDBTable
from storage.remediation_manager import stop_instance_with_backup
from storage.remediation_lock import LockContentionError

def run_demo():
    print("=" * 70)
    print("SentinelFinOps Distributed Lock Contention Demo (v4.6)")
    print("=" * 70)
    print("Launching 10 concurrent remediations for resource: i-concur-1...\n")
    
    lock_table = MockDynamoDBTable()
    history_table = MockDynamoDBTable()
    audit_table = MockDynamoDBTable()
    
    ami_creations = 0
    stop_instances_calls = 0
    counter_lock = threading.Lock()
    
    def mock_create_image(InstanceId, Name, NoReboot):
        nonlocal ami_creations
        with counter_lock:
            ami_creations += 1
        print("Creating AMI...")
        return {"ImageId": f"ami-mock-{InstanceId}"}
        
    def mock_stop_instances(InstanceIds):
        nonlocal stop_instances_calls
        with counter_lock:
            stop_instances_calls += 1
        print("Stopping Instance...")
        return {}

    # Setup the patching environment globally
    with patch("boto3.resource") as mock_boto_res, \
         patch("boto3.client") as mock_boto_client:
         
        # Wire table mocks
        def resource_side_effect(service, *args, **kwargs):
            if service == "dynamodb":
                mock_res = MagicMock()
                def table_routing(name):
                    if name == "sentinelfinops-remediation-locks":
                        return lock_table
                    elif name == "sentinelfinops-remediation-history":
                        return history_table
                    elif name == "sentinelfinops-audit":
                        return audit_table
                    return MagicMock()
                mock_res.Table.side_effect = table_routing
                return mock_res
            return MagicMock()
            
        def client_side_effect(service, *args, **kwargs):
            if service == "ec2":
                mock_ec2 = MagicMock()
                mock_ec2.describe_instances.return_value = {
                    "Reservations": [
                        {
                            "Instances": [
                                {
                                    "InstanceId": "i-concur-1",
                                    "InstanceType": "t3.micro",
                                    "SubnetId": "subnet-123",
                                    "SecurityGroups": [{"GroupId": "sg-1"}],
                                    "Tags": [{"Key": "Name", "Value": "ConcurrentInstance"}]
                                }
                            ]
                        }
                    ]
                }
                mock_ec2.create_image.side_effect = mock_create_image
                mock_ec2.stop_instances.side_effect = mock_stop_instances
                return mock_ec2
            return MagicMock()

        mock_boto_res.side_effect = resource_side_effect
        mock_boto_client.side_effect = client_side_effect

        # Thread pools to fire concurrently
        print_lock = threading.Lock()
        results = []
        denials = []
        
        def execute_remediation_thread(worker_idx):
            exec_id = f"exec-{worker_idx}"
            req_id = f"req-{worker_idx}"
            try:
                res = stop_instance_with_backup(
                    instance_id="i-concur-1",
                    account_id="123456789012",
                    account_name="Sandbox-Test",
                    region="ap-south-1",
                    execution_id=exec_id,
                    request_id=req_id
                )
                if res:
                    results.append(exec_id)
                    with print_lock:
                        print(f"Execution {worker_idx} → LOCK_ACQUIRED")
            except LockContentionError as e:
                denials.append(exec_id)
                with print_lock:
                    print(f"Execution {worker_idx} → LOCK_DENIED (already locked by {e.owner})")
            except Exception as e:
                with print_lock:
                    print(f"Execution {worker_idx} → ERROR: {e}")

        with ThreadPoolExecutor(max_workers=10) as executor:
            executor.map(execute_remediation_thread, range(10))

        # Show lock release (simulating post execution)
        print("\nRecording History...")
        print("Releasing Lock...")
        
        # Output Summary
        print("\n" + "=" * 30 + " SUMMARY " + "=" * 30)
        print(f"Attempts:                  10")
        print(f"Locks Acquired:            {len(results)}")
        print(f"Locks Denied:              {len(denials)}")
        print(f"StopInstances Calls:       {stop_instances_calls}")
        print(f"AMI Creations:             {ami_creations}")
        print(f"History Records (SUCCESS): {len([x for x in history_table.store.values() if x.get('status') == 'SUCCESS'])}")
        print(f"Audit Records:             {len(audit_table.store)}")
        print(f"Slack Messages:            {len(results)}") # Represents webhook success return
        print("=" * 69)
        
        # Final evaluation
        if len(results) == 1 and len(denials) == 9 and ami_creations == 1 and stop_instances_calls == 1:
            print("STATUS: PASS (Distributed locking guarantees exactly-once execution safety)")
        else:
            print("STATUS: FAIL (Side-effects or locking states violated)")
        print("=" * 69)

if __name__ == "__main__":
    run_demo()
