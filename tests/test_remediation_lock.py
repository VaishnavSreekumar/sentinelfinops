import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from botocore.exceptions import ClientError
from storage.remediation_lock import (
    acquire_lock, release_lock, renew_lock, is_locked, LockContentionError
)

class TestRemediationLock(unittest.TestCase):
    @patch("storage.remediation_lock.boto3.resource")
    @patch("storage.remediation_lock.publish_cloudwatch_metric")
    def test_acquire_lock_success(self, mock_metric, mock_boto):
        mock_table = MagicMock()
        mock_boto.return_value.Table.return_value = mock_table
        mock_table.put_item.return_value = {}
        
        res = acquire_lock(
            resource_id="i-test-1",
            execution_id="exec-1",
            resource_type="EC2",
            account_id="123456",
            region="ap-south-1",
            lock_owner="Tester"
        )
        
        self.assertEqual(res.status, "ACQUIRED")
        self.assertEqual(res.owner, "Tester")
        mock_table.put_item.assert_called_once()
        mock_metric.assert_any_call("LocksAcquired", 1)

    @patch("storage.remediation_lock.boto3.resource")
    @patch("storage.remediation_lock.publish_cloudwatch_metric")
    def test_acquire_lock_duplicate_denied(self, mock_metric, mock_boto):
        mock_table = MagicMock()
        mock_boto.return_value.Table.return_value = mock_table
        
        # 1. Simulate duplicate put fails
        mock_table.put_item.side_effect = ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException", "Message": "Check Failed"}},
            "PutItem"
        )
        
        # 2. Simulate read lock returns active lock
        future_expiry = (datetime.now(timezone.utc) + timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
        mock_table.get_item.return_value = {
            "Item": {
                "resource_id": "i-test-2",
                "lock_owner": "AnotherOwner",
                "execution_id": "exec-another",
                "expires_at": future_expiry
            }
        }
        
        res = acquire_lock(
            resource_id="i-test-2",
            execution_id="exec-mine",
            lock_owner="MyOwner"
        )
        
        self.assertEqual(res.status, "DENIED")
        self.assertEqual(res.owner, "AnotherOwner")
        mock_metric.assert_any_call("LockDenied", 1)

    @patch("storage.remediation_lock.boto3.resource")
    @patch("storage.remediation_lock.publish_cloudwatch_metric")
    def test_acquire_lock_expired_takeover_success(self, mock_metric, mock_boto):
        mock_table = MagicMock()
        mock_boto.return_value.Table.return_value = mock_table
        
        # First PutItem fails (it exists)
        mock_table.put_item.side_effect = [
            ClientError(
                {"Error": {"Code": "ConditionalCheckFailedException", "Message": "Exists"}},
                "PutItem"
            ),
            {"Attributes": {"lock_owner": "StaleOwner"}}  # Second PutItem succeeds and returns old attributes
        ]
        
        # Read returns expired lock
        past_expiry = (datetime.now(timezone.utc) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        mock_table.get_item.return_value = {
            "Item": {
                "resource_id": "i-test-3",
                "lock_owner": "StaleOwner",
                "execution_id": "exec-stale",
                "expires_at": past_expiry
            }
        }
        
        res = acquire_lock(
            resource_id="i-test-3",
            execution_id="exec-fresh",
            lock_owner="FreshOwner"
        )
        
        self.assertEqual(res.status, "RECOVERED")
        mock_metric.assert_any_call("LockExpired", 1)
        mock_metric.assert_any_call("LockRecovered", 1)

    @patch("storage.remediation_lock.boto3.resource")
    @patch("storage.remediation_lock.publish_cloudwatch_metric")
    def test_release_lock_success(self, mock_metric, mock_boto):
        mock_table = MagicMock()
        mock_boto.return_value.Table.return_value = mock_table
        mock_table.delete_item.return_value = {}
        
        res = release_lock("i-test-4", "exec-4")
        self.assertEqual(res.status, "RELEASED")
        mock_metric.assert_called_once_with("LockReleased", 1)

    @patch("storage.remediation_lock.boto3.resource")
    def test_release_lock_ownership_mismatch(self, mock_boto):
        mock_table = MagicMock()
        mock_boto.return_value.Table.return_value = mock_table
        
        mock_table.delete_item.side_effect = ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException", "Message": "Mismatch"}},
            "DeleteItem"
        )
        
        res = release_lock("i-test-5", "exec-wrong")
        self.assertEqual(res.status, "FAILED")
        self.assertIn("ownership mismatch", res.reason)

    @patch("storage.remediation_lock.boto3.resource")
    def test_renew_lock_success(self, mock_boto):
        mock_table = MagicMock()
        mock_boto.return_value.Table.return_value = mock_table
        mock_table.update_item.return_value = {}
        
        res = renew_lock("i-test-6", "exec-6", timeout_minutes=20)
        self.assertEqual(res.status, "ACQUIRED")
        mock_table.update_item.assert_called_once()

    @patch("storage.remediation_lock.boto3.resource")
    def test_is_locked_active(self, mock_boto):
        mock_table = MagicMock()
        mock_boto.return_value.Table.return_value = mock_table
        
        future_expiry = (datetime.now(timezone.utc) + timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
        mock_table.get_item.return_value = {
            "Item": {
                "resource_id": "i-test-7",
                "lock_owner": "Tester",
                "execution_id": "exec-7",
                "expires_at": future_expiry
            }
        }
        
        state = is_locked("i-test-7")
        self.assertTrue(state["is_locked"])
        self.assertEqual(state["status"], "ACTIVE")
        self.assertEqual(state["lock_owner"], "Tester")

if __name__ == "__main__":
    unittest.main()
