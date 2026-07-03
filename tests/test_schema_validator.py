"""
Unit tests for stateless AI response Schema Validator.
"""
import unittest
from ai.schema_validator import SchemaValidator, SchemaValidationError
from ai.contracts.recommendation import RecommendationV1
from ai.contracts.enums import RecommendedAction

class TestSchemaValidator(unittest.TestCase):
    def setUp(self):
        # Create a valid RecommendationV1 instance for testing
        self.valid_recommendation = RecommendationV1(
            model="gpt-4",
            prompt_version="1.0.0",
            resource_id="vol-1234",
            recommended_action=RecommendedAction.DELETE_VOLUME,
            reasoning="Volume is idle.",
            confidence_score=0.95,
            risk_assessment={},
            projected_monthly_savings=20.0,
            confidence_reason="No Read/Write operations for 30 days."
        )

    def test_validate_success(self):
        """Verify that a valid RecommendationV1 passes unchanged by identity."""
        res = SchemaValidator.validate(self.valid_recommendation)
        self.assertIs(res, self.valid_recommendation)

    def test_validate_type_mismatch(self):
        """Verify that passing dictionary, string, or non-RecommendationV1 raises SchemaValidationError."""
        with self.assertRaises(SchemaValidationError) as ctx:
            SchemaValidator.validate({"model": "gpt-4"}).model_dump()  # type: ignore
        self.assertIn("Invalid recommendation type", str(ctx.exception))

        with self.assertRaises(SchemaValidationError) as ctx:
            SchemaValidator.validate("not_a_model")  # type: ignore
        self.assertIn("Invalid recommendation type", str(ctx.exception))

    def test_validate_version_mismatch(self):
        """Verify that a RecommendationV1 with incorrect schema version raises SchemaValidationError."""
        # Use Pydantic's model_construct to bypass validation and construct with unsupported version
        invalid_version_rec = RecommendationV1.model_construct(
            schema_version="2.0.0",
            model="gpt-4",
            prompt_version="1.0.0",
            resource_id="vol-123"
        )
        
        with self.assertRaises(SchemaValidationError) as ctx:
            SchemaValidator.validate(invalid_version_rec)
        self.assertIn("Unsupported schema version: '2.0.0'. Expected '1.0.0'.", str(ctx.exception))

    def test_validate_no_mutation(self):
        """Verify that the validated output object is completely unmutated."""
        initial_dump = self.valid_recommendation.model_dump()
        res = SchemaValidator.validate(self.valid_recommendation)
        self.assertEqual(res.model_dump(), initial_dump)
