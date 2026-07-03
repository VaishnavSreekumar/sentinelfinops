"""
Unit tests for filesystem-backed Prompt Registry.
"""
import unittest
import os
import tempfile
from ai.prompts.registry import (
    PromptRegistry,
    PromptTemplate,
    PromptNotFoundError,
    InvalidDirectoryLayoutError,
)

class TestPromptRegistry(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory structure for testing prompts
        self.test_dir = tempfile.TemporaryDirectory()
        self.prompts_path = os.path.join(self.test_dir.name, "prompts")
        os.makedirs(self.prompts_path)

    def tearDown(self):
        self.test_dir.cleanup()

    def create_mock_prompt(self, name: str, version: str, system: str = "sys", user: str = "usr", skip_system: bool = False, skip_user: bool = False):
        prompt_dir = os.path.join(self.prompts_path, name, version)
        os.makedirs(prompt_dir, exist_ok=True)
        if not skip_system:
            with open(os.path.join(prompt_dir, "system.txt"), "w", encoding="utf-8") as f:
                f.write(system)
        if not skip_user:
            with open(os.path.join(prompt_dir, "user.txt"), "w", encoding="utf-8") as f:
                f.write(user)

    def test_invalid_prompts_dir(self):
        """Verify that initializing with non-existent directory raises InvalidDirectoryLayoutError."""
        non_existent = os.path.join(self.prompts_path, "does_not_exist")
        with self.assertRaises(InvalidDirectoryLayoutError):
            PromptRegistry(non_existent)

    def test_prompt_discovery(self):
        """Verify discovery of all prompt subdirectory names."""
        os.makedirs(os.path.join(self.prompts_path, "prompt_a"))
        os.makedirs(os.path.join(self.prompts_path, "prompt_b"))
        # Create a file to ensure files are ignored in discovery
        with open(os.path.join(self.prompts_path, "some_file.txt"), "w") as f:
            f.write("text")
            
        registry = PromptRegistry(self.prompts_path)
        prompts = registry.list_prompts()
        self.assertEqual(len(prompts), 2)
        self.assertIn("prompt_a", prompts)
        self.assertIn("prompt_b", prompts)

    def test_version_sorting(self):
        """Verify semantic sorting of version directories."""
        self.create_mock_prompt("prompt_v", "1.0.0")
        self.create_mock_prompt("prompt_v", "2.0.0")
        self.create_mock_prompt("prompt_v", "1.10.0")
        self.create_mock_prompt("prompt_v", "1.2.0")
        
        registry = PromptRegistry(self.prompts_path)
        versions = registry.list_versions("prompt_v")
        # Semver ordering should yield: 1.0.0, 1.2.0, 1.10.0, 2.0.0
        self.assertEqual(versions, ["1.0.0", "1.2.0", "1.10.0", "2.0.0"])
        self.assertEqual(registry.get_latest_version("prompt_v"), "2.0.0")

    def test_get_prompt_explicit_version(self):
        """Verify loading templates for explicit version."""
        self.create_mock_prompt("prompt_x", "1.2.3", "system x", "user x")
        
        registry = PromptRegistry(self.prompts_path)
        prompt = registry.get_prompt("prompt_x", "1.2.3")
        self.assertIsInstance(prompt, PromptTemplate)
        self.assertEqual(prompt.name, "prompt_x")
        self.assertEqual(prompt.version, "1.2.3")
        self.assertEqual(prompt.system_prompt, "system x")
        self.assertEqual(prompt.user_prompt, "user x")

    def test_get_prompt_default_latest(self):
        """Verify loading without version auto-resolves to latest version."""
        self.create_mock_prompt("prompt_y", "1.0.0", "system old", "user old")
        self.create_mock_prompt("prompt_y", "1.1.0", "system new", "user new")
        
        registry = PromptRegistry(self.prompts_path)
        prompt = registry.get_prompt("prompt_y")
        self.assertEqual(prompt.version, "1.1.0")
        self.assertEqual(prompt.system_prompt, "system new")
        self.assertEqual(prompt.user_prompt, "user new")

    def test_cache_identity(self):
        """Verify that caching works and returns identical instances."""
        self.create_mock_prompt("prompt_cache", "1.0.0", "sys content", "usr content")
        
        registry = PromptRegistry(self.prompts_path)
        prompt1 = registry.get_prompt("prompt_cache", "1.0.0")
        prompt2 = registry.get_prompt("prompt_cache", "1.0.0")
        prompt3 = registry.get_prompt("prompt_cache") # Should resolve to 1.0.0 and cache hit
        
        self.assertIs(prompt1, prompt2)
        self.assertIs(prompt1, prompt3)

    def test_missing_prompt_errors(self):
        """Verify that non-existent prompt or version raises PromptNotFoundError."""
        registry = PromptRegistry(self.prompts_path)
        with self.assertRaises(PromptNotFoundError):
            registry.get_prompt("non_existent")
            
        self.create_mock_prompt("prompt_exist", "1.0.0")
        with self.assertRaises(PromptNotFoundError):
            registry.get_prompt("prompt_exist", "2.0.0")

    def test_invalid_directory_layout(self):
        """Verify that missing system.txt or user.txt raises InvalidDirectoryLayoutError."""
        self.create_mock_prompt("prompt_invalid_sys", "1.0.0", skip_system=True)
        self.create_mock_prompt("prompt_invalid_usr", "1.0.0", skip_user=True)
        
        registry = PromptRegistry(self.prompts_path)
        with self.assertRaises(InvalidDirectoryLayoutError) as ctx:
            registry.get_prompt("prompt_invalid_sys", "1.0.0")
        self.assertIn("system.txt", str(ctx.exception))
        
        with self.assertRaises(InvalidDirectoryLayoutError) as ctx:
            registry.get_prompt("prompt_invalid_usr", "1.0.0")
        self.assertIn("user.txt", str(ctx.exception))
