"""
AI Gateway orchestration layer.
Coordinates cache checks, token tracking, retry mechanisms, and provider execution.
"""
from typing import Optional
from ai.contracts.resource_context import ResourceContextV1
from ai.contracts.recommendation import RecommendationV1
from ai.providers.base import LLMProvider
from ai.prompts.registry import PromptRegistry

class AIGateway:
    """
    Central API gateway orchestration layer managing LLM templates and reasoning calls.
    """
    def __init__(self, provider: LLMProvider, prompt_registry: PromptRegistry):
        """
        Initialize the AI Gateway with pre-configured provider and prompt_registry.
        """
        self.provider = provider
        self.registry = prompt_registry

    def execute_reasoning(
        self,
        context: ResourceContextV1,
        prompt_name: str,
        prompt_version: Optional[str] = None
    ) -> RecommendationV1:
        """
        Runs the full AI reasoning cycle for a given resource context.
        Loads the prompt templates, composes the strict prompt, and requests a RecommendationV1.
        """
        # Validate that the context is of the expected type
        if not isinstance(context, ResourceContextV1):
            raise TypeError("context must be an instance of ResourceContextV1.")

        # Load the prompt templates from the registry
        prompt_template = self.registry.get_prompt(prompt_name, prompt_version)
        system_prompt = prompt_template.system_prompt
        user_prompt = prompt_template.user_prompt

        # Serialize the context to JSON
        context_json = context.model_dump_json()

        # Compose final prompt matching the exact format:
        final_prompt = (
            f"System:\n{system_prompt}\n\n"
            f"User:\n{user_prompt}\n\n"
            f"Context:\n{context_json}"
        )

        # Invoke the provider with the composed prompt and request RecommendationV1
        recommendation = self.provider.invoke(final_prompt, RecommendationV1)
        
        return recommendation
