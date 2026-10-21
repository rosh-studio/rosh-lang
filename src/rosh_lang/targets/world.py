"""World target — connect a Rosh programme to a rosh-world WS server.

Dispatches go/look/say/create/set/destroy to a live rosh-world session.
All other statement types are silently skipped in Sprint C; they will
route through a local Runtime in Sprint G (runtime-server mode).
"""

from __future__ import annotations

import asyncio
import json
import os
import shlex
import sys
from typing import Any

from rosh_lang.core.model import (
    ConnectStatement,
    CreateStatement,
    DestroyStatement,
    ExtensionCommandStatement,
    GoStatement,
    LookStatement,
    PrintStatement,
    Programme,
    SayStatement,
    SetStatement,
    Statement,
)


def _parse_ext_args(args: str) -> dict[str, str]:
    """Parse extension command args into a dict for WS dispatch.

    Handles:
      "text"                    → {text: "text"}
      "text" key "value"        → {text: "text", key: "value"}
      "text with spaces" k v    → {text: "text with spaces", k: "v"}

    First token is always ``text``; subsequent pairs are ``key value``.
    Uses shlex for proper quote handling.
    """
    result: dict[str, str] = {}
    try:
        tokens = shlex.split(args)
    except ValueError:
        tokens = args.split() if args else []
    if not tokens:
        return result
    result["text"] = tokens[0]
    i = 1
    while i + 1 < len(tokens):
        result[tokens[i]] = tokens[i + 1]
        i += 2
    return result


def _strip_quotes(s: str) -> str:
    """Remove surrounding single or double quotes that the parser preserves."""
    s = s.strip()
    if len(s) >= 2 and s[0] in ('"', "'") and s[-1] == s[0]:
        return s[1:-1]
    return s


class WorldError(RuntimeError):
    """Server returned an error response."""


