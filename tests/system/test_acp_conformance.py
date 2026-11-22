# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey acp` driven end to end by the official ACP SDK client (SP-ACP, Task 10).

Each test starts the real `vibey acp` command line as a child process, as an editor does, and
speaks to it only through `agent-client-protocol`'s `ClientSideConnection`. The hub behind it is
`StubHub`, on loopback, found through the `serving.json` and `agent.token` it writes with the
real `LocalTokenStore`. The child is sealed off from the machine (`IsolatedAcpAgent`): a
temporary home, XDG folders and `PATH`, every `VIBEY_*` endpoint closed, and a user-level grant
that turns the bootstrap off, so nothing here can load a unit, write a client config, install
anything or reach the network.

What is held, against the code as it is (the plan's brief predates Tasks 3 to 9):

- `initialize` and `session/new`: protocol version 1, the capabilities vibey declares, an
  absolute `cwd`, the two modes, the `/` commands, and the folder's project followed live (a
  phase plan, then each ledger event as an escaped message; a spend gate's event is a notice,
  never a permission request).
- A turn: the hub call streams as `tool_call` then `tool_call_update`s, the reply as a message.
  Of four gates the hub lists, only the answerable choice gate becomes a permission request;
  the `budget_exhausted` and `deploy_interview` spend gates and the deployment opt-in are each
  refused with the host message. The option the client picks (`Answer: yes`) answers the gate
  with exactly `{"choice": "yes"}`; "Leave it open" (`<gate>:open`) answers nothing; a gate
  whose label could display reversed is refused as ambiguous.
- Modes and cancels: observe holds gates back; a switch to observe withdraws a request being
  asked; a cancel resolves a request still pending, and answers `cancelled` (never a JSON-RPC
  error); an answer picked after either answers nothing (the agent drops it, on stderr); a
  cancel during the hub call answers `cancelled` and names the request id.
- Sessions through the hub: list, close, load (the log replayed as display only, a forged
  stored event escaped, nothing re-run on the hub), resume (the mode restored, nothing shown).
- Stdout carries only ACP: every line the agent wrote is one whole JSON-RPC message the SDK
  decoded, and each update vibey builds is exactly the SDK schema's wire form, while the agent
  logs to stderr. At EOF it exits 0 within a bound, leaving no process; `</dev/null` exits at
  once.

Module-level test functions and fixtures rather than a class with an interface beside it
(ADR-0016): pytest collects them so, and the rule is about production code. The helpers below
are module-level for the same reason: each is one step these tests share.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Mapping, Sequence
from pathlib import Path
from typing import Any, Final
from uuid import uuid4

import pytest
from acp import PROTOCOL_VERSION, RequestError
from acp.client.connection import ClientSideConnection
from acp.schema import ClientCapabilities, Implementation, TextContentBlock

from tests.system.acp_conformance_client import AcpConformanceClient
from tests.system.acp_isolated_agent import IsolatedAcpAgent
from tests.system.acp_stub_hub import StubHub
from tests.system.interfaces.acp_conformance_client_interface import (
    AcpConformanceClientInterface,
)
from tests.system.interfaces.acp_isolated_agent_interface import IsolatedAcpAgentInterface
from tests.system.interfaces.acp_stub_hub_interface import StubHubInterface

WAIT: Final = 30.0
"""The bound on every wait: met in well under a second on a healthy machine; only a broken
agent (or a badly loaded runner) gets near it."""
PROJECT: Final = "0f4a6c2e-7d1b-4e3a-9c5d-2b8e1f0a6d71"
G_CHOICE: Final = "1b2c3d4e-5f60-4718-8a9b-0c1d2e3f4a5b"
G_SPEND: Final = "2c3d4e5f-6071-4829-9bac-1d2e3f4a5b6c"
G_DEPLOY_SPEND: Final = "3d4e5f60-7182-493a-acbd-2e3f4a5b6c7d"
G_OPT_IN: Final = "4e5f6071-8293-4a4b-bdce-3f4a5b6c7d8e"
G_LEAVE: Final = "5f607182-93a4-4b5c-8edf-4a5b6c7d8e9f"
G_BIDI: Final = "60718293-a4b5-4c6d-9fe0-5b6c7d8e9fa0"
G_HELD: Final = "718293a4-b5c6-4d7e-a0f1-6c7d8e9fa0b1"
G_LIVE_SPEND: Final = "8293a4b5-c6d7-4e8f-b102-7d8e9fa0b1c2"
HOSTILE: Final = "**pwn** [click](https://evil.example/x) \x1b[31mRED\x1b[0m \u202eevil\u202c <b>"
"""Model-written text as a hostile worker could write it: Markdown, a link, terminal escapes and
a right-to-left override."""
UNSAFE: Final = frozenset("\x1b\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069")
"""Characters an editor must never be handed to render: terminal escapes and bidi controls."""
NOT_FOUND: Final = -32002
INVALID_PARAMS: Final = -32602


