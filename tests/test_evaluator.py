"""
Unit tests for the AI Evaluation Framework (Phase 12).
"""
import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from ai.runtime import AIRuntime
from ai.eval.evaluator import EvaluationCase, EvaluationResult, Evaluator
from ai.contracts.scan_context import ScanContext
from ai.contracts.enums import ResourceType, PolicyValidationStatus, RecommendedAction
from ai.contracts.metrics_summary import MetricsSummary
from ai.contracts.cost_summary import CostSummary
from ai.contracts.owner_info import OwnerInfo
from ai.contracts.history_summary import HistorySummary
from ai.contracts.recommendation import RecommendationV1
from ai.contracts.policy_result import PolicyValidationResult
from ai.schema_validator import SchemaValidationError

class TestEvaluator(unittest.TestCase):
    def setUp(self) -> None:
        # Create standard mock runtime components
        self.mock_context_builder = MagicMock()
        self.mock_gateway = MagicMock()
        self.mock_schema_validator = MagicMock()
        self.mock_policy_engine = MagicMock()
        self.mock_telemetry_tracker = MagicMock()

        # Build mock runtime
        self.runtime = AIRuntime(
            context_builder=self.mock_context_builder,
            gateway=self.mock_gateway,
            schema_validator=self.mock_schema_validator,
            policy_engine=self.mock_policy_engine,
            telemetry_tracker=self.mock_telemetry_tracker,
            provider_name="mock",
            model_id="gpt-4o"
        )
        
        # Instantiate evaluator
        self.evaluator = Evaluator(self.runtime)

        # Standard ScanContext
        self.scan_context = ScanContext(
            resource_id="i-123456",
            resource_type=ResourceType.EC2,
            raw_resource={},
            metrics=MetricsSummary(cpu_mean_7_days=1.0),
            cost_summary=CostSummary(current_cost=10.0),
            owner_info=OwnerInfo(),
            history_summary=HistorySummary(),
            account_id="123456789012",
            account_name="Test Account",
            region="ap-south-1"
        )

        # Standard valid RecommendationV1
        self.recommendation = RecommendationV1(
            recommendation_id=uuid4(),
            generated_at="2026-07-04T00:00:00Z",
            model="gpt-4o",
            prompt_version="1.0.0",
            resource_id="i-123456",
            recommended_action=RecommendedAction.STOP_INSTANCE,
            reasoning="Low CPU utilization",
            confidence_score=0.95,
            risk_assessment={"downtime": "none"},
            projected_monthly_savings=15.0,
            explanation_steps=["Stop it"],
            citations=[],
            confidence_reason="Low CPU",
            assumptions=[]
        )

    def test_successful_evaluation(self) -> None:
        """Verify evaluation passes when expectations match recommendation and policy status."""
        self.mock_context_builder.build_context.return_value = MagicMock()
        self.mock_gateway.execute_reasoning.return_value = self.recommendation
        self.mock_policy_engine.evaluate.return_value = PolicyValidationResult(
            status=PolicyValidationStatus.PASSED,
            rule_name="ProductionGuardRule",
            severity="HIGH",
            violations=[],
            passed_rules=["ProductionGuardRule"],
            failed_rules=[],
            timestamp="2026-07-04T00:00:00Z"
        )

        case = EvaluationCase(
            name="Test Success",
            scan_context=self.scan_context,
            expected_policy_status=PolicyValidationStatus.PASSED,
            expected_action=RecommendedAction.STOP_INSTANCE
        )

        result = self.evaluator.evaluate(case)

        self.assertTrue(result.success)
        self.assertTrue(result.recommendation_generated)
        self.assertTrue(result.schema_valid)
        self.assertTrue(result.policy_passed)
        self.assertEqual(len(result.evaluation_errors), 0)
        self.assertGreaterEqual(result.latency_ms, 0.0)

    def test_schema_failure(self) -> None:
        """Verify that a schema validation exception is recorded and results in a failure."""
        self.mock_context_builder.build_context.return_value = MagicMock()
        self.mock_gateway.execute_reasoning.return_value = self.recommendation
        
        # Schema validator raises validation error
        self.mock_schema_validator.validate.side_effect = SchemaValidationError("Invalid schema version")

        case = EvaluationCase(
            name="Test Schema Failure",
            scan_context=self.scan_context
        )

        result = self.evaluator.evaluate(case)

        self.assertFalse(result.success)
        self.assertFalse(result.recommendation_generated)
        self.assertFalse(result.schema_valid)
        self.assertFalse(result.policy_passed)
        self.assertIn("Pipeline failed to generate a valid recommendation", result.evaluation_errors[0])

    def test_policy_rejection(self) -> None:
        """Verify that policy rejections are correctly captured and reflected in the result."""
        self.mock_context_builder.build_context.return_value = MagicMock()
        self.mock_gateway.execute_reasoning.return_value = self.recommendation
        self.mock_policy_engine.evaluate.return_value = PolicyValidationResult(
            status=PolicyValidationStatus.FAILED,
            rule_name="ProductionGuardRule",
            severity="HIGH",
            violations=["Production asset requires high confidence."],
            passed_rules=[],
            failed_rules=["ProductionGuardRule"],
            timestamp="2026-07-04T00:00:00Z"
        )

        # Expected policy status is FAILED, so case should count as successful (behaves as expected)
        case = EvaluationCase(
            name="Test Expected Policy Rejection",
            scan_context=self.scan_context,
            expected_policy_status=PolicyValidationStatus.FAILED
        )

        result = self.evaluator.evaluate(case)

        self.assertTrue(result.success)
        self.assertTrue(result.recommendation_generated)
        self.assertTrue(result.schema_valid)
        self.assertFalse(result.policy_passed)
        self.assertEqual(len(result.evaluation_errors), 0)

        # Unexpected policy failure should count as unsuccessful case
        unexpected_case = EvaluationCase(
            name="Test Unexpected Policy Rejection",
            scan_context=self.scan_context,
            expected_policy_status=PolicyValidationStatus.PASSED
        )

        result_unexpected = self.evaluator.evaluate(unexpected_case)
        self.assertFalse(result_unexpected.success)
        self.assertIn("Policy validation status mismatch", result_unexpected.evaluation_errors[0])

    def test_pipeline_exception(self) -> None:
        """Verify unexpected pipeline crashes are caught gracefully and logged as errors."""
        self.mock_context_builder.build_context.side_effect = RuntimeError("AWS Context Error")

        case = EvaluationCase(
            name="Test Pipeline Crash",
            scan_context=self.scan_context
        )

        result = self.evaluator.evaluate(case)

        self.assertFalse(result.success)
        self.assertFalse(result.recommendation_generated)
        self.assertFalse(result.schema_valid)
        self.assertFalse(result.policy_passed)
        self.assertIn("Pipeline failed to generate a valid recommendation", result.evaluation_errors[0])

    def test_evaluate_all(self) -> None:
        """Verify evaluate_all sequentially runs multiple cases and returns correct outcomes."""
        self.mock_context_builder.build_context.return_value = MagicMock()
        self.mock_gateway.execute_reasoning.return_value = self.recommendation
        self.mock_policy_engine.evaluate.return_value = PolicyValidationResult(
            status=PolicyValidationStatus.PASSED,
            rule_name="ProductionGuardRule",
            severity="HIGH",
            violations=[],
            passed_rules=["ProductionGuardRule"],
            failed_rules=[],
            timestamp="2026-07-04T00:00:00Z"
        )

        case1 = EvaluationCase(
            name="Case 1",
            scan_context=self.scan_context,
            expected_policy_status=PolicyValidationStatus.PASSED
        )
        case2 = EvaluationCase(
            name="Case 2",
            scan_context=self.scan_context,
            expected_action=RecommendedAction.STOP_INSTANCE
        )

        results = self.evaluator.evaluate_all([case1, case2])

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].case_name, "Case 1")
        self.assertTrue(results[0].success)
        self.assertEqual(results[1].case_name, "Case 2")
        self.assertTrue(results[1].success)
