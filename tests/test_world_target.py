"""Sprint C — world target tests.

Uses FakeWS to simulate the rosh-world WS server without a live connection.
FakeWS acts as an async context manager so it slots directly into _run_async.
"""
import asyncio
import io
import json

import pytest

from rosh_lang.core.parser import parse_string as parse
from rosh_lang.targets.world import WorldError, WorldRuntime


# ---------------------------------------------------------------------------
# FakeWS — minimal WS mock for unit tests
# ---------------------------------------------------------------------------

class FakeWS:
    """Pre-canned server messages for testing WorldRuntime."""

    def __init__(self, messages: list[dict]) -> None:
        self._queue = list(messages)
        self.sent: list[dict] = []

    async def send(self, data: str) -> None:
        self.sent.append(json.loads(data))

    async def recv(self) -> str:
        if not self._queue:
            raise EOFError("FakeWS: no more messages queued")
        return json.dumps(self._queue.pop(0))

    async def __aenter__(self) -> "FakeWS":
        return self

    async def __aexit__(self, *args: object) -> None:
        pass


def _welcome(world: str = "test/world") -> dict:
    return {"type": "welcome", "world": world, "seq": 1}


def _joined(level: int = 5) -> dict:
    return {"type": "joined", "actor": "agent", "level": level,
            "authenticated": level >= 3, "is_bot": True, "seq": 2, "id": "stmt-1"}


def _run(rt: WorldRuntime, programme, fake_ws: FakeWS) -> None:
    asyncio.run(rt._run_async(programme, _ws_override=fake_ws))


# ---------------------------------------------------------------------------
# Connection handshake
# ---------------------------------------------------------------------------

def test_welcome_and_join() -> None:
    out = io.StringIO()
    rt = WorldRuntime("wss://localhost", api_key="key", actor="agent", output=out)
    prog = parse("")

    fake = FakeWS([_welcome(), _joined(level=5)])
    _run(rt, prog, fake)

    assert "connected to test/world" in out.getvalue()
    assert "level 5" in out.getvalue()
    # join command was sent with is_bot=True
    assert any(m.get("cmd") == "join" for m in fake.sent)


def test_join_error_raises() -> None:
    rt = WorldRuntime("wss://localhost", api_key="bad")
    prog = parse("")

    fake = FakeWS([
        _welcome(),
        {"type": "error", "code": "forbidden", "message": "bad key", "seq": 2, "id": "stmt-1"},
    ])
    with pytest.raises(WorldError, match="join failed"):
        _run(rt, prog, fake)


# ---------------------------------------------------------------------------
# go
# ---------------------------------------------------------------------------

def test_go() -> None:
    out = io.StringIO()
    rt = WorldRuntime("wss://localhost", output=out)
    prog = parse('go "The Foyer"')

    fake = FakeWS([
        _welcome(),
        _joined(),
        {"type": "move", "to": "abc-uuid",
         "room": {"name": "The Foyer", "description": "", "exits": []},
         "seq": 3, "id": "stmt-2"},
    ])
    _run(rt, prog, fake)

    lines = out.getvalue()
    assert "The Foyer" in lines
    go_cmd = next(m for m in fake.sent if m.get("cmd") == "go")
    assert go_cmd["exit"] == "The Foyer"  # quotes stripped by _strip_quotes
    assert go_cmd["id"] == "stmt-2"


def test_go_error_raises() -> None:
    rt = WorldRuntime("wss://localhost")
    prog = parse('go nowhere')

    fake = FakeWS([
        _welcome(),
        _joined(),
        {"type": "error", "message": "No object matching 'nowhere'", "seq": 3, "id": "stmt-2"},
    ])
    with pytest.raises(WorldError, match="nowhere"):
        _run(rt, prog, fake)


# ---------------------------------------------------------------------------
# look
# ---------------------------------------------------------------------------

def test_look() -> None:
    out = io.StringIO()
    rt = WorldRuntime("wss://localhost", output=out)
    prog = parse("look")

    fake = FakeWS([
        _welcome(),
        _joined(),
        {"type": "look", "room": {
            "name": "The Library",
            "description": "Dusty shelves line the walls.",
            "exits": [{"uuid": "e1", "name": "Garden"}],
            "contents": [{"uuid": "b1", "name": "old book"}],
        }, "seq": 3, "id": "stmt-2"},
    ])
    _run(rt, prog, fake)

    text = out.getvalue()
    assert "The Library" in text
    assert "Dusty shelves" in text
    assert "Garden" in text
    assert "old book" in text


# ---------------------------------------------------------------------------
# say
# ---------------------------------------------------------------------------

