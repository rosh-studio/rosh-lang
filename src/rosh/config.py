"""
Rosh configuration management
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any


class RoshConfig:
    """Manage Rosh configuration from ~/.rosh/config.json"""

    def __init__(self):
        self.config_dir = Path.home() / ".rosh"
        self.config_file = self.config_dir / "config.json"
        self._config: Dict[str, Any] = {}
        self.load()

    def load(self):
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    self._config = json.load(f)
            except Exception as e:
                print(f"Warning: Could not load config: {e}")
                self._config = {}
        else:
            self._config = self._get_default_config()

    def save(self):
        """Save configuration to file"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(self._config, f, indent=2)

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "ai": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "temperature": 0.7,
                "max_tokens": 1000
            }
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value by dot-notation key (e.g., 'ai.provider')"""
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value

    def set(self, key: str, value: Any):
        """Set config value by dot-notation key"""
        keys = key.split('.')
        config = self._config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value

    def get_ai_key(self, provider: Optional[str] = None) -> Optional[str]:
        """Get API key for AI provider"""
        if provider is None:
            provider = self.get('ai.provider', 'openai')

        # Try config file first
        key = self.get(f'ai.{provider}_api_key')
        if key:
            return key

        # Fall back to environment variable
        env_vars = {
            'openai': 'OPENAI_API_KEY',
            'anthropic': 'ANTHROPIC_API_KEY',
            'together': 'TOGETHER_API_KEY'
        }

        env_var = env_vars.get(provider)
        if env_var:
            return os.getenv(env_var)

        return None


# Global config instance
_config = None

def get_config() -> RoshConfig:
    """Get global config instance"""
    global _config
    if _config is None:
        _config = RoshConfig()
    return _config