@pytest.fixture
async def sealed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[tuple[StubHub, IsolatedAcpAgent]]:
    agent = IsolatedAcpAgent(tmp_path, monkeypatch)
    agent.prepare()
    stub = StubHub(agent.state_dir)
    stub.start()
    try:
        yield stub, agent
    finally:
        # A failed test may leave the agent running: its whole group goes, then the stub.
        await agent.kill()
        stub.stop()


async def _opened(conn: ClientSideConnection, folder: Path) -> str:
    """Initialize, then open one session in `folder`; returns its id."""
    await conn.initialize(
        protocol_version=PROTOCOL_VERSION,
        client_capabilities=ClientCapabilities(),
        client_info=Implementation(name="vibey-conformance", version="1.0.0"),
    )
    return (await conn.new_session(cwd=str(folder), mcp_servers=[])).session_id


def _prompt(text: str) -> list[TextContentBlock]:
    return [TextContentBlock(type="text", text=text)]


def _gate(gate_id: str, kind: str, prompt: str, options: Sequence[str]) -> dict[str, Any]:
    """A gate row as the hub's `_gate_dict` renders one."""
    return {
        "gate_id": gate_id,
        "project_id": PROJECT,
        "kind": kind,
        "prompt": prompt,
        "options": list(options),
        "default_answer": None,
    }


def _option(name: str) -> Any:
    """A permission policy: select the option the client shows as `name`."""
    return lambda request: next(o["optionId"] for o in request["options"] if o["name"] == name)


def _tool_calls(
    client: AcpConformanceClient, session_id: str
) -> dict[str, list[Mapping[str, Any]]]:
    """Each tool call's frames, in order, by `toolCallId`."""
    frames: dict[str, list[Mapping[str, Any]]] = {}
    for update in client.updates(session_id):
        if update["sessionUpdate"] in ("tool_call", "tool_call_update"):
            frames.setdefault(update["toolCallId"], []).append(update)
    return frames


def _content(frame: Mapping[str, Any]) -> str:
    return "".join(item["content"]["text"] for item in frame.get("content", []))


async def _assert_clean_finish(
    agent: IsolatedAcpAgent, stub: StubHub, client: AcpConformanceClient
) -> None:
    """EOF ends the agent with 0, within a bound and leaving no process; stdout was only ACP;
    nothing the editor shows carries an escape or a bidi control; the agent only ever spoke
    to the stub as the agent principal, called no other client method, and touched nothing."""
    assert await agent.stop() == 0, agent.stderr_text
    agent.assert_stdout_was_acp()
    agent.assert_left_no_process()
    agent.assert_machine_untouched()
    assert stub.unauthorised == 0
    assert client.unexpected == ()
    for text in client.displayed():
        assert not UNSAFE & set(text), text


