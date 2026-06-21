import unittest
import os
import tempfile
import yaml
from unittest.mock import patch
from config_loader import load_config, validate_and_apply_defaults

class TestConfigLoader(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.test_dir.name, "settings.yaml")
        
    def tearDown(self):
        self.test_dir.cleanup()
        
    def write_config(self, content):
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(content, f)

    def test_load_valid_config(self):
        content = {
            "config_version": 1,
            "aws": {
                "default_region": "us-east-1",
                "organizations_enabled": False
            },
            "slack": {
                "webhook_url": "https://hooks.slack.com/services/test"
            }
        }
        self.write_config(content)
        config = load_config(self.config_path)
        self.assertEqual(config["aws"]["default_region"], "us-east-1")
        self.assertFalse(config["aws"]["organizations_enabled"])
        self.assertEqual(config["slack"]["webhook_url"], "https://hooks.slack.com/services/test")
        # Ensure default values are applied
        self.assertEqual(config["remediation"]["remediation_lock_timeout_minutes"], 15)

    def test_load_invalid_version(self):
        content = {
            "config_version": 2,
            "aws": {}
        }
        self.write_config(content)
        with self.assertRaises(ValueError) as ctx:
            load_config(self.config_path)
        self.assertIn("Unsupported config_version", str(ctx.exception))

    def test_load_missing_version(self):
        content = {
            "aws": {}
        }
        self.write_config(content)
        with self.assertRaises(ValueError) as ctx:
            load_config(self.config_path)
        self.assertIn("missing 'config_version'", str(ctx.exception))

    @patch.dict(os.environ, {
        "SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/env-override",
        "AWS_REGION": "us-west-2",
        "DRY_RUN": "true"
    })
    def test_env_overrides(self):
        content = {
            "config_version": 1,
            "aws": {
                "default_region": "ap-south-1"
            },
            "slack": {
                "webhook_url": "https://hooks.slack.com/services/yaml"
            },
            "remediation": {
                "dry_run": False
            }
        }
        self.write_config(content)
        config = load_config(self.config_path)
        self.assertEqual(config["slack"]["webhook_url"], "https://hooks.slack.com/services/env-override")
        self.assertEqual(config["aws"]["default_region"], "us-west-2")
        self.assertTrue(config["remediation"]["dry_run"])

if __name__ == "__main__":
    unittest.main()
