import unittest
from unittest.mock import patch, MagicMock
from monitoring.metrics import publish_cloudwatch_metric, track_scan, track_remediation, track_accounts

class TestMetrics(unittest.TestCase):
    @patch("monitoring.metrics.boto3.client")
    def test_publish_cloudwatch_metric_success(self, mock_boto_client):
        mock_cw = MagicMock()
        mock_boto_client.return_value = mock_cw
        
        result = publish_cloudwatch_metric("TestMetric", 10.0, unit="Count")
        
        self.assertTrue(result)
        mock_boto_client.assert_called_once_with("cloudwatch", region_name="ap-south-1")
        mock_cw.put_metric_data.assert_called_once()
        args, kwargs = mock_cw.put_metric_data.call_args
        
        self.assertEqual(kwargs["Namespace"], "SentinelFinOps")
        self.assertEqual(kwargs["MetricData"][0]["MetricName"], "TestMetric")
        self.assertEqual(kwargs["MetricData"][0]["Value"], 10.0)
        self.assertEqual(kwargs["MetricData"][0]["Unit"], "Count")

    @patch("monitoring.metrics.boto3.client")
    def test_publish_cloudwatch_metric_failure(self, mock_boto_client):
        mock_boto_client.side_effect = Exception("CloudWatch connection error")
        
        result = publish_cloudwatch_metric("TestMetric", 10.0)
        self.assertFalse(result)

    @patch("monitoring.metrics.publish_cloudwatch_metric")
    def test_trackers(self, mock_publish):
        track_scan(completed=2, failed=1)
        mock_publish.assert_any_call("ScansCompleted", 2)
        mock_publish.assert_any_call("ScansFailed", 1)
        
        mock_publish.reset_mock()
        track_remediation(completed=3, failed=0, savings=50.25)
        mock_publish.assert_any_call("RemediationsCompleted", 3)
        mock_publish.assert_any_call("SavingsGenerated", 50.25, unit="None")
        
        mock_publish.reset_mock()
        track_accounts(5)
        mock_publish.assert_called_once_with("AccountCount", 5)

if __name__ == "__main__":
    unittest.main()
