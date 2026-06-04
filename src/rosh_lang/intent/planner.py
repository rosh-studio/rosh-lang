"""Optional AI-backed planner that turns broad intent into strict Rosh."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

from rosh_lang.intent.prompts import SYSTEM_PROMPT, build_user_prompt
from rosh_lang.intent.providers import IntentProvider, IntentProviderError, provider_from_settings
from rosh_lang.intent.settings import IntentSettings
from rosh_lang.intent.validate import validate_generated_rosh


@dataclass(frozen=True, slots=True)
class IntentPlan:
    original: str
    rosh: str
    notes: str = ""


class IntentPlanner:
    """Plan strict Rosh from broad user intent when an AI provider is configured."""

    def __init__(
        self,
        *,
        settings: IntentSettings | None = None,
        provider: IntentProvider | None = None,
    ) -> None:
        self.settings = settings or IntentSettings()
        self.provider = provider if provider is not None else provider_from_settings(self.settings)

    @classmethod
    def from_state(cls, state: Mapping[str, Any]) -> "IntentPlanner":
        settings = IntentSettings.from_state(state)
        return cls(settings=settings)

    @property
    def available(self) -> bool:
        return self.provider is not None

    def plan(
        self,
        intent: str,
        *,
        state: Mapping[str, Any],
        components: list[str] | None = None,
    ) -> IntentPlan | None:
        if self.provider is None:
            return None

        prompt = build_user_prompt(
            intent,
            state_summary=_summarise_state(state),
            component_summary=_summarise_components(components),
        )
        try:
            raw = self.provider.complete(system=SYSTEM_PROMPT, prompt=prompt)
        except IntentProviderError:
            return None

        plan = _parse_plan(intent, raw)
        if plan is None:
            return None

        validation = validate_generated_rosh(plan.rosh)
        if not validation.ok:
            return None
        return plan


def _parse_plan(original: str, raw: str) -> IntentPlan | None:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.startswith("json"):
            text = text[4:].strip()

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None

    rosh = str(payload.get("rosh") or "").strip()
    notes = str(payload.get("notes") or "").strip()
    return IntentPlan(original=original, rosh=rosh, notes=notes)


def _summarise_state(state: Mapping[str, Any]) -> str:
    visible = {key: value for key, value in state.items() if not str(key).startswith("_")}
    if not visible:
        return "(empty)"
    lines: list[str] = []
    for key, value in sorted(visible.items()):
        if isinstance(value, Mapping):
            fields = ", ".join(
                f"{k}={v!r}"
                for k, v in sorted(value.items())
                if not str(k).startswith("_")
            )
            lines.append(f"{key}: object {{{fields}}}")
        else:
            lines.append(f"{key}: {value!r}")
    return "\n".join(lines)


def _summarise_components(components: list[str] | None = None) -> str:
    """Return a component manifest for the AI planner.

    If components is provided it is treated as a name filter; otherwise all
    bundled components are discovered and their provides/requires/exposes
    metadata is included so the planner can reason about component contracts
    without reading source.
    """
    from rosh_lang.core.widgets import get_bundled_library_path, parse_metadata

    library = get_bundled_library_path()
    name_filter = set(components) if components else None

    lines: list[str] = []
    for path in sorted(library.iterdir()):
        if path.suffix not in (".rosh", ".py"):
            continue
        if path.name.startswith("_"):
            continue
        name = path.stem
        if name_filter and name not in name_filter:
            continue
        try:
            meta = parse_metadata(path)
        except Exception:
            continue

        desc = meta.get("description", "")
        provides = meta.get("provides", [])
        requires = meta.get("requires", [])
        exposes = meta.get("exposes", [])
        config_keys = list(meta.get("config", {}).keys())

        parts = [f"- {name}"]
        if desc:
            parts.append(f": {desc}")
        detail: list[str] = []
        if config_keys:
            detail.append(f"config: {' '.join(config_keys)}")
        if provides:
            detail.append(f"provides: {' '.join(provides)}")
        if requires:
            detail.append(f"requires: {' '.join(requires)}")
        if exposes:
            detail.append(f"exposes: {' '.join(exposes)}")
        if detail:
            parts.append(f" [{', '.join(detail)}]")
        lines.append("".join(parts))

    return "\n".join(lines) if lines else "(none)"
