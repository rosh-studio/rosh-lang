from __future__ import annotations

import json
from dataclasses import dataclass

import pytest

from rosh_lang.intent.planner import IntentPlan, IntentPlanner
from rosh_lang.intent.providers import IntentProviderError, provider_from_settings
from rosh_lang.intent.settings import IntentSettings
from rosh_lang.intent.validate import validate_generated_rosh
from rosh_lang.repl import kernel as repl_kernel
from rosh_lang.repl.kernel import ReplKernel
from rosh_lang.repl.runtime_adapter import RuntimeAdapter


@dataclass(slots=True)
class FakeProvider:
    response: str
    prompts: list[tuple[str, str]]

    def complete(self, *, system: str, prompt: str) -> str:
        self.prompts.append((system, prompt))
        return self.response


class FailingProvider:
    def complete(self, *, system: str, prompt: str) -> str:
        raise IntentProviderError("provider failed")


def test_intent_settings_require_enable_provider_model_and_key() -> None:
    settings = IntentSettings.from_state({}, environ={})

    assert settings.available is False

    settings = IntentSettings.from_state(
        {},
        environ={
            "ROSH_AI": "1",
            "ROSH_AI_PROVIDER": "anthropic",
            "ROSH_AI_MODEL": "test-model",
            "ANTHROPIC_API_KEY": "secret",
        },
    )

    assert settings.available is True
    assert settings.provider == "anthropic"
    assert settings.model == "test-model"


def test_intent_settings_can_be_overridden_from_rosh_state() -> None:
    adapter = RuntimeAdapter()
    adapter.run_source("set _ai.enabled to true")
    adapter.run_source("set _ai.provider to anthropic")
    adapter.run_source("set _ai.model to state-model")

    settings = IntentSettings.from_state(
        adapter.runtime.state,
        environ={
            "ROSH_AI": "0",
            "ROSH_AI_PROVIDER": "other",
            "ROSH_AI_MODEL": "env-model",
            "ANTHROPIC_API_KEY": "secret",
        },
    )

    assert settings.available is True
    assert settings.provider == "anthropic"
    assert settings.model == "state-model"


def test_intent_settings_clamp_max_tokens() -> None:
    low = IntentSettings.from_state({}, environ={"ROSH_AI_MAX_TOKENS": "1"})
    high = IntentSettings.from_state({}, environ={"ROSH_AI_MAX_TOKENS": "999999"})

    assert low.max_tokens == 100
    assert high.max_tokens == 8000


def test_provider_from_settings_requires_available_settings() -> None:
    assert provider_from_settings(IntentSettings()) is None


def test_provider_from_settings_returns_anthropic_provider() -> None:
    settings = IntentSettings(
        enabled=True,
        provider="anthropic",
        model="test-model",
        api_key="secret",
    )

    provider = provider_from_settings(settings)

    assert provider is not None
    assert provider.__class__.__name__ == "AnthropicIntentProvider"


def test_validate_generated_rosh_accepts_strict_rosh() -> None:
    result = validate_generated_rosh("create object moon\nset moon.color to silver")

    assert result.ok is True
    assert result.programme is not None
    assert len(result.programme.statements) == 2


def test_validate_generated_rosh_rejects_empty_code() -> None:
    result = validate_generated_rosh("")

    assert result.ok is False
    assert "no Rosh code" in result.error


def test_validate_generated_rosh_rejects_invalid_code() -> None:
    result = validate_generated_rosh("invent magic")

    assert result.ok is False
    assert "Unknown keyword" in result.error


def test_validate_generated_rosh_rejects_unclosed_when() -> None:
    result = validate_generated_rosh("when click\nprint hello")

    assert not result.ok
    assert "when block has no matching end" in result.error


def test_planner_returns_valid_plan_from_json_response() -> None:
    provider = FakeProvider(
        response=json.dumps({
            "rosh": "create object moon\nset moon.color to silver",
            "notes": "Created a moon.",
        }),
        prompts=[],
    )
    planner = IntentPlanner(provider=provider)

    plan = planner.plan(
        "imagine a moonlit clearing",
        state={"campfire": {"color": "orange"}, "_secret": "hidden"},
        components=["score"],
    )

    assert plan == IntentPlan(
        original="imagine a moonlit clearing",
        rosh="create object moon\nset moon.color to silver",
        notes="Created a moon.",
    )
    assert provider.prompts
    _system, prompt = provider.prompts[0]
    assert "campfire: object" in prompt
    assert "_secret" not in prompt
    assert "- score" in prompt


def test_planner_accepts_json_in_markdown_fence() -> None:
    provider = FakeProvider(
        response='```json\n{"rosh": "create object moon", "notes": ""}\n```',
        prompts=[],
    )
    planner = IntentPlanner(provider=provider)

    plan = planner.plan("make a moon", state={})

    assert plan is not None
    assert plan.rosh == "create object moon"


def test_planner_returns_none_for_invalid_json() -> None:
    planner = IntentPlanner(provider=FakeProvider(response="not json", prompts=[]))

    assert planner.plan("make a moon", state={}) is None