async def test_initialize_new_session_and_the_folders_project_live(
    sealed: tuple[StubHub, IsolatedAcpAgent],
) -> None:
    stub, agent = sealed
    stub.set_projects(
        [
            {
                "project_id": PROJECT,
                "name": "demo",
                "repo_path": str(agent.workdir),
                "phase": "build",
                "open_gates": 0,
            }
        ]
    )
    stub.append_ledger(PROJECT, {"seq": 1, "kind": "phase", "phase": "design", "payload": {}})
    stub.append_ledger(PROJECT, {"seq": 2, "kind": "phase", "phase": "build", "payload": {}})
    client = AcpConformanceClient()
    conn = await agent.start(client)

    init = await conn.initialize(
        protocol_version=PROTOCOL_VERSION,
        client_capabilities=ClientCapabilities(),
        client_info=Implementation(name="vibey-conformance", version="1.0.0"),
    )
    assert init.protocol_version == 1
    capabilities = init.agent_capabilities
    assert capabilities is not None and capabilities.load_session is True
    prompts = capabilities.prompt_capabilities
    assert prompts is not None
    assert (prompts.embedded_context, prompts.image, prompts.audio) == (True, False, False)
    sessions = capabilities.session_capabilities
    assert sessions is not None
    assert None not in (sessions.list, sessions.close, sessions.resume)
    assert init.auth_methods == []
    assert init.agent_info is not None and init.agent_info.name == "vibey"

    with pytest.raises(RequestError) as relative:
        await conn.new_session(cwd="relative/folder", mcp_servers=[])
    assert relative.value.code == INVALID_PARAMS

    new = await conn.new_session(cwd=str(agent.workdir), mcp_servers=[])
    sid = new.session_id
    assert new.modes is not None and new.modes.current_mode_id == "drive"
    assert [mode.id for mode in new.modes.available_modes] == ["observe", "drive"]

    # The commands, then the project whose repository holds the folder: its plan as it stands.
    assert await client.wait_for(lambda: "plan" in client.kinds(sid), WAIT)
    commands = next(
        u["availableCommands"]
        for u in client.updates(sid)
        if u["sessionUpdate"] == "available_commands_update"
    )
    assert {"projects", "status", "gates", "answer", "new", "help"} <= {c["name"] for c in commands}
    plan = next(u["entries"] for u in client.updates(sid) if u["sessionUpdate"] == "plan")
    statuses = {entry["content"]: entry["status"] for entry in plan}
    assert (statuses["Design"], statuses["Build"], statuses["Review"]) == (
        "completed",
        "in_progress",
        "pending",
    )
    assert await client.wait_for(
        lambda: any(f"Following project demo ({PROJECT})" in t for t in client.texts(sid)), WAIT
    )

    # A new ledger event arrives as one escaped message; one that says its gate spends is also
    # a notice to answer it on the host, and never a permission request.
    stub.append_ledger(
        PROJECT,
        {
            "seq": 3,
            "kind": "gate_opened",
            "phase": "build",
            "payload": {
                "summary": HOSTILE,
                "gate_id": G_LIVE_SPEND,
                "gate_kind": "budget_exhausted",
            },
        },
    )
    assert await client.wait_for(
        lambda: any("may spend money" in t for t in client.texts(sid)), WAIT
    )
    texts = client.texts(sid)
    summary = next(t for t in texts if "gate\\_opened" in t)
    assert "\\[build\\] gate\\_opened: \\*\\*pwn\\*\\* \\[click\\]" in summary
    assert "https\\[:\\]//evil.example" in summary and "https://" not in summary
    notice = next(t for t in texts if "may spend money" in t)
    assert f"({G_LIVE_SPEND}, budget_exhausted)" in notice
    assert f"`vibey answer {G_LIVE_SPEND}`" in notice
    assert client.permission_requests == ()
    assert stub.answers == ()
    await _assert_clean_finish(agent, stub, client)


