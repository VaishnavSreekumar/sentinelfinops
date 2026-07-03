"""
Filesystem-backed Prompt Registry.
Loads and caches text prompt templates version-controlled on disk.
"""
import os
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

class PromptRegistryError(Exception):
    """Base exception for all Prompt Registry errors."""
    pass

class PromptNotFoundError(PromptRegistryError):
    """Raised when a requested prompt or version is not found."""
    pass

class InvalidDirectoryLayoutError(PromptRegistryError):
    """Raised when the prompt directory layout does not conform to the expected structure."""
    pass

@dataclass(frozen=True)
class PromptTemplate:
    """An immutable container representing a loaded system and user prompt template."""
    name: str
    version: str
    system_prompt: str
    user_prompt: str

class PromptRegistry:
    """
    Filesystem-backed registry for discovering, versioning, and loading prompt templates.
    """
    def __init__(self, prompts_dir: str):
        """
        Initialize the registry pointing to prompts_dir on disk.
        """
        self.prompts_dir = prompts_dir
        self._cache: Dict[Tuple[str, str], PromptTemplate] = {}
        
        # Verify that the prompts directory root exists and is a directory
        if not os.path.isdir(prompts_dir):
            raise InvalidDirectoryLayoutError(
                f"Prompts root directory does not exist or is not a directory: {prompts_dir}"
            )

    def list_prompts(self) -> List[str]:
        """
        Scans prompts_dir to discover all available prompt template names.
        """
        try:
            return [
                d for d in os.listdir(self.prompts_dir)
                if os.path.isdir(os.path.join(self.prompts_dir, d))
            ]
        except Exception as e:
            raise PromptRegistryError(f"Failed to list prompts in {self.prompts_dir}: {e}")

    def list_versions(self, name: str) -> List[str]:
        """
        Scans the directory of a specific prompt to discover all available versions.
        Returns the versions sorted using semantic version logic (ascending).
        """
        prompt_path = os.path.join(self.prompts_dir, name)
        if not os.path.isdir(prompt_path):
            raise PromptNotFoundError(f"Prompt '{name}' not found in registry.")
            
        try:
            versions = [
                d for d in os.listdir(prompt_path)
                if os.path.isdir(os.path.join(prompt_path, d))
            ]
            
            # Sort using standard semantic version parsing
            def parse_version(v_str: str) -> Tuple[int, ...]:
                try:
                    return tuple(map(int, v_str.split('.')))
                except ValueError:
                    # Fallback for non-standard version folders
                    return (0,)
                    
            versions.sort(key=parse_version)
            return versions
        except Exception as e:
            raise PromptRegistryError(f"Failed to list versions for prompt '{name}': {e}")

    def get_latest_version(self, name: str) -> str:
        """
        Retrieves the latest version tag for the specified prompt.
        """
        versions = self.list_versions(name)
        if not versions:
            raise PromptNotFoundError(f"No versions found for prompt '{name}'.")
        return versions[-1]

    def get_prompt(self, name: str, version: Optional[str] = None) -> PromptTemplate:
        """
        Loads and returns an immutable PromptTemplate containing system and user prompts.
        Uses in-memory cache if the prompt version is already loaded.
        If version is not supplied, automatically resolves to the latest version.
        """
        # Resolve to latest version if not explicitly supplied
        if version is None:
            version = self.get_latest_version(name)
            
        cache_key = (name, version)
        if cache_key in self._cache:
            return self._cache[cache_key]
            
        prompt_path = os.path.join(self.prompts_dir, name, version)
        if not os.path.isdir(prompt_path):
            # Check if prompt name exists at all
            if not os.path.isdir(os.path.join(self.prompts_dir, name)):
                raise PromptNotFoundError(f"Prompt '{name}' not found in registry.")
            raise PromptNotFoundError(f"Version '{version}' not found for prompt '{name}'.")
            
        system_file = os.path.join(prompt_path, "system.txt")
        user_file = os.path.join(prompt_path, "user.txt")
        
        if not os.path.isfile(system_file) or not os.path.isfile(user_file):
            raise InvalidDirectoryLayoutError(
                f"Missing required prompt files ('system.txt' or 'user.txt') under {prompt_path}"
            )
            
        try:
            with open(system_file, "r", encoding="utf-8") as f:
                system_content = f.read()
            with open(user_file, "r", encoding="utf-8") as f:
                user_content = f.read()
                
            prompt_template = PromptTemplate(
                name=name,
                version=version,
                system_prompt=system_content,
                user_prompt=user_content
            )
            
            # Cache the loaded prompt
            self._cache[cache_key] = prompt_template
            return prompt_template
        except Exception as e:
            raise PromptRegistryError(f"Failed to load prompt template from {prompt_path}: {e}")