def test_planner_returns_none_for_invalid_rosh() -> None:
    provider = FakeProvider(
        response=json.dumps({"rosh": "invent magic", "notes": ""}),
        prompts=[],
    )
    planner = IntentPlanner(provider=provider)

    assert planner.plan("make magic", state={}) is None


def test_planner_returns_none_when_provider_fails() -> None:
    planner = IntentPlanner(provider=FailingProvider())

    assert planner.plan("make a moon", state={}) is None


def test_kernel_uses_intent_planner_for_unknown_broad_intent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakePlanner:
        available = True

        @classmethod
        def from_state(cls, _state: dict[str, object]) -> "FakePlanner":
            return cls()

        def plan(self, intent: str, *, state: dict[str, object], target: str = "terminal", **_kw) -> IntentPlan:
            assert intent == "imagine a moonlit clearing"
            return IntentPlan(
                original=intent,
                rosh="\n".join([
                    "create object moon",
                    "set moon.shape to sphere",
                    "set moon.color to silver",
                ]),
                notes="Created a small moon object.",
            )

    monkeypatch.setattr(repl_kernel, "IntentPlanner", FakePlanner)
    kernel = ReplKernel(RuntimeAdapter())

    response = kernel.process_line("imagine a moonlit clearing")

    assert response.status == "ok"
    assert response.planned_rosh.startswith("create object moon")
    assert response.planner_notes == "Created a small moon object."
    assert kernel.current_subject == "moon"
    assert kernel.adapter.runtime.state["moon"]["shape"] == "sphere"


def test_kernel_leaves_broad_intent_as_error_without_configured_planner() -> None:
    kernel = ReplKernel(RuntimeAdapter())

    response = kernel.process_line("imagine a moonlit clearing")

    assert response.status == "error"
    assert response.planned_rosh == ""
    assert "Unknown keyword" in (response.error.message if response.error else "")


def test_kernel_does_not_use_intent_planner_for_keyword_typo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingPlanner:
        @classmethod
        def from_state(cls, _state: dict[str, object]) -> "FailingPlanner":
            raise AssertionError("planner should not be used for typo suggestions")

    monkeypatch.setattr(repl_kernel, "IntentPlanner", FailingPlanner)
    kernel = ReplKernel(RuntimeAdapter())

    response = kernel.process_line("creare object moon")

    assert response.status == "error"
    assert response.error is not None
    assert "create" in response.error.suggestions


# ── Target capability manifest ────────────────────────────────────


def test_summarise_target_terminal() -> None:
    from rosh_lang.intent.planner import _summarise_target
    summary = _summarise_target("terminal")
    assert "terminal" in summary
    assert "after" in summary        # listed as no-op
    assert "get" in summary          # supported
    assert "background" in summary   # supported as observable state


def test_summarise_target_web() -> None:
    from rosh_lang.intent.planner import _summarise_target
    summary = _summarise_target("web")
    assert "get" in summary          # listed as absent
    assert "after" in summary        # listed as supported


def test_summarise_target_world() -> None:
    from rosh_lang.intent.planner import _summarise_target
    summary = _summarise_target("world")
    assert "world" in summary
    assert "when" in summary         # listed as absent in world


def test_summarise_target_scratch_matches_capability_table() -> None:
    from rosh_lang.intent.planner import _summarise_target
    summary = _summarise_target("scratch")
    supported, absent = summary.split("Absent (do not use):", 1)
    assert "after" in supported
    assert "go" not in supported
    assert "go" in absent


def test_summarise_target_unknown() -> None:
    from rosh_lang.intent.planner import _summarise_target
    summary = _summarise_target("unknown-target")
    assert "unknown" in summary.lower() or "capability profile unknown" in summary


def test_build_user_prompt_includes_target() -> None:
    from rosh_lang.intent.prompts import build_user_prompt
    prompt = build_user_prompt(
        "create a planet",
        state_summary="(empty)",
        component_summary="- score",
        target_summary="Target: web\n  Supported: print say",
    )
    assert "Target: web" in prompt
    assert "create a planet" in prompt


def test_build_user_prompt_omits_target_when_empty() -> None:
    from rosh_lang.intent.prompts import build_user_prompt
    prompt = build_user_prompt(
        "create a planet",
        state_summary="(empty)",
        component_summary="- score",
    )
    assert "Active target" not in prompt


def test_planner_passes_target_to_prompt() -> None:
    """plan() with target='web' produces a prompt that mentions the web target."""
    from rosh_lang.intent.planner import IntentPlanner, IntentPlan

    captured: list[str] = []

    class CapturingProvider:
        def complete(self, *, system: str, prompt: str) -> str:
            captured.append(prompt)
            return '{"rosh": "create object box", "notes": ""}'

    planner = IntentPlanner(provider=CapturingProvider())
    planner.plan("make a box", state={}, target="web")
    assert captured, "provider was never called"
    assert "Target: web" in captured[0]
    assert "absent" in captured[0].lower()   # web lists get/connect/look as absent