async def test_a_turn_streams_and_offers_only_the_answerable_gate(
    sealed: tuple[StubHub, IsolatedAcpAgent],
) -> None:
    stub, agent = sealed
    stub.set_gates(
        [
            _gate(G_CHOICE, "choice", HOSTILE, ["yes", "no"]),
            _gate(G_SPEND, "budget_exhausted", "raise the cap?", []),
            _gate(G_DEPLOY_SPEND, "deploy_interview", "which cloud?", ["approve", "decline"]),
            _gate(G_OPT_IN, "choice", "deploy it?", ["local_only", "deploy"]),
        ]
    )
    client = AcpConformanceClient()
    client.choose(_option("Answer: yes"))
    conn = await agent.start(client)
    sid = await _opened(conn, agent.workdir)

    reply = await conn.prompt(session_id=sid, prompt=_prompt("/gates"))

    assert reply.stop_reason == "end_turn"
    assert {
        "tool_call",
        "tool_call_update",
        "agent_message_chunk",
        "available_commands_update",
    } <= client.kinds(sid)
    calls = _tool_calls(client, sid)
    hub_call = next(frames for call_id, frames in calls.items() if call_id.endswith("-1"))
    assert [(f["sessionUpdate"], f.get("status")) for f in hub_call] == [
        ("tool_call", "pending"),
        ("tool_call_update", "in_progress"),
        ("tool_call_update", "completed"),
    ]
    assert (hub_call[0]["title"], hub_call[0]["kind"]) == ("Open gates", "read")

    # Exactly one permission request: the choice gate, with vibey's options and "Leave it open".
    assert len(client.permission_requests) == 1
    asked = client.permission_requests[0]
    gate_call = f"{asked['tool_call']['toolCallId']}"
    assert gate_call.endswith(f"-gate-{G_CHOICE}")
    assert asked["options"] == [
        {"optionId": f"{G_CHOICE}:0", "name": "Answer: yes", "kind": "allow_once"},
        {"optionId": f"{G_CHOICE}:1", "name": "Answer: no", "kind": "reject_once"},
        {"optionId": f"{G_CHOICE}:open", "name": "Leave it open", "kind": "reject_once"},
    ]
    assert stub.answers == ((G_CHOICE, {"choice": "yes"}, f"acp-{sid}-{G_CHOICE}"),)
    gate_frames = calls[gate_call]
    title = gate_frames[0]["title"]
    assert title.startswith("Answer gate: \\*\\*pwn\\*\\* \\[click\\]")
    assert "https\\[:\\]//evil.example" in title and "https://" not in title
    assert gate_frames[-1]["status"] == "completed"

    # The two spend gates and the deployment opt-in: refused, each with where to answer it.
    texts = client.texts(sid)
    host = "Answer it on the host (`vibey answer {}`) or in the desktop or mobile app."
    for gate_id, kind in ((G_SPEND, "budget\\_exhausted"), (G_DEPLOY_SPEND, "deploy\\_interview")):
        refusal = f"Gate {gate_id} ({kind}) spends money, so I cannot answer it. "
        assert sum(refusal + host.format(gate_id) in t for t in texts) == 1, texts
    assert any(f"Gate {G_OPT_IN} (choice) opts the project into deployment" in t for t in texts)
    # The reply quotes the model-written prompt as plain, escaped text.
    assert any("1\\. \\[choice\\] \\*\\*pwn\\*\\*" in t for t in texts), texts

    # Turn two: "Leave it open" answers nothing, and a label that could display reversed is not
    # offered at all. The gates already offered are not offered or refused again.
    stub.set_gates(
        [
            _gate(G_SPEND, "budget_exhausted", "raise the cap?", []),
            _gate(G_DEPLOY_SPEND, "deploy_interview", "which cloud?", ["approve", "decline"]),
            _gate(G_OPT_IN, "choice", "deploy it?", ["local_only", "deploy"]),
            _gate(G_LEAVE, "choice", "pick one", ["yes", "no"]),
            _gate(G_BIDI, "choice", "which one?", ["yes", "\u202eon"]),
        ]
    )
    client.choose(_option("Leave it open"))

    second = await conn.prompt(session_id=sid, prompt=_prompt("/gates"))

    assert second.stop_reason == "end_turn"
    assert len(client.permission_requests) == 2
    left = client.permission_requests[1]
    assert left["tool_call"]["toolCallId"].endswith(f"-gate-{G_LEAVE}")
    assert len(stub.answers) == 1
    closed = _tool_calls(client, sid)[left["tool_call"]["toolCallId"]][-1]
    assert closed["status"] == "failed" and "left open; nothing was answered" in _content(closed)
    texts = client.texts(sid)
    assert any(
        f"Gate {G_BIDI} (choice) has options I cannot show unambiguously" in t for t in texts
    )
    for gate_id in (G_SPEND, G_DEPLOY_SPEND):
        assert sum(f"Gate {gate_id} (" in t for t in texts) == 1
    await _assert_clean_finish(agent, stub, client)


