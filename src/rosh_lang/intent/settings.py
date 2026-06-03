"""Configuration for optional AI-backed intent planning."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping


_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


@dataclass(frozen=True, slots=True)
class IntentSettings:
    enabled: bool = False
    provider: str = ""
    model: str = ""
    api_key: str = ""
    max_tokens: int = 1200

    @classmethod
    def from_state(
        cls,
        state: Mapping[str, Any],
        *,
        environ: Mapping[str, str] | None = None,
    ) -> "IntentSettings":
        env = environ if environ is not None else os.environ
        ai_state = state.get("_ai")
        if not isinstance(ai_state, Mapping):
            ai_state = {}

        enabled = _as_bool(ai_state.get("enabled"), default=_env_bool(env.get("ROSH_AI")))
        provider = str(ai_state.get("provider") or env.get("ROSH_AI_PROVIDER") or "").strip().lower()
        model = str(ai_state.get("model") or env.get("ROSH_AI_MODEL") or "").strip()
        max_tokens = _as_int(ai_state.get("max_tokens") or env.get("ROSH_AI_MAX_TOKENS"), default=1200)

        api_key = str(ai_state.get("api_key") or env.get("ROSH_AI_API_KEY") or "").strip()
        if not api_key and provider == "anthropic":
            api_key = str(env.get("ANTHROPIC_API_KEY") or "").strip()

        return cls(
            enabled=enabled,
            provider=provider,
            model=model,
            api_key=api_key,
            max_tokens=max_tokens,
        )

    @property
    def available(self) -> bool:
        return bool(self.enabled and self.provider and self.model and self.api_key)


def _env_bool(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in _TRUE_VALUES


def _as_bool(value: Any, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    lowered = str(value).strip().lower()
    if lowered in _TRUE_VALUES:
        return True
    if lowered in _FALSE_VALUES:
        return False
    return default


def _as_int(value: Any, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(100, min(parsed, 8000))
