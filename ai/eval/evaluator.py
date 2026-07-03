"""
AI Evaluation Framework.
Provides classes to verify AI pipeline behavior against test cases.
"""
from dataclasses import dataclass, field
import time
from typing import List, Optional

from ai.contracts.scan_context import ScanContext
from ai.contracts.enums import PolicyValidationStatus, RecommendedAction
from ai.runtime import AIRuntime

@dataclass(frozen=True)
class EvaluationCase:
    """
    Immutable case configuration for AI evaluation.
    """
    name: str
    scan_context: ScanContext
    expected_policy_status: Optional[PolicyValidationStatus] = None
    expected_action: Optional[RecommendedAction] = None

@dataclass(frozen=True)
class EvaluationResult:
    """
    Immutable result of an evaluation case run.
    """
    case_name: str
    success: bool
    recommendation_generated: bool
    schema_valid: bool
    policy_passed: bool
    latency_ms: float
    evaluation_errors: List[str] = field(default_factory=list)

class Evaluator:
    """
    Evaluation runner that executes cases against an AIRuntime instance.
    """
    def __init__(self, runtime: AIRuntime) -> None:
        self.runtime = runtime

    def evaluate(self, case: EvaluationCase) -> EvaluationResult:
        """
        Executes a single evaluation case using AIRuntime.process().
        Compares results against the case expectations.
        """
        errors = []
        recommendation_generated = False
        schema_valid = False
        policy_passed = False

        start_time = time.perf_counter()
        try:
            # Invoke the pipeline process
            recommendation, policy_result = self.runtime.process(case.scan_context)
        except Exception as e:
            # Safety fallback if process itself throws unexpectedly
            recommendation, policy_result = None, None
            errors.append(f"Unexpected process execution error: {e}")
        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000

        # Evaluate outcome
        if recommendation is not None and policy_result is not None:
            recommendation_generated = True
            schema_valid = True
            policy_passed = (policy_result.status == PolicyValidationStatus.PASSED)

            # Check action expectation
            if case.expected_action is not None:
                if recommendation.recommended_action != case.expected_action:
                    errors.append(
                        f"Recommended action mismatch: expected '{case.expected_action}', "
                        f"got '{recommendation.recommended_action}'"
                    )

            # Check policy expectation
            if case.expected_policy_status is not None:
                if policy_result.status != case.expected_policy_status:
                    errors.append(
                        f"Policy validation status mismatch: expected '{case.expected_policy_status}', "
                        f"got '{policy_result.status}'"
                    )
            else:
                # If no expectation and policy fails, treat as error
                if not policy_passed:
                    errors.append("Policy validation failed but PASSED was expected by default.")
        else:
            errors.append("Pipeline failed to generate a valid recommendation or policy result.")

        # Overall success is True if no validation errors occurred
        success = (len(errors) == 0)

        return EvaluationResult(
            case_name=case.name,
            success=success,
            recommendation_generated=recommendation_generated,
            schema_valid=schema_valid,
            policy_passed=policy_passed,
            latency_ms=latency_ms,
            evaluation_errors=errors
        )

    def evaluate_all(self, cases: List[EvaluationCase]) -> List[EvaluationResult]:
        """
        Runs all evaluation cases sequentially.
        """
        results = []
        for case in cases:
            results.append(self.evaluate(case))
        return results
