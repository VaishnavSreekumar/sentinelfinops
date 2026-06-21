import unittest
from unittest.mock import patch, MagicMock
from monitoring.healthcheck import health_check

class TestHealthCheck(unittest.TestCase):
    @patch("monitoring.healthcheck.boto3.client")
    def test_health_check_all_pass(self, mock_boto_client):
        # Setup mocks
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {"UserId": "test-user-id"}
        
        mock_ddb = MagicMock()
        mock_ddb.describe_table.return_value = {"Table": {"TableStatus": "ACTIVE"}}
        
        mock_org = MagicMock()
        mock_org.describe_organization.return_value = {}
        
        mock_pricing = MagicMock()
        mock_pricing.describe_services.return_value = {}
        
        mock_ce = MagicMock()
        mock_ce.get_dimension_values.return_value = {}
        
        # Configure client factory
        def client_side_effect(service_name, *args, **kwargs):
            if service_name == "sts":
                return mock_sts
            elif service_name == "dynamodb":
                return mock_ddb
            elif service_name == "organizations":
                return mock_org
            elif service_name == "pricing":
                return mock_pricing
            elif service_name == "ce":
                return mock_ce
            return MagicMock()
            
        mock_boto_client.side_effect = client_side_effect
        
        # Mock load_config to ensure Slack is configured
        with patch("monitoring.healthcheck.load_config") as mock_load_config:
            mock_load_config.return_value = {
                "aws": {
                    "default_region": "ap-south-1",
                    "organizations_enabled": True
                },
                "finops": {
                    "pricing_api_enabled": True,
                    "cost_explorer_enabled": True
                },
                "slack": {
                    "webhook_url": "https://hooks.slack.com/services/T/B/G"
                }
            }
            
            report = health_check()
            
        self.assertEqual(report["status"], "HEALTHY")
        self.assertEqual(report["details"]["DynamoDB"]["status"], "PASS")
        self.assertEqual(report["details"]["Organizations"]["status"], "PASS")
        self.assertEqual(report["details"]["PricingAPI"]["status"], "PASS")
        self.assertEqual(report["details"]["CostExplorer"]["status"], "PASS")
        self.assertEqual(report["details"]["SlackWebhook"]["status"], "PASS")

    @patch("monitoring.healthcheck.boto3.client")
    def test_health_check_failures(self, mock_boto_client):
        # Force DynamoDB failure
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {"UserId": "test-user-id"}
        
        mock_ddb = MagicMock()
        mock_ddb.describe_table.side_effect = Exception("DDB Connection Timeout")
        
        def client_side_effect(service_name, *args, **kwargs):
            if service_name == "sts":
                return mock_sts
            if service_name == "dynamodb":
                return mock_ddb
            return MagicMock()
            
        mock_boto_client.side_effect = client_side_effect
        
        with patch("monitoring.healthcheck.load_config") as mock_load_config:
            mock_load_config.return_value = {
                "aws": {
                    "default_region": "ap-south-1",
                    "organizations_enabled": False
                },
                "finops": {
                    "pricing_api_enabled": False,
                    "cost_explorer_enabled": False
                },
                "slack": {
                    "webhook_url": None
                }
            }
            
            report = health_check()
            
        self.assertEqual(report["status"], "UNHEALTHY")
        self.assertEqual(report["details"]["DynamoDB"]["status"], "FAIL")
        self.assertEqual(report["details"]["Organizations"]["status"], "WARNING")
        self.assertEqual(report["details"]["SlackWebhook"]["status"], "WARNING")

if __name__ == "__main__":
    unittest.main()
