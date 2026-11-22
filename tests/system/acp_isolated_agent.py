# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey acp` run as an editor runs it, sealed off from the machine (SP-ACP, Task 10).

The agent is the real command line (`vibey.cli.main.run(["acp"])`, the console script's own
entry point) in a child process, so everything between an editor and vibey is exercised: the
root callback, the stdout guard, the settings' trust merge, the composition root and the stdio
transport. Nothing is inherited from the test's environment. The child gets a temporary `HOME`,
XDG folders and an empty `PATH`, and every `VIBEY_*` endpoint the code reads points at a closed
loopback port (9, discard), so the person's own `vibey.toml`, marker files, units, editor
settings, database, models and the network are all out of its reach. An in-process guard
fixture cannot reach a child; this environment is the child's guard.

The grant is the user's file (ADR-0101): here it turns the whole bootstrap off (no doctor, no
connect, no units, no PostgreSQL, no SearXNG) and names the stub hub's state folder. The
project's file only narrows, as a cloned repository's may, and names a decoy state folder: the
agent must never make it, since `[hub]` is read from the user's file alone.

Stdout is read through a tee: each raw line is kept, then fed to the reader the official SDK's
`ClientSideConnection` reads, so the test can prove every line was one whole ACP message.
Declared by `interfaces/acp_isolated_agent_interface.py`.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import signal
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final

import pytest
from acp.client.connection import ClientSideConnection
from acp.connection import StreamDirection, StreamEvent
from acp.schema import (
    CloseSessionResponse,
    InitializeResponse,
    ListSessionsResponse,
    LoadSessionResponse,
    NewSessionResponse,
    PromptResponse,
    RequestPermissionRequest,
    ResumeSessionResponse,
    SessionNotification,
    SetSessionModeResponse,
)
from pydantic import BaseModel

from tests.domain.acp.acp_wire import assert_wire_exact
from vibey.bootstrap import acp_user_config
from vibey.infrastructure.hub.local_token import AGENT_TOKEN_FILE, RUNTIME_FILE

AGENT_CODE: Final = "from vibey.cli.main import run; run(['acp'])"
"""What the `vibey` console script runs, with `acp` as its arguments."""
LINE_LIMIT: Final = 16_777_216 + 1
"""`[acp] max_message_bytes`' default and its newline: no frame vibey sends is longer."""
EXIT_SECONDS: Final = 30.0
"""The most an agent may take to exit after its stdin closes (generous for a loaded runner;
a healthy one takes about a second)."""
CLOSED_PORT: Final = "127.0.0.1:9"
"""The discard port on loopback: nothing listens there, so a connection is refused at once."""
SAFE_ACP: Final[Mapping[str, Any]] = {
    "auto_bootstrap": False,
    "auto_connect": False,
    "auto_services": False,
    "install_postgres": "never",
    "searxng": "never",
}
"""The grant that lets the bootstrap touch nothing; the project's file repeats it (narrowing)."""
USER_ACP: Final[Mapping[str, Any]] = {
    **SAFE_ACP,
    "cancel_grace_seconds": 0.0,
    "live_poll_seconds": 0.2,
    "probe_seconds": 5,
    "permission_timeout_seconds": 60,
    "max_gate_prompts_per_turn": 5,
    "hub_start_seconds": 3600,
}
"""The user's `[acp]` for the test: no grace for a hub call a cancel interrupts (so a cancel's
outcome never depends on timing), a quick live feed, and room for every gate a turn lists."""
RESPONSES: Final[Mapping[str, type[BaseModel]]] = {
    "initialize": InitializeResponse,
    "session/new": NewSessionResponse,
    "session/prompt": PromptResponse,
    "session/load": LoadSessionResponse,
    "session/resume": ResumeSessionResponse,
    "session/list": ListSessionsResponse,
    "session/close": CloseSessionResponse,
    "session/set_mode": SetSessionModeResponse,
}
"""The schema each answer to a request the client sent is held to."""


