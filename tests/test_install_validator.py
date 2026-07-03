import unittest
from unittest.mock import patch, MagicMock
from validation.install_validator import validate_installation

class TestInstallValidator(unittest.TestCase):
    @patch("validation.install_validator.boto3.client")
    @patch("validation.install_validator.urllib.request.urlopen")
    def test_validate_installation_success(self, mock_urlopen, mock_boto_client):
        # 1. Setup mocks
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012", "Arn": "arn:aws:iam::123456789012:user/tester"}
        
        mock_iam = MagicMock()
        mock_iam.simulate_principal_policy.return_value = {
            "EvaluationResults": [
                {"EvalActionName": "dynamodb:GetItem", "EvalDecision": "allowed"},
                {"EvalActionName": "dynamodb:PutItem", "EvalDecision": "allowed"},
                {"EvalActionName": "cloudwatch:PutMetricData", "EvalDecision": "allowed"},
                {"EvalActionName": "sts:AssumeRole", "EvalDecision": "allowed"},
                {"EvalActionName": "organizations:ListAccounts", "EvalDecision": "allowed"}
            ]
        }
        mock_iam.get_role.return_value = {}
        
        mock_org = MagicMock()
        mock_org.describe_organization.return_value = {}
        
        mock_pricing = MagicMock()
        mock_pricing.describe_services.return_value = {}
        
        mock_ce = MagicMock()
        mock_ce.get_dimension_values.return_value = {}
        
        mock_ddb = MagicMock()
        mock_ddb.describe_table.return_value = {"Table": {"TableStatus": "ACTIVE"}}
        
        mock_lambda = MagicMock()
        mock_lambda.get_function.return_value = {
            "Configuration": {
                "Environment": {
                    "Variables": {
                        "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/foo"
                    }
                }
            }
        }
        
        mock_events = MagicMock()
        mock_events.describe_rule.return_value = {"State": "ENABLED", "ScheduleExpression": "rate(1 hour)"}
        
        # Configure client factory
        def client_side_effect(service_name, *args, **kwargs):
            if service_name == "sts":
                return mock_sts
            elif service_name == "iam":
                return mock_iam
            elif service_name == "organizations":
                return mock_org
            elif service_name == "pricing":
                return mock_pricing
            elif service_name == "ce":
                return mock_ce
            elif service_name == "dynamodb":
                return mock_ddb
            elif service_name == "lambda":
                return mock_lambda
            elif service_name == "events":
                return mock_events
            return MagicMock()
            
        mock_boto_client.side_effect = client_side_effect
        
        # Mock urllib urlopen response context manager
        mock_context = MagicMock()
        mock_urlopen.return_value.__enter__.return_value = mock_context
        
        with patch("validation.install_validator.load_config") as mock_load_config:
            mock_load_config.return_value = {
                "aws": {
                    "default_region": "ap-south-1",
                    "role_name": "SentinelFinOpsExecutionRole",
                    "organizations_enabled": True
                },
                "finops": {
                    "pricing_api_enabled": True,
                    "cost_explorer_enabled": True
                },
                "remediation": {
                    "remediation_lock_timeout_minutes": 15
                },
                "slack": {
                    "webhook_url": "https://hooks.slack.com/services/T/B/G"
                }
            }
            
            result = validate_installation()
            
        self.assertEqual(result, "PASS")
        mock_sts.get_caller_identity.assert_called_once()
        mock_iam.simulate_principal_policy.assert_called_once()
        mock_org.describe_organization.assert_called_once()
        mock_pricing.describe_services.assert_called_once()
        mock_ce.get_dimension_values.assert_called_once()
        self.assertEqual(mock_ddb.describe_table.call_count, 8)
        mock_lambda.get_function.assert_called_once_with(FunctionName="sentinelfinops-scanner")
        mock_events.describe_rule.assert_called_once_with(Name="sentinelfinops-hourly-schedule")
        mock_urlopen.assert_called_once()

if __name__ == "__main__":
    unittest.main()
