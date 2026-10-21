"""Provider abstraction for optional AI intent planning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from rosh_lang.intent.settings import IntentSettings


class IntentProviderError(RuntimeError):
    """Raised when an intent provider cannot complete a planning request."""


class IntentProvider(Protocol):
    def complete(self, *, system: str, prompt: str) -> str:
        """Return model text for a planning prompt."""


@dataclass(slots=True)
class AnthropicIntentProvider:
    settings: IntentSettings

    def complete(self, *, system: str, prompt: str) -> str:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - depends on optional extra
            raise IntentProviderError(
                "Install rosh-lang[ai] to use the anthropic intent provider."
            ) from exc

        client = anthropic.Anthropic(api_key=self.settings.api_key)
        try:
            response = client.messages.create(
                model=self.settings.model,
                max_tokens=self.settings.max_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:  # pragma: no cover - network/provider failure
            raise IntentProviderError(str(exc)) from exc

        chunks: list[str] = []
        for block in response.content:
            text = getattr(block, "text", None)
            if text:
                chunks.append(str(text))
        return "\n".join(chunks).strip()


def provider_from_settings(settings: IntentSettings) -> IntentProvider | None:
    if not settings.available:
        return None
    if settings.provider == "anthropic":
        return AnthropicIntentProvider(settings=settings)
    return None