class IsolatedAcpAgent:
    """Declared by `interfaces/acp_isolated_agent_interface.py::IsolatedAcpAgentInterface`."""

    def __init__(self, root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self._root = root
        self._monkeypatch = monkeypatch
        self._home = root / "home"
        self._xdg = root / "xdg"
        self._bin = root / "bin"
        self._tmp = root / "tmp"
        self._state = root / "hub-state"
        self._decoy = root / "decoy-state"
        self._work = root / "project"
        self._user_config = self._home / "unset"
        self._process: asyncio.subprocess.Process | None = None
        self._conn: ClientSideConnection | None = None
        self._sdk_reader: asyncio.StreamReader | None = None
        self._tasks: list[asyncio.Task[None]] = []
        self._raw: list[bytes] = []
        self._incoming: list[dict[str, Any]] = []
        self._sent: dict[Any, str] = {}
        self._stderr: list[str] = []
        self._stderr_changed = asyncio.Condition()

    @property
    def workdir(self) -> Path:
        return self._work

    @property
    def state_dir(self) -> Path:
        return self._state

    @property
    def stderr_text(self) -> str:
        return "".join(self._stderr)

    @property
    def raw_lines(self) -> tuple[bytes, ...]:
        return tuple(self._raw)

    # -- the sealed environment -----------------------------------------------------------

    def prepare(self, **acp: Any) -> None:
        for folder in (self._home, self._bin, self._tmp, self._work):
            folder.mkdir(parents=True)
        for name in ("config", "state", "data", "cache", "runtime"):
            (self._xdg / name).mkdir(parents=True, mode=0o700)
        # The real lookup, under the child's HOME and XDG_CONFIG_HOME: the same file the child
        # will read, wherever this platform keeps it.
        with self._monkeypatch.context() as patched:
            for name, value in self.environment().items():
                patched.setenv(name, value)
            self._user_config = acp_user_config()
        if not self._user_config.is_relative_to(self._root):
            raise AssertionError(f"the user's vibey.toml would be {self._user_config}")
        self._user_config.parent.mkdir(parents=True, mode=0o700)
        self._user_config.write_text(
            self._toml({"hub": {"state_dir": str(self._state)}, "acp": {**USER_ACP, **acp}})
        )
        (self._work / "vibey.toml").write_text(
            self._toml({"hub": {"state_dir": str(self._decoy)}, "acp": dict(SAFE_ACP)})
        )

    def environment(self) -> dict[str, str]:
        refused = f"http://{CLOSED_PORT}"
        return {
            "HOME": str(self._home),
            "XDG_CONFIG_HOME": str(self._xdg / "config"),
            "XDG_STATE_HOME": str(self._xdg / "state"),
            "XDG_DATA_HOME": str(self._xdg / "data"),
            "XDG_CACHE_HOME": str(self._xdg / "cache"),
            "XDG_RUNTIME_DIR": str(self._xdg / "runtime"),
            "PATH": str(self._bin),
            "TMPDIR": str(self._tmp),
            "PYTHONUTF8": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "NO_PROXY": "*",
            "no_proxy": "*",
            "VIBEY_PG_URL": f"postgresql://acp-conformance@{CLOSED_PORT}/none",
            "VIBEY_PG_MIGRATE_URL": f"postgresql://acp-conformance@{CLOSED_PORT}/none",
            "VIBEY_OLLAMA_URL": refused,
            "VIBEY_SEARXNG_URL": refused,
        }

    @staticmethod
    def _toml(tables: Mapping[str, Mapping[str, Any]]) -> str:
        lines: list[str] = []
        for table, keys in tables.items():
            lines.append(f"[{table}]")
            for key, value in keys.items():
                shown = json.dumps(value) if not isinstance(value, bool) else str(value).lower()
                lines.append(f"{key} = {shown}")
            lines.append("")
        return "\n".join(lines)

    # -- the process ----------------------------------------------------------------------

    async def start(self, client: Any) -> ClientSideConnection:
        self._process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            AGENT_CODE,
            cwd=self._work,
            env=self.environment(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
            limit=LINE_LIMIT,
        )
        self._sdk_reader = asyncio.StreamReader(limit=LINE_LIMIT)
        self._tasks = [
            asyncio.create_task(self._tee(), name="acp-stdout-tee"),
            asyncio.create_task(self._collect_stderr(), name="acp-stderr"),
        ]
        assert self._process.stdin is not None
        self._conn = ClientSideConnection(
            client, self._process.stdin, self._sdk_reader, observers=[self._observe]
        )
        return self._conn

    async def stop(self) -> int:
        process = self._running()
        assert process.stdin is not None
        process.stdin.close()
        with contextlib.suppress(BrokenPipeError, ConnectionResetError):
            await process.stdin.wait_closed()
        code = await asyncio.wait_for(process.wait(), EXIT_SECONDS)
        await asyncio.wait_for(asyncio.gather(*self._tasks), EXIT_SECONDS)
        if self._conn is not None:
            await self._conn.close()
        return code

    async def kill(self) -> None:
        process = self._process
        if process is not None and process.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            await process.wait()
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        if self._conn is not None:
            await self._conn.close()

    async def wait_stderr(self, text: str, timeout: float, *, count: int = 1) -> bool:
        def seen() -> bool:
            return self.stderr_text.count(text) >= count

        async with self._stderr_changed:
            try:
                await asyncio.wait_for(self._stderr_changed.wait_for(seen), timeout)
            except TimeoutError:
                return seen()
        return True

    def run_with_stdin_from_dev_null(self, timeout: float) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(  # noqa: S603 - this interpreter, a fixed argument list
            [sys.executable, "-c", AGENT_CODE],
            cwd=self._work,
            env=self.environment(),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=timeout,
            start_new_session=True,
            check=False,
        )

    async def _tee(self) -> None:
        process = self._running()
        reader = self._sdk_reader
        assert process.stdout is not None and reader is not None
        while line := await process.stdout.readline():
            self._raw.append(line)
            reader.feed_data(line)
        reader.feed_eof()

    async def _collect_stderr(self) -> None:
        process = self._running()
        assert process.stderr is not None
        while chunk := await process.stderr.read(65_536):
            async with self._stderr_changed:
                self._stderr.append(chunk.decode("utf-8", errors="replace"))
                self._stderr_changed.notify_all()

    def _observe(self, event: StreamEvent) -> None:
        message = event.message
        if event.direction is StreamDirection.INCOMING:
            self._incoming.append(message)
        elif "method" in message and "id" in message:
            self._sent[message["id"]] = message["method"]

    def _running(self) -> asyncio.subprocess.Process:
        if self._process is None:
            raise RuntimeError("the agent was not started")
        return self._process

    # -- what is checked after it ran -----------------------------------------------------

    def assert_stdout_was_acp(self) -> None:
        assert self._raw, "the agent wrote nothing to stdout"
        # The SDK decoded every line: one it could not parse is dropped before its observers.
        assert len(self._incoming) == len(self._raw), (len(self._incoming), len(self._raw))
        for raw in self._raw:
            assert raw.endswith(b"\n"), raw
            message = json.loads(raw.decode("utf-8"))
            assert isinstance(message, dict) and message.get("jsonrpc") == "2.0", raw
            method = message.get("method")
            if method == "session/update":
                assert "id" not in message, raw
                assert_wire_exact(SessionNotification, message["params"])
            elif method == "session/request_permission":
                assert "id" in message, raw
                assert_wire_exact(RequestPermissionRequest, message["params"])
            else:
                # Nothing else is ever sent unasked: this is an answer to a client request.
                assert method is None, raw
                asked = self._sent[message["id"]]
                if "error" in message:
                    error = message["error"]
                    assert isinstance(error["code"], int) and isinstance(error["message"], str)
                    assert "result" not in message, raw
                else:
                    RESPONSES[asked].model_validate(message["result"])

    def assert_left_no_process(self) -> None:
        process = self._running()
        assert process.returncode is not None, "the agent is still running"
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            return
        raise AssertionError(f"a process outlived the agent in its group {process.pid}")

    def assert_machine_untouched(self) -> None:
        kept = sorted(path.name for path in self._state.iterdir())
        assert kept == sorted([AGENT_TOKEN_FILE, RUNTIME_FILE]), kept
        assert not self._decoy.exists(), "the project's [hub] state_dir was used"
        written = sorted(
            path
            for folder in (self._home, self._xdg)
            for path in folder.rglob("*")
            if not path.is_dir()
        )
        assert written == [self._user_config], written