class WorldRuntime:
    """Execute Rosh statements against a rosh-world WS session."""

    def __init__(
        self,
        ws_url: str,
        api_key: str = "",
        actor: str = "rosh-agent",
        output: Any = None,
    ) -> None:
        self.ws_url = ws_url
        self.api_key = api_key
        self.actor = actor
        self.output = output or sys.stdout
        self._name_to_uuid: dict[str, str] = {}
        self._stmt_counter = 0
        self._ws: Any = None

    # ── Internal helpers ────────────────────────────────────────

    def _next_id(self) -> str:
        self._stmt_counter += 1
        return f"stmt-{self._stmt_counter}"

    async def _send(self, **kwargs: Any) -> dict[str, Any]:
        """Send a command and await its direct response (skipping push events)."""
        cmd_id = self._next_id()
        kwargs["id"] = cmd_id
        await self._ws.send(json.dumps(kwargs))
        while True:
            raw = await self._ws.recv()
            msg = json.loads(raw)
            if msg.get("type") in ("event", "heartbeat"):
                continue  # push broadcast — wait for our reply
            return msg

    async def _run_with_ws(self, programme: Programme) -> None:
        raw = await self._ws.recv()
        welcome = json.loads(raw)
        if welcome.get("type") != "welcome":
            raise WorldError(f"Expected welcome, got: {welcome}")

        joined = await self._send(cmd="join", name=self.actor, api_key=self.api_key, is_bot=True)
        if joined.get("type") == "error":
            raise WorldError(f"join failed: {joined.get('message')}")

        world_id = welcome.get("world", self.ws_url)
        level = joined.get("level", 0)
        self.output.write(f"[world] connected to {world_id} as {self.actor} (level {level})\n")

        for stmt in programme.statements:
            await self._exec_stmt(stmt)

    async def _run_async(self, programme: Programme, *, _ws_override: Any = None) -> None:
        if _ws_override is not None:
            self._ws = _ws_override
            await self._run_with_ws(programme)
            return

        try:
            from websockets.asyncio.client import connect
        except ImportError:
            raise ImportError(
                "The 'world' target requires 'websockets'.\n"
                "Install with: pip install websockets"
            )

        ws_url = self.ws_url
        if self.api_key:
            sep = "&" if "?" in ws_url else "?"
            ws_url = f"{ws_url}{sep}api_key={self.api_key}"
        async with connect(ws_url) as ws:
            self._ws = ws
            await self._run_with_ws(programme)

    # ── Statement dispatch ──────────────────────────────────────

    async def _exec_stmt(self, stmt: Statement) -> None:
        if isinstance(stmt, GoStatement):
            target = _strip_quotes(stmt.target)
            resp = await self._send(cmd="go", exit=target)
            if resp.get("type") == "error":
                raise WorldError(f"go '{target}': {resp.get('message')}")
            room = resp.get("room", {})
            dest = room.get("name") or resp.get("to", "?")
            self.output.write(f"[world] → {dest}\n")

        elif isinstance(stmt, LookStatement):
            resp = await self._send(cmd="look")
            if resp.get("type") == "error":
                raise WorldError(f"look: {resp.get('message')}")
            room = resp.get("room", {})
            self.output.write(f"\n[{room.get('name', '?')}]\n")
            if room.get("description"):
                self.output.write(f"{room['description']}\n")
            exits = room.get("exits") or []
            if exits:
                names = [e.get("name", e.get("uuid", "?")) for e in exits]
                self.output.write(f"Exits: {', '.join(names)}\n")
            contents = room.get("contents") or []
            if contents:
                names_c = [c.get("name", c.get("uuid", "?")) for c in contents]
                self.output.write(f"Contents: {', '.join(names_c)}\n")

        elif isinstance(stmt, SayStatement):
            text = _strip_quotes(stmt.text)
            resp = await self._send(cmd="say", text=text)
            if resp.get("type") == "error":
                raise WorldError(f"say: {resp.get('message')}")

        elif isinstance(stmt, CreateStatement):
            obj_type = "room" if stmt.kind in ("scene", "room") else "object"
            name = _strip_quotes(stmt.name)
            resp = await self._send(cmd="create", name=name, type=obj_type)
            if resp.get("type") == "error":
                raise WorldError(f"create '{name}': {resp.get('message')}")
            uuid = resp.get("object", {}).get("uuid", "")
            if uuid:
                self._name_to_uuid[stmt.name] = uuid
                self._name_to_uuid[name] = uuid
            self.output.write(f"[world] created {obj_type} '{name}'\n")

        elif isinstance(stmt, SetStatement):
            if "." in stmt.target:
                obj_name, key = stmt.target.split(".", 1)
                value = _strip_quotes(str(stmt.value))
                cmd: dict[str, Any] = {"cmd": "set", "key": key, "value": value, "target": obj_name}
                uuid = self._name_to_uuid.get(obj_name)
                if uuid:
                    cmd["uuid"] = uuid
                resp = await self._send(**cmd)
                if resp.get("type") == "error":
                    raise WorldError(f"set {stmt.target}: {resp.get('message')}")

        elif isinstance(stmt, DestroyStatement):
            target = self._name_to_uuid.get(stmt.name, stmt.name)
            resp = await self._send(cmd="destroy", uuid=target)
            if resp.get("type") == "error":
                raise WorldError(f"destroy '{stmt.name}': {resp.get('message')}")

        elif isinstance(stmt, PrintStatement):
            self.output.write(stmt.text + "\n")

        elif isinstance(stmt, ExtensionCommandStatement):
            cmd_args = _parse_ext_args(stmt.args)
            resp = await self._send(cmd=stmt.verb, **cmd_args)
            if resp.get("type") == "error":
                raise WorldError(f"{stmt.verb}: {resp.get('message')}")

        elif isinstance(stmt, ConnectStatement):
            pass  # URL already resolved at start; mid-script reconnect deferred

        else:
            verb = type(stmt).__name__.replace("Statement", "").lower()
            self.output.write(f"[world] warning: '{verb}' not supported by world target\n")


def run_world(
    programme: Programme,
    url: str = "",
    api_key: str = "",
    actor: str = "rosh-agent",
    output: Any = None,
) -> WorldRuntime:
    """Execute a Rosh programme against a rosh-world server.

    URL resolution order: url parameter → connect world ... statement → ROSH_WORLD_URL env.
    API key resolution order: api_key parameter → ROSH_WORLD_KEY env.
    """
    if not url:
        for stmt in programme.statements:
            if isinstance(stmt, ConnectStatement) and stmt.name == "world" and stmt.url:
                url = stmt.url
                break
    if not url:
        url = os.environ.get("ROSH_WORLD_URL", "")
    if not url:
        raise ValueError(
            "No world URL. Use 'connect world wss://...' in your script, "
            "pass url=, or set ROSH_WORLD_URL."
        )

    if not api_key:
        api_key = os.environ.get("ROSH_WORLD_KEY", "")

    rt = WorldRuntime(ws_url=url, api_key=api_key, actor=actor, output=output)
    asyncio.run(rt._run_async(programme))
    return rt
