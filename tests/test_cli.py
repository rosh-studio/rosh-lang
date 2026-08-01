from __future__ import annotations

import io
import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

from rosh_lang import __main__ as cli
from rosh_lang.cli import cloud
from rosh_lang.repl import shell as repl_shell
from rosh_lang.repl.kernel import ReplKernel, canonical_help_topic, usage_error_for_command
from rosh_lang.repl.natural import lower_shell_input
from rosh_lang.repl.runtime_adapter import RuntimeAdapter
from rosh_lang.core.runtime import Runtime


class _FakeResponse:
    def __init__(self, data: dict) -> None:
        self.data = data

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.data).encode()


def test_cloud_config_is_saved_with_private_permissions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_dir = tmp_path / ".rosh"
    config_file = config_dir / "config.json"
    monkeypatch.setattr(cloud, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(cloud, "CONFIG_FILE", config_file)

    cloud._save_config({"api_key": "rosh_k1_test"})

    assert config_dir.stat().st_mode & 0o777 == 0o700
    assert config_file.stat().st_mode & 0o777 == 0o600


def test_cloud_get_retries_transient_http_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    responses: list[object] = [
        HTTPError("https://rosh.cloud/api/v1/docs", 522, None, {}, io.BytesIO(b"")),
        _FakeResponse({"version": "0.8.0"}),
    ]

    def next_response(*_args: object, **_kwargs: object) -> object:
        response = responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response

    monkeypatch.setattr(cloud, "urlopen", next_response)
    monkeypatch.setattr(cloud.time, "sleep", lambda _seconds: None)

    result = cloud._fetch_docs("rosh_k1_test")

    assert result == {"version": "0.8.0"}
    assert "Temporary error 522; retrying" in capsys.readouterr().out


def test_cloud_post_does_not_retry_transient_http_error(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls = 0

    def fail(*_args: object, **_kwargs: object) -> None:
        nonlocal calls
        calls += 1
        raise HTTPError("https://rosh.cloud/api/v1/programs", 522, None, {}, io.BytesIO(b""))

    monkeypatch.setattr(cloud, "urlopen", fail)

    with pytest.raises(SystemExit):
        cloud._api_request("POST", "/api/v1/programs", {"title": "test"})

    assert calls == 1
    assert "Error 522: rosh.cloud temporarily unavailable after 1 attempt" in capsys.readouterr().out


def test_api_request_non_fatal_returns_error_dict_instead_of_exiting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*_args: object, **_kwargs: object) -> None:
        raise HTTPError("https://rosh.cloud/api/v1/worlds", 500, None, {}, io.BytesIO(b'{"error": "boom"}'))

    monkeypatch.setattr(cloud, "urlopen", fail)

    result = cloud._api_request("POST", "/api/v1/worlds", {"slug": "x"}, fatal=False)

    assert result["success"] is False
    assert result["status"] == 500
    assert "boom" in result["error"]


def test_push_world_falls_back_to_put_on_slug_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str]] = []

    def fake_urlopen(req: object, timeout: int = 30) -> object:
        method = req.get_method()  # type: ignore[attr-defined]
        url = req.full_url  # type: ignore[attr-defined]
        calls.append((method, url))
        if method == "POST":
            raise HTTPError(url, 409, None, {}, io.BytesIO(json.dumps({"code": "slug_exists", "error": "dup"}).encode()))
        return _FakeResponse({"success": True, "slug": "my-world", "owner": "alice"})

    monkeypatch.setattr(cloud, "urlopen", fake_urlopen)

    result = cloud.push_world("my-world", "create object cube", api_key="rosh_k1_test")

    assert result["success"] is True
    assert [m for m, _ in calls] == ["POST", "PUT"]
    assert calls[1][1].endswith("/api/v1/worlds/my-world")


def test_kernel_push_appends_only_executed_source_not_builtins() -> None:
    kernel = ReplKernel(RuntimeAdapter())

    kernel.process_line("create object cube")
    kernel.process_line("state")
    kernel.process_line("help")
    kernel.process_line("this is not valid rosh at all !!!")
    kernel.process_line("set cube.color to red")

    assert kernel.session_lines == ["create object cube", "set cube.color to red"]


