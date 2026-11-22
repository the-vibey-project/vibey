# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A loopback stand-in for the hub, for the ACP conformance test (SP-ACP, Task 10).

`vibey acp` reaches the hub through `HubGateway`, as the scoped agent principal: it reads the
user's `[hub] state_dir`, presents `<state_dir>/agent.token` and finds the hub in
`<state_dir>/serving.json`. This stub writes both files with the real `LocalTokenStore`, so the
agent finds it exactly as it finds a hub `vibey serve` runs, and it listens on 127.0.0.1 only.

Where the hub's own pure code says what an answer looks like, the stub uses it rather than a
copy: `HUB_CHAT` parses the chat message and renders the turn (`summarize_turn`, which also
flags spend gates as the hub does). The rest is the smallest faithful shape of each route the
agent reads (`app.py`): the projects list, the live ledger page, a gate's answer, and the four
`/api/v1/acp/sessions` routes with the hub's ownership and folder rules.

It never drops a connection and never holds a request past `HOLD_SECONDS`, which is below the
gateway's 15-second timeout: a transport error is the one thing that makes the agent run
`vibey hub start`, and the conformance test must never start anything.

Declared by `interfaces/acp_stub_hub_interface.py`.
"""

from __future__ import annotations

import json
import os
import re
import threading
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Final
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

from vibey.domain.acp.session_log import SessionEventKind
from vibey.domain.errors import LifecycleInvalid
from vibey.domain.hub_chat import HUB_CHAT
from vibey.infrastructure.hub.local_token import LocalTokenStore, ServingRecord

HOLD_SECONDS: Final = 10.0
"""The longest a held chat turn waits: below `HubGateway`'s 15 s, so the agent never sees a
timeout (an `httpx` error, which would make it try `vibey hub start`)."""
WAIT_STEP_SECONDS: Final = 0.05
"""How often a bounded wait re-checks its condition between notifications."""
_SESSION: Final = re.compile(r"^/api/v1/acp/sessions/([0-9a-f-]{36})(/events)?$")
_ANSWER: Final = re.compile(r"^/api/v1/gates/([0-9a-f-]{36})/answer$")
_LEDGER: Final = re.compile(r"^/api/v1/projects/([0-9a-f-]{36})/ledger/after$")
_KINDS: Final = frozenset(kind.value for kind in SessionEventKind)


class StubHub:
    """Declared by `interfaces/acp_stub_hub_interface.py::StubHubInterface`."""

    def __init__(self, state_dir: Path) -> None:
        self._store = LocalTokenStore(state_dir)
        self._token = ""
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._changed = threading.Condition()
        self._projects: list[dict[str, Any]] = []
        self._ledger: dict[str, list[dict[str, Any]]] = {}
        self._gates: list[dict[str, Any]] = []
        self._answers: list[tuple[str, Mapping[str, Any], str | None]] = []
        self._requests: list[tuple[str, str]] = []
        self._unauthorised = 0
        self._sessions: dict[str, dict[str, Any]] = {}
        self._refused: set[str] = set()
        self._holding = False
        self._held = threading.Event()
        self._release = threading.Event()

    # -- lifecycle -----------------------------------------------------------------------

    @property
    def port(self) -> int:
        if self._server is None:
            raise RuntimeError("the stub hub is not started")
        return int(self._server.server_address[1])

    def start(self) -> None:
        hub = self

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 - the name http.server dispatches to
                hub._serve(self, "GET")

            def do_POST(self) -> None:  # noqa: N802 - the name http.server dispatches to
                hub._serve(self, "POST")

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                return None  # the agent's stderr is under test; the stub's own stays quiet

        self._token = self._store.agent_token()
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self._server.daemon_threads = True
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            kwargs={"poll_interval": WAIT_STEP_SECONDS},
            name="acp-stub-hub",
            daemon=True,
        )
        self._thread.start()
        self._store.record_serving(ServingRecord(host="127.0.0.1", port=self.port, pid=os.getpid()))

    def stop(self) -> None:
        self.release_chat()
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=HOLD_SECONDS)

    # -- scripting -----------------------------------------------------------------------

    def set_projects(self, projects: Sequence[Mapping[str, Any]]) -> None:
        with self._changed:
            self._projects = [dict(project) for project in projects]

    def append_ledger(self, project_id: str, event: Mapping[str, Any]) -> None:
        with self._changed:
            events = self._ledger.setdefault(project_id, [])
            if event.get("seq") != len(events) + 1:
                raise ValueError(f"the next seq of {project_id} is {len(events) + 1}")
            events.append(dict(event))

    def set_gates(self, gates: Sequence[Mapping[str, Any]]) -> None:
        with self._changed:
            self._gates = [dict(gate) for gate in gates]

    def hold_chat(self) -> None:
        self._held.clear()
        self._release.clear()
        self._holding = True

    def release_chat(self) -> None:
        self._holding = False
        self._release.set()

    def wait_chat_held(self, timeout: float) -> bool:
        return self._held.wait(timeout)

    def refuse_sessions_under(self, cwd: str) -> None:
        with self._changed:
            self._refused.add(cwd)

    def forge_session_event(self, session_id: str, kind: str, payload: Mapping[str, Any]) -> int:
        with self._changed:
            kept = self._sessions[session_id]
            seq = max((event[0] for event in kept["events"]), default=0) + 1
            kept["events"].append((seq, kind, dict(payload)))
            kept["updated_at"] = datetime.now(UTC)
            self._changed.notify_all()
            return seq

    def session_events(self, session_id: str) -> tuple[tuple[int, str, Mapping[str, Any]], ...]:
        with self._changed:
            kept = self._sessions.get(session_id)
            return tuple(kept["events"]) if kept is not None else ()

    def wait_for_session_event(self, session_id: str, kind: str, timeout: float) -> bool:
        with self._changed:
            return self._changed.wait_for(
                lambda: any(event[1] == kind for event in self._events_of(session_id)), timeout
            )

    @property
    def answers(self) -> tuple[tuple[str, Mapping[str, Any], str | None], ...]:
        with self._changed:
            return tuple(self._answers)

    @property
    def requests(self) -> tuple[tuple[str, str], ...]:
        with self._changed:
            return tuple(self._requests)

    @property
    def unauthorised(self) -> int:
        with self._changed:
            return self._unauthorised

    # -- serving -------------------------------------------------------------------------

    def _serve(self, request: BaseHTTPRequestHandler, method: str) -> None:
        url = urlsplit(request.path)
        query = {key: values[-1] for key, values in parse_qs(url.query).items()}
        with self._changed:
            self._requests.append((method, url.path))
            authorised = request.headers.get("authorization") == f"Bearer {self._token}"
            if not authorised:
                self._unauthorised += 1
        if not authorised:
            self._reply(request, 401, {"detail": "not the agent token"})
            return
        body: Mapping[str, Any] = {}
        if method == "POST":
            length = int(request.headers.get("content-length") or 0)
            raw = request.rfile.read(length) if length else b"{}"
            parsed = json.loads(raw or b"{}")
            body = parsed if isinstance(parsed, Mapping) else {}
        status, document = self._route(method, url.path, query, body)
        self._reply(request, status, document)

    def _route(
        self, method: str, path: str, query: Mapping[str, str], body: Mapping[str, Any]
    ) -> tuple[int, Any]:
        if method == "GET" and path == "/health/live":
            return 200, {"status": "ok"}
        if method == "GET" and path == "/api/v1/projects":
            with self._changed:
                return 200, list(self._projects)
        if method == "GET" and path == "/api/v1/gates":
            return 200, {"gates": self._formatted_gates()}
        if method == "POST" and path == "/api/v1/chat/messages":
            return self._chat(body)
        if method == "POST" and (answer := _ANSWER.match(path)):
            return self._answer(answer.group(1), body)
        if method == "GET" and (ledger := _LEDGER.match(path)):
            return self._ledger_after(ledger.group(1), query)
        if path == "/api/v1/acp/sessions":
            return self._create(body) if method == "POST" else self._list(query)
        if session := _SESSION.match(path):
            session_id, events = session.group(1), session.group(2)
            if method == "POST" and events:
                return self._append(session_id, body)
            if method == "GET" and events:
                return self._events(session_id, query)
            if method == "GET":
                return self._summary(session_id, query)
        return 404, {"detail": f"the stub hub has no {method} {path}"}

    def _chat(self, body: Mapping[str, Any]) -> tuple[int, Any]:
        if self._holding:
            self._held.set()
            self._release.wait(HOLD_SECONDS)
        raw_project = body.get("project_id")
        project = UUID(str(raw_project)) if raw_project else None
        with self._changed:
            gates = [dict(gate) for gate in self._gates]
            projects = list(self._projects)
        try:
            intent = HUB_CHAT.parse(
                str(body.get("message", "")), project_id=project, open_gates=gates
            )
        except LifecycleInvalid as exc:
            return 422, {"detail": str(exc)}
        if intent.kind == "help":
            return 200, HUB_CHAT.summarize_turn(
                intent=intent, tool_calls=(), gates=gates, project_id=project
            )
        results: dict[str, Any] = {
            "projects": projects,
            "gates": {"gates": [HUB_CHAT.format_gate_prompt(gate) for gate in gates]},
            "status": {"project": {"name": "stub project", "phase": "build", "cycle": 1}},
        }
        call = {"name": intent.tool_name, "arguments": {}, "result": results.get(intent.kind, {})}
        active = intent.project_id or project
        return 200, HUB_CHAT.summarize_turn(
            intent=intent, tool_calls=(call,), gates=gates, project_id=active
        )

    def _answer(self, gate_id: str, body: Mapping[str, Any]) -> tuple[int, Any]:
        answer = body.get("answer")
        request_id = body.get("request_id")
        with self._changed:
            self._answers.append(
                (
                    gate_id,
                    dict(answer) if isinstance(answer, Mapping) else {},
                    request_id if isinstance(request_id, str) else None,
                )
            )
            gate = next((g for g in self._gates if g.get("gate_id") == gate_id), None)
            if gate is None:
                return 404, {"detail": f"no open gate {gate_id}"}
            if HUB_CHAT.format_gate_prompt(gate)["is_spend"]:
                return 403, {"detail": "the agent principal may not answer a spending gate"}
            self._gates.remove(gate)
        return 200, {"gate_id": gate_id, "status": "answered", "replayed": False}

    def _ledger_after(self, project_id: str, query: Mapping[str, str]) -> tuple[int, Any]:
        after, limit = int(query.get("seq", "0")), int(query.get("limit", "200"))
        with self._changed:
            events = [e for e in self._ledger.get(project_id, []) if e["seq"] > after][:limit]
        return 200, {
            "project_id": project_id,
            "events": events,
            "last_seq": events[-1]["seq"] if events else None,
        }

    def _formatted_gates(self) -> list[dict[str, Any]]:
        with self._changed:
            return [HUB_CHAT.format_gate_prompt(gate) for gate in self._gates]

    # -- the ACP session routes ----------------------------------------------------------

    def _create(self, body: Mapping[str, Any]) -> tuple[int, Any]:
        session_id, cwd = str(body.get("session_id")), str(body.get("cwd"))
        with self._changed:
            if cwd in self._refused:
                return 400, {"detail": "the stub hub refuses sessions kept under that folder"}
            kept = self._sessions.get(session_id)
            if kept is not None:
                return (201, {"session_id": session_id}) if kept["cwd"] == cwd else (409, {})
            self._sessions[session_id] = {
                "cwd": cwd,
                "events": [],
                "updated_at": datetime.now(UTC),
            }
            self._changed.notify_all()
        return 201, {"session_id": session_id}

    def _append(self, session_id: str, body: Mapping[str, Any]) -> tuple[int, Any]:
        seq, kind, payload = body.get("seq"), body.get("kind"), body.get("payload")
        if not isinstance(seq, int) or kind not in _KINDS or not isinstance(payload, Mapping):
            return 422, {"detail": "not an event"}
        with self._changed:
            kept = self._sessions.get(session_id)
            if kept is None:
                return 403, {"detail": "no such session of yours"}
            same = next((event for event in kept["events"] if event[0] == seq), None)
            if same is not None:
                return (200, {"stored": True}) if same[1:] == (kind, payload) else (409, {})
            kept["events"].append((seq, kind, dict(payload)))
            kept["events"].sort(key=lambda event: event[0])
            kept["updated_at"] = datetime.now(UTC)
            self._changed.notify_all()
        return 200, {"stored": True}

    def _kept(self, session_id: str, query: Mapping[str, str]) -> dict[str, Any] | None:
        kept = self._sessions.get(session_id)
        if kept is None or ("cwd" in query and query["cwd"] != kept["cwd"]):
            return None
        return kept

    def _events(self, session_id: str, query: Mapping[str, str]) -> tuple[int, Any]:
        after, limit = int(query.get("after", "0")), int(query.get("limit", "200"))
        with self._changed:
            kept = self._kept(session_id, query)
            if kept is None:
                return 403, {"detail": "no such session of yours under that folder"}
            events = [
                {"seq": seq, "kind": kind, "payload": payload}
                for seq, kind, payload in kept["events"]
                if seq > after
            ][:limit]
        return 200, {"events": events, "last_seq": events[-1]["seq"] if events else None}

    def _summary(self, session_id: str, query: Mapping[str, str]) -> tuple[int, Any]:
        with self._changed:
            kept = self._kept(session_id, query)
            if kept is None:
                return 403, {"detail": "no such session of yours under that folder"}
            newest: dict[str, Any] = {}
            for _, kind, payload in kept["events"]:
                newest[kind] = payload
            seqs = [event[0] for event in kept["events"]]
        return 200, {
            "session_id": session_id,
            "newest_seq": max(seqs, default=0),
            **{key: newest.get(key) for key in ("mode", "attach", "title")},
        }

    def _list(self, query: Mapping[str, str]) -> tuple[int, Any]:
        with self._changed:
            listed = [
                (session_id, kept)
                for session_id, kept in self._sessions.items()
                if "cwd" not in query or kept["cwd"] == query["cwd"]
            ]
            listed.sort(key=lambda item: (item[1]["updated_at"], item[0]), reverse=True)
            sessions = [
                {
                    "session_id": session_id,
                    "cwd": kept["cwd"],
                    "title": self._title(kept),
                    "updated_at": kept["updated_at"].isoformat(),
                    "closed": bool(kept["events"]) and kept["events"][-1][1] == "closed",
                }
                for session_id, kept in listed
            ]
        return 200, {"sessions": sessions, "next_cursor": None}

    @staticmethod
    def _title(kept: Mapping[str, Any]) -> str | None:
        titles = [payload.get("title") for _, kind, payload in kept["events"] if kind == "title"]
        return titles[-1] if titles and isinstance(titles[-1], str) else None

    def _events_of(self, session_id: str) -> list[tuple[int, str, Mapping[str, Any]]]:
        kept = self._sessions.get(session_id)
        return list(kept["events"]) if kept is not None else []

    @staticmethod
    def _reply(request: BaseHTTPRequestHandler, status: int, document: Any) -> None:
        data = json.dumps(document).encode()
        request.send_response(status)
        request.send_header("content-type", "application/json")
        request.send_header("content-length", str(len(data)))
        request.end_headers()
        request.wfile.write(data)
