"""
Prompt Registry management.
Loads and caches text prompt templates version-controlled on disk.
"""

class PromptRegistry:
    """
    Registry for loading and versioning system and user prompt templates.
    """
    def __init__(self, prompts_dir: str):
        self.prompts_dir = prompts_dir

    def get_template(self, name: str, version: str) -> tuple[str, str]:
        """
        Loads (system_template, user_template) matching the version from disk.
        """
        raise NotImplementedError("get_template is not implemented yet")

    def register_template(self, name: str, version: str, system: str, user: str) -> bool:
        """
        Saves a system and user prompt template configuration under the registry.
        """
        raise NotImplementedError("register_template is not implemented yet")
