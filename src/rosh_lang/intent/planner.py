"""Optional AI-backed planner that turns broad intent into strict Rosh."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Mapping

_log = logging.getLogger(__name__)

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
        target: str = "terminal",
    ) -> IntentPlan | None:
        if self.provider is None:
            return None

        prompt = build_user_prompt(
            intent,
            state_summary=_summarise_state(state),
            component_summary=_summarise_components(components),
            target_summary=_summarise_target(target),
        )
        try:
            raw = self.provider.complete(system=SYSTEM_PROMPT, prompt=prompt)
        except IntentProviderError as exc:
            _log.warning("IntentPlanner: provider error: %s", exc)
            return None

        plan = _parse_plan(intent, raw)
        if plan is None:
            _log.warning("IntentPlanner: could not parse plan from response: %r", raw[:200])
            return None

        validation = validate_generated_rosh(plan.rosh)
        if not validation.ok:
            _log.warning("IntentPlanner: generated Rosh failed validation: %s", validation.error)
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


_TARGET_CAPS: dict[str, dict[str, str]] = {
    "terminal": {
        "supported": (
            "print say create set destroy send event on when if repeat "
            "for-each add remove define do look get connect go background"
        ),
        "no-op": "after sprite sound play animate",
        "absent": "",
        "notes": (
            "after/sprite/sound/play/animate parse without error but produce no effect. "
            "background stores state but has no visual effect. "
            "get and look return state data. connect stores a named URL."
        ),
    },
    "web": {
        "supported": (
            "print say create set destroy send event on when if repeat "
            "for-each add remove define do go after sprite sound play animate background"
        ),
        "no-op": "",
        "absent": "get connect look",
        "notes": (
            "Full interactive runtime. after fires setTimeout. "
            "get/connect/look have no JS equivalent — omit them."
        ),
    },
    "phaser": {
        "supported": (
            "print say create set destroy send event on when if repeat "
            "for-each add remove define do go after sprite sound play animate background"
        ),
        "no-op": "",
        "absent": "get connect look",
        "notes": "Same as web but renders with Phaser 3. get/connect/look absent.",
    },
    "threejs": {
        "supported": (
            "print say create set destroy send event on when if repeat "
            "for-each add remove define do go after sprite sound play animate background"
        ),
        "no-op": "",
        "absent": "get connect look",
        "notes": "Same as web but renders in Three.js 3D. get/connect/look absent.",
    },
    "scratch": {
        "supported": (
            "print say create set destroy send on when if repeat "
            "define do after sound play background"
        ),
        "no-op": "",
        "absent": "event for-each add remove get connect look go animate sprite",
        "notes": (
            "Scratch export. event/for-each/add/remove/go/animate/sprite absent. "
            "Custom events cannot be declared. after compiles to wait then broadcast. "
            "No scene or collection operations."
        ),
    },
    "world": {
        "supported": "print say create set destroy go look connect",
        "no-op": "",
        "absent": (
            "when on if repeat for-each add remove define do event send after "
            "sprite sound play animate background"
        ),
        "notes": (
            "World target is highly restricted — only 8 statements are supported. "
            "No event handlers, no conditionals, no loops, no components."
        ),
    },
}


def _summarise_target(target: str) -> str:
    """Return a one-paragraph description of what the active target supports."""
    info = _TARGET_CAPS.get(target.lower())
    if info is None:
        return f"Target '{target}' — capability profile unknown; use conservative Rosh."
    lines = [f"Target: {target}"]
    lines.append(f"  Supported: {info['supported']}")
    if info["no-op"]:
        lines.append(f"  No-op (parse OK, no effect): {info['no-op']}")
    if info["absent"]:
        lines.append(f"  Absent (do not use): {info['absent']}")
    lines.append(f"  Note: {info['notes']}")
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