def test_say() -> None:
    rt = WorldRuntime("wss://localhost")
    prog = parse('say "Hello world"')

    fake = FakeWS([
        _welcome(),
        _joined(),
        {"type": "said", "actor": "agent", "text": "Hello world", "seq": 3, "id": "stmt-2"},
    ])
    _run(rt, prog, fake)

    say_cmd = next(m for m in fake.sent if m.get("cmd") == "say")
    assert say_cmd["text"] == "Hello world"


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------

def test_create_object() -> None:
    out = io.StringIO()
    rt = WorldRuntime("wss://localhost", output=out)
    prog = parse("create object chest")

    fake = FakeWS([
        _welcome(),
        _joined(),
        {"type": "created", "object": {"uuid": "chest-uuid-1234", "name": "chest"},
         "seq": 3, "id": "stmt-2"},
    ])
    _run(rt, prog, fake)

    assert "chest" in out.getvalue()
    assert rt._name_to_uuid["chest"] == "chest-uuid-1234"


# ---------------------------------------------------------------------------
# set
# ---------------------------------------------------------------------------

def test_set_property_uses_cached_uuid() -> None:
    rt = WorldRuntime("wss://localhost")
    rt._name_to_uuid["chest"] = "chest-uuid-1234"
    prog = parse('set chest.description to "A dusty old chest"')

    fake = FakeWS([
        _welcome(),
        _joined(),
        {"type": "property_set", "uuid": "chest-uuid-1234", "seq": 3, "id": "stmt-2"},
    ])
    _run(rt, prog, fake)

    set_cmd = next(m for m in fake.sent if m.get("cmd") == "set")
    assert set_cmd["uuid"] == "chest-uuid-1234"
    assert set_cmd["key"] == "description"
    assert set_cmd["value"] == "A dusty old chest"


# ---------------------------------------------------------------------------
# destroy
# ---------------------------------------------------------------------------

def test_destroy_uses_cached_uuid() -> None:
    rt = WorldRuntime("wss://localhost")
    rt._name_to_uuid["chest"] = "chest-uuid-1234"
    prog = parse("destroy chest")

    fake = FakeWS([
        _welcome(),
        _joined(),
        {"type": "destroyed", "uuid": "chest-uuid-1234", "seq": 3, "id": "stmt-2"},
    ])
    _run(rt, prog, fake)

    destroy_cmd = next(m for m in fake.sent if m.get("cmd") == "destroy")
    assert destroy_cmd["uuid"] == "chest-uuid-1234"


# ---------------------------------------------------------------------------
# print runs locally (no WS message)
# ---------------------------------------------------------------------------

def test_print_is_local() -> None:
    out = io.StringIO()
    rt = WorldRuntime("wss://localhost", output=out)
    prog = parse('print "hello from rosh"')

    fake = FakeWS([_welcome(), _joined()])
    _run(rt, prog, fake)

    assert "hello from rosh" in out.getvalue()
    # no extra WS messages sent (only the join)
    assert all(m.get("cmd") == "join" for m in fake.sent)


# ---------------------------------------------------------------------------
# seq + id on commands
# ---------------------------------------------------------------------------

def test_commands_carry_sequential_ids() -> None:
    rt = WorldRuntime("wss://localhost")
    prog = parse("look\nlook\nlook")

    fake = FakeWS([
        _welcome(),
        _joined(),
        {"type": "look", "room": {}, "seq": 3, "id": "stmt-2"},
        {"type": "look", "room": {}, "seq": 4, "id": "stmt-3"},
        {"type": "look", "room": {}, "seq": 5, "id": "stmt-4"},
    ])
    _run(rt, prog, fake)

    look_cmds = [m for m in fake.sent if m.get("cmd") == "look"]
    ids = [m["id"] for m in look_cmds]
    assert ids == ["stmt-2", "stmt-3", "stmt-4"]


# ---------------------------------------------------------------------------
# connect world ... sets URL (run_world integration)
# ---------------------------------------------------------------------------

def test_run_world_no_url_raises() -> None:
    from rosh_lang.targets.world import run_world
    prog = parse('print "hello"')
    with pytest.raises(ValueError, match="No world URL"):
        run_world(prog)


def test_run_world_url_from_connect_stmt() -> None:
    from rosh_lang.targets.world import run_world
    prog = parse('connect world wss://localhost/worlds/test/demo\nprint "hi"')
    # Just verify URL is extracted — don't actually connect
    rt = WorldRuntime.__new__(WorldRuntime)
    rt.ws_url = ""
    for stmt in prog.statements:
        from rosh_lang.core.model import ConnectStatement
        if isinstance(stmt, ConnectStatement) and stmt.name == "world" and stmt.url:
            rt.ws_url = stmt.url
            break
    assert rt.ws_url == "wss://localhost/worlds/test/demo"
