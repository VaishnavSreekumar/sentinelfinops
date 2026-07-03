"""
Unit tests for AI Slack Notification enhancements.
"""
import unittest
from unittest.mock import patch, MagicMock
import json
from uuid import uuid4

from ai.contracts.recommendation import RecommendationV1
from ai.contracts.policy_result import PolicyValidationResult
from ai.contracts.enums import RecommendedAction, PolicyValidationStatus, RiskLevel
from notifications.notifier import send_alert, send_ebs_alert

class TestAISlackNotifications(unittest.TestCase):
    def setUp(self) -> None:
        self.recommendation = RecommendationV1(
            recommendation_id=uuid4(),
            generated_at="2026-07-04T00:00:00Z",
            model="gpt-4o",
            prompt_version="1.0.0",
            resource_id="i-123456",
            recommended_action=RecommendedAction.STOP_INSTANCE,
            reasoning="Instance is idle with <1% CPU for 14 days.",
            confidence_score=0.92,
            risk_assessment={"downtime": "negligible"},
            projected_monthly_savings=45.0,
            explanation_steps=["Analyze CPU history", "Check network traffic"],
            citations=["metric-cpu"],
            confidence_reason="Consistently low resource usage.",
            assumptions=["No cron jobs scheduled"]
        )

        self.policy_passed = PolicyValidationResult(
            status=PolicyValidationStatus.PASSED,
            rule_name="ProductionGuardRule",
            severity=RiskLevel.LOW.value,
            violations=[],
            passed_rules=["ProductionGuardRule"],
            failed_rules=[],
            timestamp="2026-07-04T00:01:00Z"
        )

        self.policy_failed = PolicyValidationResult(
            status=PolicyValidationStatus.FAILED,
            rule_name="ProductionGuardRule",
            severity=RiskLevel.CRITICAL.value,
            violations=["Cannot stop a database server in production environment.", "Confidence score is below 95% threshold for production."],
            passed_rules=[],
            failed_rules=["ProductionGuardRule"],
            timestamp="2026-07-04T00:01:00Z"
        )

    @patch("notifications.notifier.requests.post")
    def test_backward_compatibility_send_alert(self, mock_post) -> None:
        """Verify send_alert payload matches previous implementation exactly when AI data is absent."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # Execute send_alert without AI arguments
        send_alert(
            instance_name="test-instance",
            instance_id="i-123456",
            owner="test-owner",
            cpu_usage=5.00,
            monthly_cost=100.00,
            account_id="123456789012",
            account_name="test-account",
            region="us-east-1"
        )

        mock_post.assert_called_once()
        kwargs = mock_post.call_args[1]
        payload = kwargs["json"]

        button_value_ec2 = json.dumps({
            "resource_type": "EC2",
            "resource_id": "i-123456",
            "account_id": "123456789012",
            "account_name": "test-account",
            "region": "us-east-1"
        })

        expected_old_alert = {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            "⚠️ *SentinelFinOps Alert*\n\n"
                            "*Account Name:* test-account\n"
                            "*Account ID:* 123456789012\n"
                            "*Region:* us-east-1\n\n"
                            "*Instance Name:* test-instance\n"
                            "*Instance ID:* i-123456\n\n"
                            "*Owner:* test-owner\n\n"
                            "*CPU Usage:* 5.00%\n\n"
                            "*Estimated Monthly Cost:* $100.00\n\n"
                            "*Potential Savings:* $100.00/month\n\n"
                            "*Recommendation:* Review or Terminate\n"
                        )
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "✅ Acknowledge"
                            },
                            "action_id": "acknowledge",
                            "value": button_value_ec2
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "⏰ Snooze"
                            },
                            "action_id": "snooze",
                            "value": button_value_ec2
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Auto Fix"
                            },
                            "action_id": "autofix",
                            "value": button_value_ec2
                        }
                    ]
                }
            ]
        }

        # Assert dictionary structures are exactly equal
        self.assertEqual(payload, expected_old_alert)

    @patch("notifications.notifier.requests.post")
    def test_backward_compatibility_send_ebs_alert(self, mock_post) -> None:
        """Verify send_ebs_alert payload matches previous implementation exactly when AI data is absent."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        # Execute send_ebs_alert without AI arguments
        send_ebs_alert(
            volume_id="vol-1234",
            size=50,
            monthly_savings=25.50,
            account_id="123456789012",
            account_name="test-account",
            region="us-east-1"
        )

        mock_post.assert_called_once()
        kwargs = mock_post.call_args[1]
        payload = kwargs["json"]

        button_value_ebs = json.dumps({
            "resource_type": "EBS",
            "resource_id": "vol-1234",
            "account_id": "123456789012",
            "account_name": "test-account",
            "region": "us-east-1"
        })

        expected_old_ebs = {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            "⚠️ *Unused EBS Volume Detected*\n\n"
                            "*Account Name:* test-account\n"
                            "*Account ID:* 123456789012\n"
                            "*Region:* us-east-1\n\n"
                            "*Volume:*\nvol-1234\n\n"
                            "*Size:*\n50 GB\n\n"
                            "*Estimated Savings:*\n$25.50/month\n"
                        )
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "✅ Acknowledge"
                            },
                            "action_id": "acknowledge",
                            "value": button_value_ebs
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "⏰ Snooze"
                            },
                            "action_id": "snooze",
                            "value": button_value_ebs
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Auto Fix"
                            },
                            "action_id": "autofix",
                            "value": button_value_ebs
                        }
                    ]
                }
            ]
        }

        # Assert dictionary structures are exactly equal
        self.assertEqual(payload, expected_old_ebs)

    @patch("notifications.notifier.requests.post")
    def test_ai_alert_rendering_passed(self, mock_post) -> None:
        """Verify EC2 alert formats AI recommendation and passing policy result correctly."""
        mock_response = MagicMock()
        mock_post.return_value = mock_response

        send_alert(
            instance_name="test-instance",
            instance_id="i-123456",
            owner="test-owner",
            cpu_usage=5.00,
            monthly_cost=100.00,
            account_id="123456789012",
            account_name="test-account",
            region="us-east-1",
            recommendation=self.recommendation,
            policy_result=self.policy_passed
        )

        payload = mock_post.call_args[1]["json"]
        blocks = payload["blocks"]

        # Expected 4 blocks: Main block, AI block, Policy block, Actions block
        self.assertEqual(len(blocks), 4)

        # Verify AI recommendation block contents
        ai_block_text = blocks[1]["text"]["text"]
        self.assertIn("🤖 *AI Recommendation Details*", ai_block_text)
        self.assertIn("*Proposed Action:* STOP_INSTANCE", ai_block_text)
        self.assertIn("*Confidence Score:* 0.92 (Consistently low resource usage.)", ai_block_text)
        self.assertIn("*Rationale:* Instance is idle with <1% CPU for 14 days.", ai_block_text)
        self.assertIn("• Analyze CPU history", ai_block_text)

        # Verify Policy check block contents
        policy_block_text = blocks[2]["text"]["text"]
        self.assertIn("🛡️ *Policy Validation Result*", policy_block_text)
        self.assertIn("*Status:* ✅ PASSED", policy_block_text)
        self.assertIn("*Rule Checked:* `ProductionGuardRule`", policy_block_text)
        self.assertIn("*Severity:* `LOW`", policy_block_text)

    @patch("notifications.notifier.requests.post")
    def test_ai_alert_rendering_failed(self, mock_post) -> None:
        """Verify EBS alert formats AI recommendation and failing policy result (blocked) correctly."""
        mock_response = MagicMock()
        mock_post.return_value = mock_response

        send_ebs_alert(
            volume_id="vol-1234",
            size=50,
            monthly_savings=25.50,
            account_id="123456789012",
            account_name="test-account",
            region="us-east-1",
            recommendation=self.recommendation,
            policy_result=self.policy_failed
        )

        payload = mock_post.call_args[1]["json"]
        blocks = payload["blocks"]

        # Expected 4 blocks: Main block, AI block, Policy block, Actions block
        self.assertEqual(len(blocks), 4)

        # Verify Policy check block contents
        policy_block_text = blocks[2]["text"]["text"]
        self.assertIn("🛡️ *Policy Validation Result*", policy_block_text)
        self.assertIn("*Status:* ❌ BLOCKED/FAILED", policy_block_text)
        self.assertIn("*Rule Checked:* `ProductionGuardRule`", policy_block_text)
        self.assertIn("*Severity:* `CRITICAL`", policy_block_text)
        self.assertIn("• Cannot stop a database server in production environment.", policy_block_text)
        self.assertIn("• Confidence score is below 95% threshold for production.", policy_block_text)

    @patch("notifications.notifier.requests.post")
    def test_deterministic_formatting(self, mock_post) -> None:
        """Verify that formatting is completely deterministic (no random attributes)."""
        mock_response = MagicMock()
        mock_post.return_value = mock_response

        # Execute multiple times
        send_alert(
            instance_name="test", instance_id="i-1", owner="tester", cpu_usage=1.0, monthly_cost=10.0,
            recommendation=self.recommendation, policy_result=self.policy_passed
        )
        payload1 = mock_post.call_args_list[0][1]["json"]

        send_alert(
            instance_name="test", instance_id="i-1", owner="tester", cpu_usage=1.0, monthly_cost=10.0,
            recommendation=self.recommendation, policy_result=self.policy_passed
        )
        payload2 = mock_post.call_args_list[1][1]["json"]

        self.assertEqual(payload1, payload2)