def test_kernel_push_reports_no_api_key_without_exiting(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cloud, "get_api_key_or_none", lambda: None)

    kernel = ReplKernel(RuntimeAdapter())
    kernel.process_line("create object cube")
    response = kernel.process_line("push my-world")

    assert response.status == "error"
    assert response.error is not None
    assert "No API key configured" in response.error.message


def test_kernel_bare_push_gives_usage_error() -> None:
    kernel = ReplKernel(RuntimeAdapter())
    response = kernel.process_line("push")

    assert response.status == "error"
    assert response.error is not None
    assert "push <slug>" in response.error.guidance


def test_runtime_adapter_get_state_filters_internal_keys() -> None:
    adapter = RuntimeAdapter()
    adapter.runtime.state["player"] = {"x": 1}
    adapter.runtime.state["_scene"] = "intro"

    items = adapter.get_state()

    assert [item.key for item in items] == ["player"]


def test_cli_scratch_target_writes_sb3(tmp_path: Path) -> None:
    source = tmp_path / "ball.rosh"
    source.write_text(
        "\n".join([
            "create object ball",
            "set ball.shape to circle",
            "set ball.color to red",
        ]),
        encoding="utf-8",
    )

    result = cli.main([str(source), "--target", "scratch"])

    assert result == 0
    assert (tmp_path / "ball.sb3").exists()