async def test_observe_holds_gates_back_and_a_cancel_resolves_what_is_pending(
    sealed: tuple[StubHub, IsolatedAcpAgent],
) -> None:
    stub, agent = sealed
    stub.set_gates([_gate(G_HELD, "choice", "ship it?", ["yes", "no"])])
    client = AcpConformanceClient()
    conn = await agent.start(client)
    sid = await _opened(conn, agent.workdir)

    # Observe: the turn runs, the gate is not offered.
    await conn.set_session_mode(session_id=sid, mode_id="observe")
    assert await client.wait_for(
        lambda: (
            {"sessionUpdate": "current_mode_update", "currentModeId": "observe"}
            in client.updates(sid)
        ),
        WAIT,
    )
    held_back = await conn.prompt(session_id=sid, prompt=_prompt("/gates"))
    assert held_back.stop_reason == "end_turn"
    assert client.permission_requests == ()

    # Drive offers it; a switch to observe while it is asked withdraws the request, the turn ends
    # though the client never answered, and the pick the client sends later answers nothing.
    await conn.set_session_mode(session_id=sid, mode_id="drive")
    client.hold()
    turn = asyncio.create_task(conn.prompt(session_id=sid, prompt=_prompt("/gates")))
    assert await client.wait_for(lambda: len(client.permission_requests) == 1, WAIT)
    await conn.set_session_mode(session_id=sid, mode_id="observe")
    withdrawn = await asyncio.wait_for(turn, WAIT)
    assert withdrawn.stop_reason == "end_turn"
    assert any(f"Nothing was answered for gate {G_HELD}" in t for t in client.texts(sid))
    client.release(f"{G_HELD}:0")
    assert await agent.wait_stderr("dropped response with unknown id", WAIT)
    assert stub.answers == ()

    # Drive again: the gate is asked again; a cancel resolves the pending request and the turn
    # answers `cancelled`, not an error. The late pick answers nothing here either.
    await conn.set_session_mode(session_id=sid, mode_id="drive")
    client.hold()
    turn = asyncio.create_task(conn.prompt(session_id=sid, prompt=_prompt("/gates")))
    assert await client.wait_for(lambda: len(client.permission_requests) == 2, WAIT)
    await conn.cancel(session_id=sid)
    cancelled = await asyncio.wait_for(turn, WAIT)
    assert cancelled.stop_reason == "cancelled"
    client.release(f"{G_HELD}:0")
    assert await agent.wait_stderr("dropped response with unknown id", WAIT, count=2)
    assert stub.answers == ()
    asked = client.permission_requests[1]["tool_call"]["toolCallId"]
    closed = _tool_calls(client, sid)[asked][-1]
    assert closed["status"] == "failed" and "nothing was answered" in _content(closed)

    # A cancel while the hub call is in flight: `cancelled` at once, the call closed truthfully.
    stub.hold_chat()
    turn = asyncio.create_task(conn.prompt(session_id=sid, prompt=_prompt("/projects")))
    assert await asyncio.to_thread(stub.wait_chat_held, WAIT)
    await conn.cancel(session_id=sid)
    interrupted = await asyncio.wait_for(turn, WAIT)
    stub.release_chat()
    assert interrupted.stop_reason == "cancelled"
    hub_call = next(
        frames
        for frames in _tool_calls(client, sid).values()
        if frames[0].get("title") == "List projects"
    )
    assert hub_call[-1]["status"] == "failed"
    assert f"the hub may still apply it (request id acp-{sid}-" in _content(hub_call[-1])

    # The session is not wedged by any of it.
    after = await conn.prompt(session_id=sid, prompt=_prompt("/help"))
    assert after.stop_reason == "end_turn"
    assert len(client.permission_requests) == 2
    await _assert_clean_finish(agent, stub, client)


