import unittest
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
from storage.remediation_manager import stop_instance_with_backup
from storage.remediation_lock import LockContentionError

# 1. Thread-safe Mock DynamoDB Table that implements Conditional Checks
class MockDynamoDBTable:
    def __init__(self):
        self.lock = threading.Lock()
        self.store = {}
        
    def put_item(self, Item, ConditionExpression=None, ExpressionAttributeValues=None, ReturnValues=None):
        resource_id = Item.get("resource_id") or Item.get("instance_id")
        with self.lock:
            if ConditionExpression == "attribute_not_exists(resource_id)":
                if resource_id in self.store:
                    # Check if expired (simulating expires_at evaluation)
                    curr = self.store[resource_id]
                    import datetime
                    from datetime import timezone
                    now = datetime.datetime.now(timezone.utc)
                    expires = datetime.datetime.fromisoformat(curr["expires_at"].replace("Z", "+00:00"))
                    if now < expires:
                        raise ClientError({"Error": {"Code": "ConditionalCheckFailedException", "Message": "Locked"}}, "PutItem")
                old = self.store.get(resource_id)
                self.store[resource_id] = Item
                return {"Attributes": old} if ReturnValues == "ALL_OLD" else {}
                
            elif ConditionExpression == "execution_id = :old_exec AND expires_at = :old_exp":
                old_exec = ExpressionAttributeValues[":old_exec"]
                old_exp = ExpressionAttributeValues[":old_exp"]
                if resource_id not in self.store:
                    raise ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem")
                curr = self.store[resource_id]
                if curr.get("execution_id") != old_exec or curr.get("expires_at") != old_exp:
                    raise ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem")
                old = curr.copy()
                self.store[resource_id] = Item
                return {"Attributes": old} if ReturnValues == "ALL_OLD" else {}
            else:
                old = self.store.get(resource_id)
                self.store[resource_id] = Item
                return {"Attributes": old} if ReturnValues == "ALL_OLD" else {}

    def get_item(self, Key):
        resource_id = Key.get("resource_id") or Key.get("instance_id")
        with self.lock:
            item = self.store.get(resource_id)
            if item:
                return {"Item": item.copy()}
            return {}
            
    def delete_item(self, Key, ConditionExpression=None, ExpressionAttributeValues=None):
        resource_id = Key.get("resource_id") or Key.get("instance_id")
        with self.lock:
            if ConditionExpression == "execution_id = :exec_id":
                exec_id = ExpressionAttributeValues[":exec_id"]
                if resource_id not in self.store:
                    raise ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "DeleteItem")
                if self.store[resource_id].get("execution_id") != exec_id:
                    raise ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "DeleteItem")
                del self.store[resource_id]
                return {}
            else:
                if resource_id in self.store:
                    del self.store[resource_id]
                return {}

    def update_item(self, Key, UpdateExpression=None, ConditionExpression=None, ExpressionAttributeValues=None, ExpressionAttributeNames=None):
        resource_id = Key.get("resource_id") or Key.get("instance_id")
        with self.lock:
            if ConditionExpression == "execution_id = :exec_id":
                exec_id = ExpressionAttributeValues[":exec_id"]
                if resource_id not in self.store:
                    raise ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "UpdateItem")
                if self.store[resource_id].get("execution_id") != exec_id:
                    raise ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "UpdateItem")
                new_expires = ExpressionAttributeValues[":new_expires"]
                self.store[resource_id]["expires_at"] = new_expires
                if ExpressionAttributeValues and ":new_ttl" in ExpressionAttributeValues:
                    self.store[resource_id]["ttl"] = ExpressionAttributeValues[":new_ttl"]
                return {}

    def query(self, KeyConditionExpression=None, ScanIndexForward=False, Limit=None):
        with self.lock:
            items = list(self.store.values())
            # Sort by timestamp descending if ScanIndexForward is False
            items = sorted(items, key=lambda x: x.get("timestamp", ""), reverse=not ScanIndexForward)
            if Limit:
                items = items[:Limit]
            return {"Items": items}

class TestConcurrentRemediation(unittest.TestCase):
    def setUp(self):
        self.lock_table = MockDynamoDBTable()
        self.history_table = MockDynamoDBTable()
        self.audit_table = MockDynamoDBTable()
        
        # Concurrency Counters
        self.ami_creations = 0
        self.stop_instances_calls = 0
        self.counter_lock = threading.Lock()

    def mock_create_image(self, InstanceId, Name, NoReboot):
        with self.counter_lock:
            self.ami_creations += 1
        return {"ImageId": f"ami-mock-{InstanceId}"}

    def mock_stop_instances(self, InstanceIds):
        with self.counter_lock:
            self.stop_instances_calls += 1
        return {}

    @patch("boto3.resource")
    @patch("boto3.client")
    def test_concurrent_remediation_execution(self, mock_boto_client, mock_boto_res):
        # 1. Wire table mocks
        def resource_side_effect(service, *args, **kwargs):
            if service == "dynamodb":
                mock_res = MagicMock()
                def table_routing(name):
                    if name == "sentinelfinops-remediation-locks":
                        return self.lock_table
                    elif name == "sentinelfinops-remediation-history":
                        return self.history_table
                    elif name == "sentinelfinops-audit":
                        return self.audit_table
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
                mock_ec2.create_image.side_effect = self.mock_create_image
                mock_ec2.stop_instances.side_effect = self.mock_stop_instances
                return mock_ec2
            return MagicMock()

        mock_boto_res.side_effect = resource_side_effect
        mock_boto_client.side_effect = client_side_effect

        # 2. Spawn 10 concurrent requests
        results = []
        errors = []
        
        def run_remediation(worker_idx):
            import uuid
            exec_id = f"exec-{worker_idx}-{uuid.uuid4()}"
            req_id = f"req-{worker_idx}-{uuid.uuid4()}"
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
                    results.append(res)
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=10) as executor:
            executor.map(run_remediation, range(10))

        # 3. Assert Lock Concurrency Outcomes
        self.assertEqual(len(results), 1, "Exactly one execution must succeed.")
        self.assertEqual(len(errors), 9, "Exactly nine executions must be denied/fail.")
        for err in errors:
            self.assertIsInstance(err, LockContentionError, "Denied executions must raise LockContentionError.")

        # 4. Assert Side Effects (Exactly-once execution guarantees)
        self.assertEqual(self.ami_creations, 1, "Exactly one AMI backup must have been created.")
        self.assertEqual(self.stop_instances_calls, 1, "Exactly one stop instance command must have been issued.")
        
        # Verify Remediation History
        history_items = list(self.history_table.store.values())
        success_items = [x for x in history_items if x.get("status") == "SUCCESS"]
        self.assertEqual(len(success_items), 1, "Exactly one SUCCESS history record must exist.")
        self.assertEqual(success_items[0]["resource_id"], "i-concur-1")
        self.assertEqual(success_items[0]["action"], "STOP_INSTANCE")
        
        # Verify Audit Logging
        audit_items = list(self.audit_table.store.values())
        self.assertEqual(len(audit_items), 1, "Exactly one SUCCESS audit log record must exist.")

if __name__ == "__main__":
    unittest.main()