def test_cli_assets_search_outputs_candidates(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    requests = tmp_path / "requests.json"
    requests.write_text(
        json.dumps([{"query": "pictish stone", "target": "threejs"}]),
        encoding="utf-8",
    )

    result = cli.main(["assets", "search", str(requests), "--provider", "mock", "--limit", "1"])

    assert result == 0
    data = json.loads(capsys.readouterr().out)
    assert data[0]["provider"] == "mock"
    assert data[0]["candidates"][0]["id"] == "mock_pictish_stone"


def test_cli_assets_search_reports_missing_file(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        cli.main(["assets", "search", "/tmp/does-not-exist-rosh-assets.json"])

    assert "AssetError:" in capsys.readouterr().err


def test_cli_assets_search_reports_invalid_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    requests = tmp_path / "bad.json"
    requests.write_text("{not json", encoding="utf-8")

    with pytest.raises(SystemExit):
        cli.main(["assets", "search", str(requests)])

    assert "invalid JSON" in capsys.readouterr().err


def test_cli_assets_search_reports_unknown_provider(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    requests = tmp_path / "requests.json"
    requests.write_text(json.dumps([{"query": "stone"}]), encoding="utf-8")

    with pytest.raises(SystemExit):
        cli.main(["assets", "search", str(requests), "--provider", "nope"])

    assert "unknown provider" in capsys.readouterr().err


def test_cli_assets_search_limit_zero_clamps_to_one(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    requests = tmp_path / "requests.json"
    requests.write_text(json.dumps([{"query": "pictish stone"}]), encoding="utf-8")

    result = cli.main(["assets", "search", str(requests), "--limit", "0"])

    assert result == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data[0]["candidates"]) == 1


def test_runtime_adapter_lists_top_level_dicts_as_objects() -> None:
    adapter = RuntimeAdapter()
    adapter.runtime.state["player"] = {"x": 1, "y": 2}
    adapter.runtime.state["score"] = 10

    objects = adapter.list_objects()

    assert len(objects) == 1
    assert objects[0].name == "player"
    assert objects[0].fields == ["x", "y"]


def test_runtime_adapter_returns_look_results_for_state_view() -> None:
    adapter = RuntimeAdapter()
    adapter.runtime.state["player"] = {"x": 1}

    _programme, view, items = adapter.run_source("look")

    assert view == "state"
    assert [item.key for item in items] == ["player"]


def test_kernel_bare_name_convenience_uses_get() -> None:
    adapter = RuntimeAdapter()
    adapter.runtime.state["player"] = {"x": 1}
    kernel = ReplKernel(adapter)

    response = kernel.process_line("player")

    assert response.view == "get"
    assert response.state_items[0].key == "player"


def test_kernel_reports_help_topic() -> None:
    kernel = ReplKernel(RuntimeAdapter())

    response = kernel.process_line("help set")

    assert response.view == "help"
    assert response.help_topic == "set"


def test_help_alias_maps_to_canonical_topic() -> None:
    assert canonical_help_topic("inspect") == "look"


def test_kernel_maps_examine_alias_to_look() -> None:
    adapter = RuntimeAdapter()
    adapter.runtime.state["player"] = {"x": 1}
    kernel = ReplKernel(adapter)

    response = kernel.process_line("examine player")

    assert response.view == "get"
    assert response.state_items[0].key == "player"


def test_kernel_maps_ls_alias_to_list_objects() -> None:
    adapter = RuntimeAdapter()
    adapter.runtime.state["player"] = {"x": 1}
    kernel = ReplKernel(adapter)

    response = kernel.process_line("ls")

    assert response.view == "objects"
    assert response.object_items[0].name == "player"


def test_kernel_suggests_keyword_for_typo() -> None:
    kernel = ReplKernel(RuntimeAdapter())

    response = kernel.process_line("creare object player")

    assert response.status == "error"
    assert response.error is not None
    assert "create" in response.error.suggestions


def test_usage_error_for_incomplete_set_includes_examples() -> None:
    error = usage_error_for_command("set")

    assert error is not None
    assert error.kind == "shell"
    assert error.guidance[0] == "set <target> to <value>"


def test_kernel_returns_shell_usage_error_for_incomplete_command() -> None:
    kernel = ReplKernel(RuntimeAdapter())

    response = kernel.process_line("set")

    assert response.status == "error"
    assert response.error is not None
    assert response.error.kind == "shell"
    assert "set <target> to <value>" in response.error.guidance


def test_runtime_adapter_guides_parse_error_for_incomplete_set() -> None:
    adapter = RuntimeAdapter()

    try:
        adapter.run_source("set")
    except Exception as exc:
        error = adapter.format_error(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected parse error")

    assert error.kind == "parse"
    assert "set <target> to <value>" in error.guidance


def test_runtime_adapter_suggests_property_for_look_typo() -> None:
    adapter = RuntimeAdapter()
    adapter.runtime.state["ball"] = {"color": "red"}

    try:
        adapter.run_source("look ball.colr")
    except Exception as exc:
        error = adapter.format_error(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected runtime error")

    assert error.kind == "runtime"
    assert "ball.color" in error.suggestions


def test_natural_lowering_turns_big_red_ball_into_strict_rosh() -> None:
    lowered = lower_shell_input("create a big red ball")

    assert lowered.changed is True
    assert lowered.text == "\n".join([
        "create object ball",
        "set ball.shape to circle",
        "set ball.color to red",
        "set ball.width to 0.16",
        "set ball.height to 0.16",
        "set ball.depth to 0.16",
        "set ball.x to 0.5",
        "set ball.y to 0.5",
    ])
    assert lowered.subject == "ball"


def test_natural_lowering_leaves_strict_create_alone() -> None:
    lowered = lower_shell_input("create object ball")

    assert lowered.changed is False
    assert lowered.text == "create object ball"


def test_natural_lowering_turns_make_ball_blue_into_set() -> None:
    lowered = lower_shell_input("make ball blue")

    assert lowered.changed is True
    assert lowered.text == "set ball.color to blue"
    assert lowered.subject == "ball"


def test_natural_lowering_uses_current_subject_for_make_it_blue() -> None:
    lowered = lower_shell_input("make it blue", current_subject="ball")

    assert lowered.changed is True
    assert lowered.text == "set ball.color to blue"
    assert lowered.subject == "ball"


def test_natural_lowering_turns_move_it_to_center_into_xy_set() -> None:
    lowered = lower_shell_input("move it to center", current_subject="ball")

    assert lowered.changed is True
    assert lowered.text == "\n".join([
        "set ball.x to 0.5",
        "set ball.y to 0.5",
    ])
    assert lowered.subject == "ball"


def test_natural_lowering_turns_move_ball_to_numeric_position_into_xy_set() -> None:
    lowered = lower_shell_input("move ball to 25 75")

    assert lowered.changed is True
    assert lowered.text == "\n".join([
        "set ball.x to 0.25",
        "set ball.y to 0.75",
    ])
    assert lowered.subject == "ball"


def test_natural_lowering_turns_make_the_ball_green_into_set() -> None:
    lowered = lower_shell_input("make the ball green")

    assert lowered.changed is True
    assert lowered.text == "set ball.color to green"
    assert lowered.subject == "ball"


def test_natural_lowering_turns_make_it_smaller_into_relative_size_set() -> None:
    lowered = lower_shell_input("make it smaller", current_subject="ball")

    assert lowered.changed is True
    assert lowered.text == "\n".join([
        "set ball.width to ball.width * 0.75",
        "set ball.height to ball.height * 0.75",
        "set ball.depth to ball.depth * 0.75",
    ])
    assert lowered.subject == "ball"


def test_natural_lowering_turns_move_it_left_into_relative_position_set() -> None:
    lowered = lower_shell_input("move it left", current_subject="ball")

    assert lowered.changed is True
    assert lowered.text == "set ball.x to ball.x - 0.1"
    assert lowered.subject == "ball"


def test_natural_lowering_turns_put_the_ball_at_numeric_position_into_xy_set() -> None:
    lowered = lower_shell_input("put the ball at 40 60")

    assert lowered.changed is True
    assert lowered.text == "\n".join([
        "set ball.x to 0.4",
        "set ball.y to 0.6",
    ])
    assert lowered.subject == "ball"


def test_kernel_executes_natural_create_phrase() -> None:
    kernel = ReplKernel(RuntimeAdapter())

    response = kernel.process_line("create a big red ball")

    assert response.status == "ok"
    assert kernel.adapter.runtime.state["ball"]["shape"] == "circle"
    assert kernel.adapter.runtime.state["ball"]["color"] == "red"
    assert kernel.adapter.runtime.state["ball"]["width"] == 0.16


def test_kernel_executes_natural_sprite_phrase() -> None:
    kernel = ReplKernel(RuntimeAdapter())

    response = kernel.process_line("make a small blue spaceship")

    assert response.status == "ok"
    assert kernel.adapter.runtime.state["spaceship"]["sprite"] == "blue spaceship"
    assert kernel.adapter.runtime.state["spaceship"]["color"] == "blue"
    assert kernel.adapter.runtime.state["spaceship"]["width"] == 0.07


def test_kernel_uses_current_subject_for_make_it_blue() -> None:
    kernel = ReplKernel(RuntimeAdapter())

    kernel.process_line("create object ball")
    response = kernel.process_line("make it blue")

    assert response.status == "ok"
    assert kernel.adapter.runtime.state["ball"]["color"] == "blue"


def test_kernel_uses_current_subject_for_move_it_to_center() -> None:
    kernel = ReplKernel(RuntimeAdapter())

    kernel.process_line("create object ball")
    response = kernel.process_line("move it to center")

    assert response.status == "ok"
    assert kernel.adapter.runtime.state["ball"]["x"] == 0.5
    assert kernel.adapter.runtime.state["ball"]["y"] == 0.5


def test_kernel_moves_named_object_to_numeric_position() -> None:
    kernel = ReplKernel(RuntimeAdapter())

    kernel.process_line("create object ball")
    response = kernel.process_line("move ball to 25 75")

    assert response.status == "ok"
    assert kernel.adapter.runtime.state["ball"]["x"] == 0.25
    assert kernel.adapter.runtime.state["ball"]["y"] == 0.75


def test_kernel_makes_the_ball_green() -> None:
    kernel = ReplKernel(RuntimeAdapter())

    kernel.process_line("create object ball")
    response = kernel.process_line("make the ball green")

    assert response.status == "ok"
    assert kernel.adapter.runtime.state["ball"]["color"] == "green"


def test_kernel_makes_it_smaller_relative_to_current_size() -> None:
    kernel = ReplKernel(RuntimeAdapter())

    kernel.process_line("create a big red ball")
    response = kernel.process_line("make it smaller")

    assert response.status == "ok"
    assert kernel.adapter.runtime.state["ball"]["width"] == 0.12
    assert kernel.adapter.runtime.state["ball"]["height"] == 0.12
    assert kernel.adapter.runtime.state["ball"]["depth"] == 0.12


def test_kernel_moves_it_left_relative_to_current_position() -> None:
    kernel = ReplKernel(RuntimeAdapter())

    kernel.process_line("create a big red ball")
    response = kernel.process_line("move it left")

    assert response.status == "ok"
    assert kernel.adapter.runtime.state["ball"]["x"] == 0.4


def test_kernel_puts_the_ball_at_numeric_position() -> None:
    kernel = ReplKernel(RuntimeAdapter())

    kernel.process_line("create object ball")
    response = kernel.process_line("put the ball at 40 60")

    assert response.status == "ok"
    assert kernel.adapter.runtime.state["ball"]["x"] == 0.4
    assert kernel.adapter.runtime.state["ball"]["y"] == 0.6


def test_completion_matches_help_keywords() -> None:
    adapter = RuntimeAdapter()

    matches = repl_shell._completion_matches(adapter, "se", "help se", 5)

    assert "set" in matches


def test_completion_matches_list_subcommands() -> None:
    adapter = RuntimeAdapter()

    matches = repl_shell._completion_matches(adapter, "ob", "list ob", 5)

    assert matches == ["objects"]


def test_readline_bind_instruction_uses_libedit_form() -> None:
    assert repl_shell._readline_bind_instruction("libedit readline emulation") == "bind ^I rl_complete"


def test_readline_bind_instruction_uses_gnu_form() -> None:
    assert repl_shell._readline_bind_instruction("GNU readline") == "tab: complete"


def test_main_no_args_starts_repl(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[Runtime | None] = []

    def fake_start_repl(runtime: Runtime | None = None) -> None:
        called.append(runtime)

    monkeypatch.setattr(cli, "start_repl", fake_start_repl)

    result = cli.main([])

    assert result == 0
    assert called == [None]


def test_main_command_with_interactive_preserves_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[Runtime | None] = []

    def fake_start_repl(runtime: Runtime | None = None) -> None:
        called.append(runtime)

    monkeypatch.setattr(cli, "start_repl", fake_start_repl)

    result = cli.main(["-c", 'create object player', "-i"])

    assert result == 0
    assert called
    assert called[0] is not None
    assert "player" in called[0].state


def test_main_interactive_file_preserves_runtime(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    called: list[Runtime | None] = []
    script = tmp_path / "hello.rosh"
    script.write_text('create object player\n')

    def fake_start_repl(runtime: Runtime | None = None) -> None:
        called.append(runtime)

    monkeypatch.setattr(cli, "start_repl", fake_start_repl)

    result = cli.main([str(script), "-i"])

    assert result == 0
    assert called
    assert called[0] is not None
    assert "player" in called[0].state


def test_main_rejects_interactive_with_non_terminal_target() -> None:
    result = cli.main(["example.rosh", "-i", "--target", "web"])
    assert result == 2


def test_kernel_say_returns_say_view_with_text() -> None:
    kernel = ReplKernel(RuntimeAdapter())

    response = kernel.process_line('say "greetings"')

    assert response.status == "ok"
    assert response.view == "say"
    assert response.state_items[0].value == "greetings"


def test_kernel_look_object_returns_get_view_with_dict_items() -> None:
    adapter = RuntimeAdapter()
    adapter.runtime.state["ball"] = {"color": "red", "x": 0.5}
    kernel = ReplKernel(adapter)

    response = kernel.process_line("look ball")

    assert response.status == "ok"
    assert response.view == "get"
    item = response.state_items[0]
    assert item.key == "ball"
    assert isinstance(item.value, dict)
    assert item.value["color"] == "red"


def test_kernel_dotted_interpolation_in_print() -> None:
    from io import StringIO

    rt = Runtime()
    out = StringIO()
    rt.output = out
    adapter = RuntimeAdapter(runtime=rt)
    kernel = ReplKernel(adapter)

    kernel.process_line("create object ball")
    kernel.process_line("set ball.color to blue")
    kernel.process_line('print "color is {ball.color}"')

    assert "color is blue" in out.getvalue()


def test_when_say_handler_interpolates_text_payload() -> None:
    from io import StringIO

    rt = Runtime()
    out = StringIO()
    rt.output = out
    adapter = RuntimeAdapter(runtime=rt)
    kernel = ReplKernel(adapter)

    kernel.process_line('when say then\n  print "heard: {text}"\nend')
    kernel.process_line('say "hello world"')

    output = out.getvalue()
    assert "heard: hello world" in output
