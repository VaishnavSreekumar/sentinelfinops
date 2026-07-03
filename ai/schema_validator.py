"""
AI response schema validator.
Validates structured RecommendationV1 contracts before processing.
"""
from ai.contracts.recommendation import RecommendationV1

class SchemaValidationError(Exception):
    """
    Exception raised when an AI recommendation fails structural or version validation.
    """
    pass

class SchemaValidator:
    """
    Stateless validation engine for AI recommendation contracts.
    """
    @staticmethod
    def validate(recommendation: RecommendationV1) -> RecommendationV1:
        """
        Validates that the input is a supported recommendation contract
        and matches the expected schema version constraints.
        Returns the recommendation instance unchanged if valid.
        """
        # 1. Enforce type checking for RecommendationV1
        if not isinstance(recommendation, RecommendationV1):
            raise SchemaValidationError(
                f"Invalid recommendation type: expected 'RecommendationV1', got '{type(recommendation).__name__}'."
            )
            
        # 2. Verify schema version constraint
        if recommendation.schema_version != "1.0.0":
            raise SchemaValidationError(
                f"Unsupported schema version: '{recommendation.schema_version}'. Expected '1.0.0'."
            )
            
        return recommendation
