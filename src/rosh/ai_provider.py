"""
AI provider abstraction for Rosh

Supports multiple AI providers with a unified interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import json


class AIProvider(ABC):
    """Abstract base class for AI providers"""

    @abstractmethod
    def prompt(self, message: str, context: Optional[Dict] = None, **kwargs) -> str:
        """
        Send a prompt to the AI and get a response

        Args:
            message: The prompt text
            context: Optional context dictionary (variables, state, etc.)
            **kwargs: Provider-specific options

        Returns:
            AI response as string
        """
        pass


class OpenAIProvider(AIProvider):
    """OpenAI provider (GPT-4, GPT-3.5, etc.)"""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model

    def prompt(self, message: str, context: Optional[Dict] = None, **kwargs) -> str:
        """Send prompt to OpenAI"""
        try:
            import openai
        except ImportError:
            raise ImportError(
                "OpenAI package not installed. Run: pip install openai"
            )

        # Build messages
        messages = []

        # Add context as system message if provided
        if context:
            context_str = json.dumps(context, indent=2)
            messages.append({
                "role": "system",
                "content": f"You are helping with a Rosh program. Current state:\n{context_str}"
            })

        # Add user message
        messages.append({
            "role": "user",
            "content": message
        })

        # Make API call
        client = openai.OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=kwargs.get('temperature', 0.7),
            max_tokens=kwargs.get('max_tokens', 1000)
        )

        return response.choices[0].message.content


class AnthropicProvider(AIProvider):
    """Anthropic provider (Claude)"""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key
        self.model = model

    def prompt(self, message: str, context: Optional[Dict] = None, **kwargs) -> str:
        """Send prompt to Anthropic"""
        try:
            import anthropic
        except ImportError:
            raise ImportError(
                "Anthropic package not installed. Run: pip install anthropic"
            )

        # Build prompt with context
        full_prompt = message
        if context:
            context_str = json.dumps(context, indent=2)
            full_prompt = f"Current program state:\n{context_str}\n\n{message}"

        # Make API call
        client = anthropic.Anthropic(api_key=self.api_key)
        response = client.messages.create(
            model=self.model,
            max_tokens=kwargs.get('max_tokens', 1000),
            messages=[{
                "role": "user",
                "content": full_prompt
            }]
        )

        return response.content[0].text


def get_provider(provider_name: str, api_key: str, model: Optional[str] = None) -> AIProvider:
    """
    Factory function to get AI provider instance

    Args:
        provider_name: Name of provider ('openai', 'anthropic', etc.)
        api_key: API key for the provider
        model: Optional model name override

    Returns:
        AIProvider instance
    """
    providers = {
        'openai': lambda: OpenAIProvider(api_key, model or "gpt-4o-mini"),
        'anthropic': lambda: AnthropicProvider(api_key, model or "claude-3-5-sonnet-20241022"),
    }

    if provider_name not in providers:
        raise ValueError(
            f"Unknown AI provider: {provider_name}. "
            f"Available: {', '.join(providers.keys())}"
        )

    return providers[provider_name]()