async def test_sessions_list_close_load_and_resume_through_the_hub(
    sealed: tuple[StubHub, IsolatedAcpAgent],
) -> None:
    stub, agent = sealed
    client = AcpConformanceClient()
    conn = await agent.start(client)
    folder = str(agent.workdir)
    sid = await _opened(conn, agent.workdir)
    assert (await conn.prompt(session_id=sid, prompt=_prompt("/gates"))).stop_reason == "end_turn"
    await conn.set_session_mode(session_id=sid, mode_id="observe")
    assert await asyncio.to_thread(stub.wait_for_session_event, sid, "mode", WAIT)

    listed = await conn.list_sessions(cwd=folder)
    assert [(s.session_id, s.cwd, s.title) for s in listed.sessions] == [(sid, folder, "/gates")]
    assert (await conn.list_sessions(cwd=str(agent.workdir / "elsewhere"))).sessions == []
    assert sid in [s.session_id for s in (await conn.list_sessions()).sessions]

    await conn.close_session(session_id=sid)
    assert await asyncio.to_thread(stub.wait_for_session_event, sid, "closed", WAIT)
    with pytest.raises(RequestError) as gone:
        await conn.prompt(session_id=sid, prompt=_prompt("/gates"))
    assert gone.value.code == NOT_FOUND

    # Whoever holds the agent's key could have written into the log: a forged message and an
    # event of a kind vibey never keeps. A load shows the first as escaped text, never the second.
    stub.forge_session_event(sid, "agent_message", {"text": HOSTILE})
    stub.forge_session_event(sid, "request_permission", {"toolCall": {"toolCallId": "x"}})
    chats = stub.requests.count(("POST", "/api/v1/chat/messages"))
    mark = len(client.updates(sid))

    loaded = await conn.load_session(cwd=folder, session_id=sid, mcp_servers=[])

    assert loaded.modes is not None and loaded.modes.current_mode_id == "observe"
    assert await client.wait_for(
        lambda: (
            "available_commands_update" in [u["sessionUpdate"] for u in client.updates(sid)[mark:]]
        ),
        WAIT,
    )
    after = list(client.updates(sid)[mark:])
    replayed = after[: [u["sessionUpdate"] for u in after].index("available_commands_update")]
    kinds = {update["sessionUpdate"] for update in replayed}
    assert kinds <= {
        "user_message_chunk",
        "agent_message_chunk",
        "tool_call",
        "tool_call_update",
        "plan",
        "current_mode_update",
    }, kinds
    assert {
        "sessionUpdate": "user_message_chunk",
        "content": {"type": "text", "text": "/gates"},
    } in (replayed)
    assert {"sessionUpdate": "current_mode_update", "currentModeId": "observe"} in replayed
    forged = [
        u["content"]["text"]
        for u in replayed
        if u["sessionUpdate"] == "agent_message_chunk" and "pwn" in u["content"]["text"]
    ]
    assert len(forged) == 1 and forged[0].startswith("\\*\\*pwn\\*\\* \\[click\\]")
    # Display only: nothing asked of the client, nothing run on the hub.
    assert client.permission_requests == ()
    assert stub.requests.count(("POST", "/api/v1/chat/messages")) == chats
    assert stub.answers == ()

    # Resume restores the mode and shows nothing.
    await conn.close_session(session_id=sid)
    mark = len(client.updates(sid))
    resumed = await conn.resume_session(session_id=sid, cwd=folder)
    assert resumed.modes is not None and resumed.modes.current_mode_id == "observe"
    assert await client.wait_for(
        lambda: any(
            u["sessionUpdate"] == "available_commands_update" for u in client.updates(sid)[mark:]
        ),
        WAIT,
    )
    assert client.updates(sid)[mark]["sessionUpdate"] == "available_commands_update"

    # Another folder's id, or an id no one kept, is not found -- in the same words.
    for session_id, cwd in ((sid, str(agent.workdir / "elsewhere")), (str(uuid4()), folder)):
        with pytest.raises(RequestError) as unknown:
            await conn.load_session(cwd=cwd, session_id=session_id, mcp_servers=[])
        assert unknown.value.code == NOT_FOUND
    await _assert_clean_finish(agent, stub, client)


async def test_stdout_stays_protocol_only_while_the_agent_logs_to_stderr(
    sealed: tuple[StubHub, IsolatedAcpAgent],
) -> None:
    stub, agent = sealed
    noisy = agent.workdir / "noisy"
    noisy.mkdir()
    stub.refuse_sessions_under(str(noisy))
    client = AcpConformanceClient()
    conn = await agent.start(client)
    quiet = await _opened(conn, agent.workdir)
    loud = (await conn.new_session(cwd=str(noisy), mcp_servers=[])).session_id

    # The hub refuses to keep one session's history: the agent logs it on stderr and tells the
    # client; the other session is kept as ever.
    assert (await conn.prompt(session_id=loud, prompt=_prompt("/help"))).stop_reason == "end_turn"
    assert (await conn.prompt(session_id=quiet, prompt=_prompt("/help"))).stop_reason == "end_turn"
    assert await agent.wait_stderr("the hub refused session", WAIT)
    assert await client.wait_for(
        lambda: any(t.startswith("Session history:") for t in client.texts(loud)), WAIT
    )
    assert any("/new \\<name\\> \\<what to build\\>" in t for t in client.texts(quiet))
    assert await asyncio.to_thread(stub.wait_for_session_event, quiet, "user_message", WAIT)
    assert stub.session_events(loud) == ()

    await _assert_clean_finish(agent, stub, client)
    assert b"the hub refused session" not in b"".join(agent.raw_lines)


def test_vibey_acp_with_stdin_from_dev_null_exits_at_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    agent = IsolatedAcpAgent(tmp_path, monkeypatch)
    agent.prepare()

    done = agent.run_with_stdin_from_dev_null(timeout=WAIT)

    assert done.returncode == 0, done.stderr.decode()
    assert done.stdout == b""
    # Nothing was asked of a hub, so nothing was made for one.
    assert not agent.state_dir.exists()


def test_the_conformance_doubles_satisfy_their_interfaces(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stub = StubHub(tmp_path / "state")
    stub.start()
    try:
        assert isinstance(stub, StubHubInterface)
        assert stub.port > 0
    finally:
        stub.stop()
    assert isinstance(IsolatedAcpAgent(tmp_path, monkeypatch), IsolatedAcpAgentInterface)
    assert isinstance(AcpConformanceClient(), AcpConformanceClientInterface)
