"""
Integration tests for the AI Runtime Integration (Phase 11).
"""
import unittest
from unittest.mock import patch, MagicMock
import json
from uuid import uuid4
from datetime import datetime

from ai.runtime import AIRuntime, create_ai_runtime
from ai.contracts.scan_context import ScanContext
from ai.contracts.enums import ResourceType, PolicyValidationStatus, RiskLevel, RecommendedAction
from ai.contracts.metrics_summary import MetricsSummary
from ai.contracts.cost_summary import CostSummary
from ai.contracts.owner_info import OwnerInfo
from ai.contracts.history_summary import HistorySummary
from ai.contracts.recommendation import RecommendationV1
from ai.contracts.policy_result import PolicyValidationResult
from ai.telemetry.tracker import TelemetryTracker

class TestAIRuntimeIntegration(unittest.TestCase):
    def setUp(self) -> None:
        self.recommendation = RecommendationV1(
            recommendation_id=uuid4(),
            generated_at="2026-07-04T00:00:00Z",
            model="gpt-4o",
            prompt_version="1.0.0",
            resource_id="i-123456",
            recommended_action=RecommendedAction.STOP_INSTANCE,
            reasoning="Instance has been idle.",
            confidence_score=0.95,
            risk_assessment={"downtime": "none"},
            projected_monthly_savings=15.0,
            explanation_steps=["Step 1"],
            citations=["metric"],
            confidence_reason="Low CPU",
            assumptions=["No impact"]
        )
        
        self.ebs_recommendation = RecommendationV1(
            recommendation_id=uuid4(),
            generated_at="2026-07-04T00:00:00Z",
            model="gpt-4o",
            prompt_version="1.0.0",
            resource_id="vol-1234",
            recommended_action=RecommendedAction.DELETE_VOLUME,
            reasoning="Volume is unattached.",
            confidence_score=0.98,
            risk_assessment={"data_loss": "low"},
            projected_monthly_savings=8.0,
            explanation_steps=["Step 1"],
            citations=["metric"],
            confidence_reason="No attachments",
            assumptions=["No snapshot required"]
        )

    @patch("scanner.run_scan.get_instances")
    @patch("scanner.ebs_scanner.get_unattached_volumes")
    @patch("scanner.run_scan.get_average_cpu")
    @patch("scanner.run_scan.monthly_cost")
    @patch("scanner.run_scan.is_snoozed")
    @patch("scanner.run_scan.get_instance_owner")
    @patch("storage.alert_state_manager.get_alert_state")
    @patch("storage.alert_state_manager.set_alert_state")
    @patch("notifications.notifier.requests.post")
    @patch("ai.providers.openai.OpenAI")
    @patch("policy.rules.production_guard.ProductionGuardRule.evaluate")
    @patch("scanner.run_scan.boto3.client")
    def test_run_scan_successful_ai_enrichment(
        self, mock_boto, mock_rule, mock_openai, mock_post,
        mock_set_alert, mock_get_alert, mock_owner, mock_snooze,
        mock_cost, mock_cpu, mock_ebs, mock_ec2
    ) -> None:
        """Verify successful AI reasoning and passing policy check correctly enriches alerts."""
        # Setup mock resource data
        mock_ec2.return_value = [{
            "instance_id": "i-123456",
            "instance_type": "t3.micro",
            "instance_name": "test-instance",
            "tags": []
        }]
        mock_ebs.return_value = []
        mock_cpu.return_value = 1.0  # idle
        mock_cost.return_value = 10.0
        mock_snooze.return_value = False
        mock_owner.return_value = "owner-dev"
        mock_get_alert.return_value = "NEW"

        # Mock STS account details
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {"Account": "112233445566"}
        mock_boto.return_value = mock_sts

        # Mock OpenAI chat completion parse result
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.refusal = None
        mock_choice.message.parsed = self.recommendation
        mock_client.beta.chat.completions.parse.return_value.choices = [mock_choice]
        mock_openai.return_value = mock_client

        # Mock Policy Rule to pass
        mock_rule.return_value = True

        # Mock Slack response
        mock_slack_response = MagicMock()
        mock_slack_response.status_code = 200
        mock_post.return_value = mock_slack_response

        # Execute scan
        from scanner.run_scan import run_scan
        run_scan()

        # Verify mock rule was called with legacy parameters
        mock_rule.assert_called_once()
        args = mock_rule.call_args[0]
        self.assertEqual(args[0].resource_id, "i-123456")
        self.assertEqual(args[1].resource_id, "i-123456")

        # Verify Slack post payload contained AI & Policy details
        mock_post.assert_called_once()
        payload = mock_post.call_args[1]["json"]
        blocks = payload["blocks"]
        self.assertEqual(len(blocks), 4)

        # AI Details block
        self.assertIn("🤖 *AI Recommendation Details*", blocks[1]["text"]["text"])
        self.assertIn("STOP_INSTANCE", blocks[1]["text"]["text"])

        # Policy Block
        self.assertIn("🛡️ *Policy Validation Result*", blocks[2]["text"]["text"])
        self.assertIn("✅ PASSED", blocks[2]["text"]["text"])

        # Verify alert state is changed
        mock_set_alert.assert_called_once_with("i-123456", "ALERTED")

    @patch("scanner.run_scan.get_instances")
    @patch("scanner.ebs_scanner.get_unattached_volumes")
    @patch("storage.alert_state_manager.get_alert_state")
    @patch("storage.alert_state_manager.set_alert_state")
    @patch("notifications.notifier.requests.post")
    @patch("ai.providers.openai.OpenAI")
    @patch("policy.rules.production_guard.ProductionGuardRule.evaluate")
    @patch("scanner.run_scan.boto3.client")
    def test_run_scan_policy_blocked_advisory(
        self, mock_boto, mock_rule, mock_openai, mock_post,
        mock_set_alert, mock_get_alert, mock_ebs, mock_ec2
    ) -> None:
        """Verify EBS alert includes the blocked status when a policy rule rejects the recommendation."""
        # Setup mock volume data
        mock_ec2.return_value = []
        mock_ebs.return_value = [{
            "volume_id": "vol-1234",
            "size_gb": 50,
            "volume_type": "gp3",
            "availability_zone": "ap-south-1a",
            "create_time": datetime.utcnow(),
            "tags": []
        }]
        mock_get_alert.return_value = "NEW"

        # Mock STS account details
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {"Account": "112233445566"}
        mock_boto.return_value = mock_sts

        # Mock OpenAI chat completion parse result
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.refusal = None
        mock_choice.message.parsed = self.ebs_recommendation
        mock_client.beta.chat.completions.parse.return_value.choices = [mock_choice]
        mock_openai.return_value = mock_client

        # Mock Policy Rule to reject (return violations)
        mock_rule.return_value = ["Volume is critical for database backup logs."]

        # Mock Slack response
        mock_slack_response = MagicMock()
        mock_slack_response.status_code = 200
        mock_post.return_value = mock_slack_response

        # Execute scan
        from scanner.run_scan import run_scan
        run_scan()

        # Verify Slack post payload contained policy details indicating a block
        mock_post.assert_called_once()
        payload = mock_post.call_args[1]["json"]
        blocks = payload["blocks"]
        self.assertEqual(len(blocks), 4)

        # Policy Block contains blocked details
        self.assertIn("🛡️ *Policy Validation Result*", blocks[2]["text"]["text"])
        self.assertIn("❌ BLOCKED/FAILED", blocks[2]["text"]["text"])
        self.assertIn("• Volume is critical for database backup logs.", blocks[2]["text"]["text"])

        # Alert state is still updated since deterministic flow triggers it
        mock_set_alert.assert_called_once_with("vol-1234", "ALERTED")

    @patch("scanner.run_scan.get_instances")
    @patch("scanner.ebs_scanner.get_unattached_volumes")
    @patch("scanner.run_scan.get_average_cpu")
    @patch("scanner.run_scan.monthly_cost")
    @patch("scanner.run_scan.is_snoozed")
    @patch("scanner.run_scan.get_instance_owner")
    @patch("storage.alert_state_manager.get_alert_state")
    @patch("storage.alert_state_manager.set_alert_state")
    @patch("notifications.notifier.requests.post")
    @patch("ai.providers.openai.OpenAI")
    @patch("scanner.run_scan.boto3.client")
    def test_run_scan_graceful_fallback_on_ai_failure(
        self, mock_boto, mock_openai, mock_post,
        mock_set_alert, mock_get_alert, mock_owner, mock_snooze,
        mock_cost, mock_cpu, mock_ebs, mock_ec2
    ) -> None:
        """Verify that any exception in the AI pipeline is caught, and scanner falls back to deterministic alerting."""
        mock_ec2.return_value = [{
            "instance_id": "i-123456",
            "instance_type": "t3.micro",
            "instance_name": "test-instance",
            "tags": []
        }]
        mock_ebs.return_value = []
        mock_cpu.return_value = 1.0  # idle
        mock_cost.return_value = 10.0
        mock_snooze.return_value = False
        mock_owner.return_value = "owner-dev"
        mock_get_alert.return_value = "NEW"

        # Mock STS
        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {"Account": "112233445566"}
        mock_boto.return_value = mock_sts

        # Mock OpenAI to crash on invocation
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.side_effect = Exception("OpenAI Connection Timeout")
        mock_openai.return_value = mock_client

        # Mock Slack response
        mock_slack_response = MagicMock()
        mock_slack_response.status_code = 200
        mock_post.return_value = mock_slack_response

        # Execute scan - should NOT raise an exception
        try:
            from scanner.run_scan import run_scan
            run_scan()
        except Exception as e:
            self.fail(f"run_scan raised an exception instead of falling back: {e}")

        # Slack should still have been called but with exactly 2 blocks (backward compatibility fallback)
        mock_post.assert_called_once()
        payload = mock_post.call_args[1]["json"]
        blocks = payload["blocks"]
        self.assertEqual(len(blocks), 2)  # only main and actions blocks

        # Verify alert state still set
        mock_set_alert.assert_called_once_with("i-123456", "ALERTED")
