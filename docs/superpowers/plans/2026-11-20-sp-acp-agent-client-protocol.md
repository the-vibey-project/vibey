# SP-ACP: Agent Client Protocol Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `vibey acp` speaks the Agent Client Protocol (ACP v1) over stdio so an editor or driver LLM can fully drive vibey, and on a machine where nobody ran `vibey doctor` or `vibey connect --yes` it runs both itself and keeps the hub and worker running as user-level services.

**Architecture:** vibey is the ACP **agent**; the editor is the client. A stdlib, asyncio, bidirectional JSON-RPC 2.0 peer is factored out of the MCP stdio server and shared by both. Pure ACP types, the session state machine, gate-to-permission mapping and update mapping live in `src/vibey/domain/acp/`. Method dispatch, the prompt turn, bootstrap, keep-alive and session persistence live in `src/vibey/application/acp/`. Every action reaches the hub through the existing `HubGateway` as the scoped agent principal, so the hub's scope model (never `spend`) stays the enforcement point. Composition happens in `src/vibey/bootstrap.py`.

**Tech Stack:** Python 3.12+ stdlib (`asyncio`, `json`, `fcntl`, `subprocess`), the existing `httpx` hub gateway, asyncpg plus one new migration for the hub-side session log, launchd and `systemd --user`. Dev only: `agent-client-protocol==1.0.0` (import name `acp`, pulls `pydantic>=2.7`, which vibey already depends on) as a schema validator and conformance client.

**Spec:** the master plan `docs/superpowers/plans/2026-11-10-vibey-optimization-program.md`, section SP-ACP (added by the concurrent "what is left" rewrite), carrying the operator-approved design of 2026-11-20. The approved design is restated in "Approved design" below so this plan stands alone. The protocol reference is <https://agentclientprotocol.com/protocol/overview> and its schema page.

## Approved design (operator rulings of 2026-11-20, binding)

- vibey is the ACP agent over stdio JSON-RPC 2.0, `protocolVersion: 1`. Zed or any ACP client launches it as `vibey acp`. No new console script.
- Hand-rolled on a shared stdlib JSON-RPC peer factored out of `infrastructure/mcp/stdio_server.py`. No runtime dependency. The official `agent-client-protocol` 1.0.0 Python SDK is a dev dependency used as a conformance client.
- Reached over ACP on a machine where `vibey doctor` and `vibey connect --yes` never ran, vibey runs both itself, then installs AND loads user-level launchd or systemd services for the hub and the worker and keeps them running. No sudo for that. A step that needs sudo (installing PostgreSQL) goes through ACP `session/request_permission`.
- Spend gates (`budget_exhausted`, `deploy_*`) are never answerable by the agent principal and are never offered as a permission. ADR-0046 and the scope model are unchanged.
- The supervisor's "the operator loads units" stance (ADR-0070, the #1189 module docstrings) is amended by a new ADR-0101 to "loads user-level units only, never system ones, only under an explicit grant", the grant being `[acp] auto_bootstrap = true` (default true). The governing rule also becomes a proposed sub-doctrine in a separate canon PR that the operator merges.
- Everything is configurable under a new `[acp]` table in `vibey.toml` (ADR-0018).

## Facts verified while grounding this plan (develop `903bfbde2`, ACP site, PyPI)

These correct or sharpen the approved design. Each is a decision this plan takes; none changes an operator ruling.

1. **Framing is confirmed.** The ACP transports page: messages are delimited by `\n` and MUST NOT contain embedded newlines; UTF-8; the agent MUST NOT write anything to stdout that is not a valid ACP message; it MAY log UTF-8 to stderr. `json.dumps` already escapes newlines inside strings, so one `json.dumps` per line is valid framing.
2. **The chat planner is `HubChat`** (`HUB_CHAT`, `domain/hub_chat.py`), not `HubChatPlanner`. The hub already runs a whole chat turn at `POST /api/v1/chat/messages` and returns `{reply, tool_calls, gates, project_id}`.
3. **The slash catalogue is `CHAT_SLASH_COMMANDS`** in `domain/hub_chat.py` (its TypeScript twin is `clients/app/src/core/chat.ts`). `packages/vibey-core/src/catalogue.ts` is the engine and loop catalogue. The commands are `/projects /status /gates /answer /budget /queue /ledger /loops /lanes /doctor /new /start /pause /abandon /help`. There is no `/resume`; `/start` resumes work. ACP advertises the Python list as it is; adding a command is out of scope.
4. **No WebSocket client is a runtime dependency** (`httpx` has none). The live stream therefore polls `GET /api/v1/projects/{id}/ledger/after?seq=N`, which the hub documents as "the live feed, for a client that polls" and which reads the same `HubService.ledger_after` the `/live` WebSocket reads. Same events, same order, no new dependency.
5. **Session persistence goes through the hub.** An editor launches `vibey acp` without `[supervisor] env_file`, so the process has no `VIBEY_PG_URL`, and ADR-0055 and ADR-0100 keep database credentials out of model-driven processes. The `acp_session` tables are written by the hub on routes the agent principal may call. The repository follows the codebase convention (`infrastructure/db/`), not `infrastructure/acp/`.
6. **`notice` updates need the client's `session.notices` capability.** Without it the same text goes out as `agent_message_chunk`.
7. **`session/request_permission` belongs inside a prompt turn**, and a `session/update` sent before the `session/new` response names a session the client does not know yet. So bootstrap steps 1 to 3 start right after `session/new` returns, and the privileged step 4 is asked at the start of the first `session/prompt`.
8. **`sudo` cannot get a password over ACP.** A permission option is a yes or no, not a password field, and `PostgresLocalService` runs `sudo` with stdin inherited, which in `vibey acp` is the protocol pipe. In ACP the command runner rewrites `sudo` to `sudo -n` with stdin closed. On macOS (Homebrew) no sudo is needed. When `sudo -n` needs a password, vibey says the exact command for the operator to run and continues in the degraded mode.
9. **The supervisor does not supervise the hub today.** `SupervisorPlanner` plans `worker`, `delivery`, `state-sync`. Units restart on failure only (`KeepAlive{SuccessfulExit=false}`, `Restart=on-failure`). A `hub` service and an `always` restart policy are new.
10. **One hub per user is already enforced** by `ServeLock` (`<state_dir>/serve.lock`, flock). A hub unit started while a detached hub (spawned by `HubGateway`'s `vibey hub start` fallback) holds the lock exits at once and is restarted every `restart_seconds`. Bootstrap must not cause that.
11. **Zed's `settings.json` is JSONC** (comments allowed). The entry shape is `"agent_servers": {"vibey": {"type": "custom", "command": ..., "args": ["acp"], "env": {}}}` at `~/.config/zed/settings.json` on macOS and Linux. A strict JSON parse of a commented file fails; vibey never rewrites it and prints the snippet instead.
12. **Sub-doctrine 12.p is taken** (proposed by ADR-0100, not yet in the canon). The ACP rule is proposed as **12.q**.
13. The SDK 1.0.0 client API, from its `examples/client.py`: `from acp import PROTOCOL_VERSION, Client, connect_to_agent`; `conn.initialize(protocol_version=..., client_capabilities=..., client_info=...)`, `conn.new_session(cwd=..., mcp_servers=[])`, `conn.prompt(session_id=..., prompt=[TextContentBlock(text=...)])`. Task 10 step 1 re-reads these names from the installed 1.0.0 wheel before the conformance test is written.

## Global Constraints

- ADR-0016: code lives in classes, a class per file, each with its interface beside it (`<dir>/interfaces/<module>_interface.py`), interfaces declare and never consume. A module-level function carries its reason at the definition. Value types (frozen dataclasses, enums, constants) are exempt from the interface rule (master plan Decision 3).
- ADR-0023: `domain/`, `application/`, `infrastructure/`, `cli/` each keep a 100% branch floor. Every task ends with its layer at 100%.
- Domain purity: nothing in `src/vibey/domain/acp/` does I/O, async, clock or network (`tests/domain/test_domain_purity.py` walks `domain/` recursively).
- `.importlinter`: add `vibey.application.acp.interfaces` to `interfaces-declare-only`, and `vibey.infrastructure.jsonrpc.interfaces` and `vibey.infrastructure.acp.interfaces` to `infrastructure-interfaces-declare-only`. `uv run lint-imports` stays green.
- ADR-0017 dogfood: reuse `HubGateway`, `HostTools`, `HubChat`, `HubScopePolicy`, `SupervisorPlanner`, `TimerUnitRenderer`, `SupervisorHost`, `HostInstaller`, `PostgresLocalService`, `ServeLock`'s flock pattern and `public.ledger_refuse_rewrite()`. The codexloop `appserver/client.py` is NOT reused: it is a one-shot, client-only, anyio exchange in the codexloop tenant, omits the `jsonrpc` member by Codex's dialect, and cannot receive requests. That is a capability gap, so the shared peer is added to vibey, and converging codexloop onto it is a follow-up issue, not this plan.
- ADR-0018: every value below that a reasonable adopter could want different is an `[acp]` key, read by name, unknown keys and wrong types refused by name.
- The ledger is append-only. The new `acp_session_event` table is append-only by trigger. A mode change, an attach and a close are new rows.
- Every job is idempotent under replay. Every hub write from ACP carries a request id derived from `(session_id, seq)`.
- Never block a worker on a human. A gate is already a parked job; the ACP agent process is not a worker; a permission prompt that is never answered times out and leaves the gate open (silence is not consent, sub-doctrine 12.d).
- stdout of `vibey acp` carries only ACP messages. Logging goes to stderr.
- No TypeScript or JavaScript is touched. If a task finds it must, ADR-0088 applies.
- Conventional Commits. Commit and push in the foreground. Never edit a worktree while a hook runs.
- Agent-surface trees change together: `.claude/skills/`, `.agents/skills/`, `.cursor/rules/`, `.agent/rules/`, plus the plugin copy and its microslices.
- Hot files: `cli/main.py` changes only in the `doctor` body (Task 7) and one `app.command("acp")` line (Task 3). `infrastructure/hub/app.py` gains only the session routes (Task 6).
- No literal volatile path (the system temporary directory and its relatives) in any tracked text (`tests/meta/test_no_volatile_work_paths.py`).

## The `[acp]` table (Task 2 defines it; later tasks consume it)

| Key | Type | Default | Used by |
|---|---|---|---|
| `auto_bootstrap` | bool | `true` | Task 7, 8: the grant; `false` skips doctor, connect, services, PostgreSQL and keep-alive |
| `auto_connect` | bool | `true` | Task 7 |
| `auto_services` | bool | `true` | Task 8 |
| `install_postgres` | `"ask"` or `"never"` | `"ask"` | Task 7 |
| `services` | list, subset of `["hub", "worker"]` | `["hub", "worker"]` | Task 8 |
| `restart` | `"always"` or `"on-failure"` | `"always"` | Task 8 |
| `service_workdir` | string | `""` (the directory of `[supervisor] env_file`) | Task 8 |
| `probe_seconds` | int, at least 5 | `30` | Task 8 |
| `modes` | list, subset of `["observe", "drive"]`, non-empty | `["observe", "drive"]` | Task 5 |
| `default_mode` | string, one of `modes` | `"drive"` | Task 3, 5 |
| `bootstrap_timeout_seconds` | int, at least 1 | `120` | Task 7 |
| `permission_timeout_seconds` | int, at least 1 | `600` | Task 4, 7 |
| `max_gate_prompts_per_turn` | int, at least 0 | `3` | Task 4 |
| `reject_words` | list of strings | `["reject", "decline", "deny", "no", "cancel"]` | Task 4 |
| `live_poll_seconds` | float, at least 0.2 | `1.0` | Task 5 |
| `live_message_chars` | int, at least 40 | `400` | Task 5 |
| `live_between_turns` | bool | `true` | Task 5 |
| `cancel_grace_seconds` | float, at least 0 | `2.0` | Task 3 |
| `max_message_bytes` | int, at least 65536 | `16777216` | Task 1, 3 |
| `pending_events_max` | int, at least 1 | `1000` | Task 6 |

## Review Focus

The five failure modes most likely to bite a person using this, each pinned by a named test in the task that owns the code:

1. **stdout pollution corrupts the stream.** A stray `print`, a `typer.echo` inside a reused doctor check, or a child process that inherits fd 1 writes non-ACP bytes, and the editor drops the connection. Expected: every byte on stdout is a valid ACP line; everything else lands on stderr. Pinned by `test_acp_stdout_carries_only_protocol_lines_when_code_and_children_print` (Task 3).
2. **Cancel races the prompt or a pending permission.** `session/prompt` and `session/cancel` arrive in one read, or cancel arrives while a permission request is out, or a cancel after a finished turn leaks into the next. Expected: exactly one stop reason per turn, `cancelled` when the cancel belongs to that turn, every pending permission resolved `cancelled` locally, the next turn unaffected. Pinned by the Hypothesis properties in Task 2 and `test_cancel_in_the_same_read_as_prompt_returns_cancelled` and `test_cancel_while_permission_pending_resolves_it_and_ends_turn` (Task 3, Task 4).
3. **A spend gate is offered over ACP.** Expected: no `session/request_permission` for any kind in `SPEND_GATE_KINDS`, whatever its options say; a message telling the operator to answer it on the host. Pinned by `test_spend_gates_are_never_offered_even_with_approve_options` (Task 4); the hub's own refusal stays as the second wall.
4. **Duplicate or colliding services.** A detached hub already holds `ServeLock` when the hub unit loads; the operator already installed `dev.vibey.worker`; two `vibey acp` processes (two editor windows) bootstrap or `kickstart -k` at the same time. Expected: one hub, no restart loop, an operator unit never overwritten, one restart per death. Pinned by `test_running_detached_hub_defers_the_hub_unit`, `test_existing_loaded_label_is_left_alone`, `test_two_processes_serialise_bootstrap_and_restart_once` (Task 8).
5. **Bootstrap hangs `session/new` or reruns every session.** Expected: `session/new` answers before any doctor probe completes; connect runs once per vibey version; a healthy machine costs one health probe per session. Pinned by `test_session_new_answers_before_slow_bootstrap_finishes` and `test_second_session_skips_connect_by_marker` (Task 7).

Also pinned, because the design implies them: the shared-peer refactor changes no MCP byte (`test_mcp_replies_are_byte_identical_to_the_golden_transcript`, Task 1); an oversized line is refused and the stream continues (`test_oversized_line_is_refused_and_the_next_line_is_served`, Task 1); a hub restart neither loses nor repeats live events (`test_live_stream_resumes_from_watermark_without_duplicates`, Task 5).

## File Structure

Create:

- `src/vibey/infrastructure/jsonrpc/__init__.py`
- `src/vibey/infrastructure/jsonrpc/errors.py`: value module: `PARSE_ERROR=-32700`, `INVALID_REQUEST=-32600`, `METHOD_NOT_FOUND=-32601`, `INVALID_PARAMS=-32602`, `INTERNAL_ERROR=-32603`, `RpcError(Exception)` with `code`, `message`, `data`.
- `src/vibey/infrastructure/jsonrpc/codec.py` + `interfaces/codec_interface.py`: line parse and encode, `ok`/`error` builders.
- `src/vibey/infrastructure/jsonrpc/peer.py` + `interfaces/peer_interface.py`: the asyncio bidirectional peer.
- `src/vibey/domain/acp/__init__.py`
- `src/vibey/domain/acp/protocol.py`: value module (method names, enums, error codes, `PROTOCOL_VERSION = 1`).
- `src/vibey/domain/acp/settings.py`: value module, `AcpSettings`.
- `src/vibey/domain/acp/session_state.py` + `interfaces/session_state_interface.py`
- `src/vibey/domain/acp/update_mapper.py` + `interfaces/update_mapper_interface.py`
- `src/vibey/domain/acp/gate_permission.py` + `interfaces/gate_permission_interface.py`
- `src/vibey/domain/acp/modes.py` + `interfaces/modes_interface.py`
- `src/vibey/application/acp/__init__.py`
- `src/vibey/application/acp/dto.py`: value module: `HubTurn`, `HubToolResult`, `LedgerPage`, `SessionRecord`, `SessionEvent`, `DoctorResult`, `UnitOutcome`.
- `src/vibey/application/acp/interfaces/`: `client_channel_interface.py`, `acp_hub_port_interface.py`, `service_loader_interface.py`, `host_connector_interface.py`, `postgres_installer_interface.py`, `doctor_probe_interface.py`, `acp_session_repository_interface.py`, plus one interface per class below.
- `src/vibey/application/acp/acp_agent.py`: method dispatch and the session registry.
- `src/vibey/application/acp/acp_prompt_turn.py`: one prompt turn.
- `src/vibey/application/acp/acp_live_feed.py`: ledger polling into updates.
- `src/vibey/application/acp/acp_bootstrap.py`: steps 1 to 4.
- `src/vibey/application/acp/acp_keep_alive.py`: step 5.
- `src/vibey/application/acp/doctor_checks.py`: extracted from the CLI.
- `src/vibey/application/acp/acp_session_service.py`: hub-side persistence and replay.
- `src/vibey/application/acp/acp_session_journal.py`: ACP-side ordered, bounded write-behind of session events to the hub.
- `src/vibey/infrastructure/acp/__init__.py`
- `src/vibey/infrastructure/acp/stdio_transport.py` + interface: fd guard, reader, writer.
- `src/vibey/infrastructure/acp/acp_hub_client.py`: implements `AcpHubPortInterface` over `HubGateway`.
- `src/vibey/infrastructure/acp/acp_settings_loader.py` + interface.
- `src/vibey/infrastructure/acp/service_loader.py`: launchctl and `systemctl --user` only.
- `src/vibey/infrastructure/acp/bootstrap_lock.py` + interface: flock on `<state_dir>/acp-bootstrap.lock`.
- `src/vibey/infrastructure/acp/acp_command_runner.py` + interface: `stdin=DEVNULL`, `sudo -n`.
- `src/vibey/infrastructure/acp/host_connector.py`: implements `HostConnectorInterface` over `HostInstaller`, with the version marker.
- `src/vibey/infrastructure/supervisor_installer.py` + `infrastructure/interfaces/supervisor_installer_interface.py`: path resolution and unit writing, extracted from `cli/supervisor.py`.
- `src/vibey/infrastructure/db/acp_session_repository.py` (declared by the application port).
- `src/vibey/infrastructure/db/migrations/0023_acp_session.sql`
- `src/vibey/cli/acp.py` + `cli/interfaces/acp_interface.py`
- `src/vibey/cli/doctor_probes.py` + `cli/interfaces/doctor_probes_interface.py`: the CLI-level probes (`SERVE.exposure_line`, `SABBATH`, `SUPERVISOR`, `HOST_HEALTH`, `GATE_NOTICE_DOCTOR`, the database sections) as `DoctorProbeInterface` objects.
- `docs/architecture/decisions/0101-the-acp-agent-and-self-installing-services.md`
- `docs/guides/acp.md`
- `changelog.d/acp-agent.feature.md`
- Tests: `tests/infrastructure/jsonrpc/`, `tests/domain/acp/`, `tests/application/acp/`, `tests/infrastructure/acp/`, `tests/infrastructure/db/test_acp_session_repository.py`, `tests/cli/test_acp_cli.py`, `tests/system/test_acp_conformance.py`, `tests/infrastructure/mcp/golden/mcp_transcript.jsonl`.

Modify:

- `src/vibey/infrastructure/mcp/stdio_server.py`: framing and error helpers come from `jsonrpc/codec.py`.
- `src/vibey/domain/hub_scope.py`: `HubAction.RECORD_ACP_SESSION` requiring `VIEW`.
- `src/vibey/domain/supervisor.py`: `HUB` service, `SupervisedService.restart`, `SupervisorPlanner.acp_services`.
- `src/vibey/infrastructure/driver/timer_units.py`: render `restart="always"`.
- `src/vibey/infrastructure/supervisor.py`, `src/vibey/cli/supervisor.py`: docstrings amended (ADR-0101); `install` delegates to `SupervisorInstaller`.
- `src/vibey/infrastructure/hub/app.py`, `src/vibey/cli/serve.py`: the session routes and their wiring.
- `src/vibey/domain/host_clients.py`: a Zed ACP client spec.
- `src/vibey/cli/main.py`: the `doctor` body uses `LOCAL_DOCTOR_CHECKS`; `app.command("acp")(acp_command)`.
- `src/vibey/bootstrap.py`: `build_acp_agent(...)`.
- `.importlinter`, `pyproject.toml` (dev dependency), `uv.lock`.
- `docs/reference/cli.md`, `docs/reference/configuration.md`, `docs/reference/hub-api.json`, `docs/reference/hub-api.md`, `docs/agents/instructions.toml` (100 to 101 ADRs), `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` (rendered), `README.md`, `docs/index.md`, `properdocs.yml`.
- The `vibey-chat-driver` skill in `.claude/skills/`, `.agents/skills/`, `.cursor/rules/vibey-chat-driver.mdc`, `.agent/rules/vibey-chat-driver.md`, `src/vibey_tools/skills/plugins/vibey/skills/vibey-chat-driver/SKILL.md`, and `docs/microslices/skills/vibey/skills/vibey-chat-driver/`.

---

### Task 1: The shared JSON-RPC peer, and the MCP server re-pointed at it

**Files:**
- Create: `src/vibey/infrastructure/jsonrpc/{__init__,errors,codec,peer}.py`, `src/vibey/infrastructure/jsonrpc/interfaces/{__init__,codec_interface,peer_interface}.py`
- Modify: `src/vibey/infrastructure/mcp/stdio_server.py`, `.importlinter`
- Test: `tests/infrastructure/jsonrpc/test_codec.py`, `tests/infrastructure/jsonrpc/test_peer.py`, `tests/infrastructure/mcp/test_mcp_golden.py`, `tests/infrastructure/mcp/golden/mcp_transcript.jsonl`

**Interfaces:**
- Consumes: nothing new.
- Produces:
  - `JsonRpcCodec.parse_line(line: str) -> Mapping[str, Any] | dict[str, Any]`: returns the parsed message, or a ready error response (`PARSE_ERROR` "Parse error: {msg}", `INVALID_REQUEST` "Invalid Request: expected JSON object") with `id: None`. Blank lines return `{}` and are skipped by callers via `JsonRpcCodec.is_blank(line: str) -> bool`.
  - `JsonRpcCodec.encode(message: Mapping[str, Any]) -> str` (exactly `json.dumps(message)`, no trailing newline).
  - `JsonRpcCodec.ok(msg_id: Any, result: Mapping[str, Any]) -> dict[str, Any]`, `JsonRpcCodec.error(msg_id: Any, code: int, message: str, data: Any = None) -> dict[str, Any]` (no `data` key when `None`).
  - `JsonRpcCodec.validate(message: Mapping[str, Any]) -> dict[str, Any] | None`: the MCP envelope check (`jsonrpc == "2.0"`, string `method` or a response shape), returning the error response or `None`.
  - `RequestHandler = Callable[[str, Mapping[str, Any]], Awaitable[Mapping[str, Any]]]`, `NotificationHandler = Callable[[str, Mapping[str, Any]], Awaitable[None]]`.
  - `JsonRpcPeer(reader: asyncio.StreamReader, write_line: Callable[[str], Awaitable[None]], *, on_request: RequestHandler, on_notification: NotificationHandler, codec: JsonRpcCodecInterface, id_prefix: str = "vibey", max_message_bytes: int = 16_777_216)`.
  - `async JsonRpcPeer.run() -> None` (returns at EOF), `async JsonRpcPeer.request(method: str, params: Mapping[str, Any], *, timeout: float | None = None) -> Mapping[str, Any]` (raises `RpcError` on an error response, `PeerClosed` at EOF, `TimeoutError` on timeout), `async JsonRpcPeer.notify(method: str, params: Mapping[str, Any]) -> None`, `JsonRpcPeer.cancel_outbound(predicate: Callable[[str, Mapping[str, Any]], bool]) -> tuple[str, ...]` (resolves matching pending outbound requests with `PeerCancelled` and returns their ids).
  - `PeerClosed(Exception)`, `PeerCancelled(Exception)` in `errors.py`.

- [ ] **Step 1: Capture the golden MCP transcript from the current code, before any change**

Write a one-off script in the scratchpad (not committed) that feeds every request in `tests/infrastructure/mcp/test_mcp_server.py`'s cases (initialize for each of the four protocol versions, ping, `tools/list`, `tools/call` success and each error branch, every protocol-error parametrisation, a notification, a blank line, a non-object line, malformed JSON) through `McpStdioServer(gateway=_StubGateway(...)).serve` and records `input<TAB>output` pairs. Commit the pairs as `tests/infrastructure/mcp/golden/mcp_transcript.jsonl`.

- [ ] **Step 2: Write the failing tests**

```python
# tests/infrastructure/mcp/test_mcp_golden.py
def test_mcp_replies_are_byte_identical_to_the_golden_transcript() -> None:
    for case in _golden_cases():
        assert MCP_SERVER.handle_line(case.input) == case.output  # str or None

# tests/infrastructure/jsonrpc/test_codec.py
def test_parse_line_reports_parse_error_with_null_id() -> None:
    assert CODEC.parse_line("{nope") == {"jsonrpc": "2.0", "id": None,
        "error": {"code": -32700, "message": "Parse error: Expecting property name enclosed in double quotes"}}
def test_parse_line_refuses_arrays_as_invalid_request() -> None: ...   # code -32600
def test_encode_never_emits_a_raw_newline() -> None:
    assert "\n" not in CODEC.encode({"text": "a\nb"})
def test_error_omits_data_when_none() -> None: ...

# tests/infrastructure/jsonrpc/test_peer.py  (pytest-asyncio; a StreamReader fed by the test)
async def test_inbound_request_gets_one_response_with_its_id() -> None: ...
async def test_notifications_never_get_a_response() -> None: ...
async def test_handlers_run_concurrently_so_a_notification_lands_mid_request() -> None:
    # handler for "slow" awaits an Event the "poke" notification sets; both arrive in one feed
async def test_handlers_start_in_arrival_order() -> None:
    # record the first synchronous statement of each handler; order equals line order
async def test_outbound_request_resolves_by_id_out_of_order() -> None: ...
async def test_outbound_error_response_raises_rpc_error_with_code() -> None: ...
async def test_unknown_response_id_is_logged_to_stderr_and_dropped() -> None: ...
async def test_handler_exception_becomes_internal_error_and_the_peer_keeps_serving() -> None: ...
async def test_rpc_error_from_handler_keeps_its_code_and_data() -> None: ...
async def test_unknown_method_is_method_not_found() -> None: ...   # when the handler raises RpcError(METHOD_NOT_FOUND)
async def test_writes_are_serialised_one_whole_line_at_a_time() -> None:
    # 50 concurrent notify() calls; every written chunk is exactly one json line ending "\n"
async def test_eof_fails_pending_outbound_with_peer_closed() -> None: ...
async def test_cancel_outbound_resolves_matching_requests_only() -> None: ...
async def test_oversized_line_is_refused_and_the_next_line_is_served() -> None:
    # max_message_bytes=65536; feed 70_000-byte line then a valid ping; expect -32600 (id None) then the ping reply
async def test_request_timeout_raises_timeout_error_and_forgets_the_id() -> None: ...
```

- [ ] **Step 3: Run them to see them fail**

Run: `uv run pytest -q tests/infrastructure/jsonrpc tests/infrastructure/mcp/test_mcp_golden.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'vibey.infrastructure.jsonrpc'` (the golden test passes against the old code once the import is from `stdio_server`; make it import `MCP_STDIO_SERVER` so it passes now and keeps passing).

- [ ] **Step 4: Implement the codec, the peer and re-point `McpStdioServer`**

The codec keeps `json.dumps` defaults (`ensure_ascii=True`, default separators), which is what makes the MCP bytes identical. The peer reads with `reader.readline()` inside a loop that catches `ValueError`/`asyncio.LimitOverrunError`, drains to the next `\n`, and answers `INVALID_REQUEST` "Invalid Request: message exceeds {max_message_bytes} bytes"; the `StreamReader` is created by the caller with `limit=max_message_bytes`. Each inbound message is dispatched with `asyncio.create_task` in arrival order; the task set is held so tasks are not garbage collected and are cancelled at EOF. One `asyncio.Lock` guards `write_line`. Outbound ids are `f"{id_prefix}-{n}"` from a counter. `McpStdioServer` keeps its synchronous loop and public methods; only `_ok`, `_error`, the constants and the `handle_line` parse move to the codec (re-export the four constants from `stdio_server.py` so existing imports hold).

- [ ] **Step 5: Run the suites, including the untouched MCP tests**

Run: `uv run pytest -q tests/infrastructure/jsonrpc tests/infrastructure/mcp && uv run coverage run -m pytest -q tests/infrastructure/jsonrpc tests/infrastructure/mcp && uv run coverage report --include='src/vibey/infrastructure/jsonrpc/*,src/vibey/infrastructure/mcp/stdio_server.py' --fail-under=100`
Expected: all pass, `TOTAL ... 100%`. `tests/infrastructure/mcp/test_mcp_server.py` is not edited.

- [ ] **Step 6: Gates and commit**

Run: `uv run ruff check . && uv run ruff format --check . && uv run mypy --strict src/vibey && uv run lint-imports`
Expected: no findings; `Contracts: N kept, 0 broken.`

```bash
git add src/vibey/infrastructure/jsonrpc tests/infrastructure/jsonrpc tests/infrastructure/mcp src/vibey/infrastructure/mcp/stdio_server.py .importlinter
git commit -m "refactor(mcp): factor a shared stdlib JSON-RPC codec and asyncio peer out of the MCP server"
```

---

### Task 2: Domain ACP types, settings, modes and the session state machine

**Files:**
- Create: `src/vibey/domain/acp/{__init__,protocol,settings,session_state,modes}.py`, `src/vibey/domain/acp/interfaces/{__init__,session_state_interface,modes_interface}.py`, `src/vibey/infrastructure/acp/{__init__,acp_settings_loader}.py`, `src/vibey/infrastructure/acp/interfaces/{__init__,acp_settings_loader_interface}.py`
- Modify: `pyproject.toml` (dev: `"agent-client-protocol==1.0.0"`), `uv.lock`, `.importlinter`
- Test: `tests/domain/acp/test_protocol.py`, `tests/domain/acp/test_session_state.py`, `tests/domain/acp/test_modes.py`, `tests/infrastructure/acp/test_acp_settings_loader.py`

**Interfaces:**
- Consumes: `HubScope` (`domain/hub_scope.py`).
- Produces:
  - `protocol.py`: `PROTOCOL_VERSION: Final = 1`; method constants `INITIALIZE="initialize"`, `AUTHENTICATE="authenticate"`, `SESSION_NEW="session/new"`, `SESSION_LOAD="session/load"`, `SESSION_RESUME="session/resume"`, `SESSION_LIST="session/list"`, `SESSION_CLOSE="session/close"`, `SESSION_PROMPT="session/prompt"`, `SESSION_CANCEL="session/cancel"`, `SESSION_SET_MODE="session/set_mode"`, `SESSION_UPDATE="session/update"`, `REQUEST_PERMISSION="session/request_permission"`; `class StopReason(StrEnum)` (`end_turn`, `max_tokens`, `max_turn_requests`, `refusal`, `cancelled`); `ToolCallStatus` (`pending`, `in_progress`, `completed`, `failed`); `ToolKind` (`read`, `edit`, `delete`, `move`, `search`, `execute`, `think`, `fetch`, `switch_mode`, `other`); `PlanEntryStatus` (`pending`, `in_progress`, `completed`); `PermissionKind` (`allow_once`, `allow_always`, `reject_once`, `reject_always`); `NoticeSeverity` (`info`, `warning`, `error`); `RESOURCE_NOT_FOUND: Final = -32002`, `AUTH_REQUIRED: Final = -32000`, `REQUEST_CANCELLED: Final = -32800`.
  - `settings.py`: `@dataclass(frozen=True) class AcpSettings` with exactly the keys and defaults of the `[acp]` table above (`services: tuple[str, ...]`, `modes: tuple[str, ...]`, `reject_words: tuple[str, ...]`).
  - `AcpSessionState(session_id: str)`: `begin_turn(turn_id: str) -> None` (raises `TurnAlreadyRunning`, a `VibeyError`, when a turn is active; raises `SessionClosed` when closed); `register_permission(request_id: str) -> None`; `resolve_permission(request_id: str) -> None`; `request_cancel() -> tuple[str, ...]` (marks the active turn cancelled and returns the pending permission ids; no-op returning `()` with no active turn); `finish_turn(proposed: StopReason) -> StopReason` (returns `CANCELLED` if this turn was cancelled, else `proposed`; clears the turn); `close() -> tuple[str, ...]` (cancels any active turn, idempotent); properties `turn_active: bool`, `cancel_requested: bool`, `closed: bool`, `pending_permissions: frozenset[str]`.
  - `AcpModes(settings: AcpSettings)`: `available() -> tuple[AcpMode, ...]` where `AcpMode(id: str, name: str, description: str)`; `scopes_for(mode_id: str, agent_scopes: frozenset[HubScope]) -> frozenset[HubScope]` (`observe` gives `{VIEW}`, `drive` gives `{VIEW, ANSWER, RUN}`, both intersected with `agent_scopes`; unknown id raises `UnknownMode`); `session_modes(current: str) -> dict[str, Any]` (the ACP `SessionModeState` dict).
  - `AcpSettingsLoader.load(path: Path) -> AcpSettings` and `from_mapping(section: Mapping[str, object]) -> AcpSettings`; missing file or table gives defaults; unknown key or wrong type raises `ConfigError` naming the key; each bound in the table is checked.

- [ ] **Step 1: Write the failing tests**

```python
# tests/domain/acp/test_session_state.py  (hypothesis)
EVENTS = st.lists(st.sampled_from(["begin", "perm", "resolve", "cancel", "finish", "close"]), max_size=40)

@given(EVENTS)
def test_every_begun_turn_ends_with_exactly_one_stop_reason(events: list[str]) -> None:
    # drive a model: count begun turns and finish_turn results; at the end, after close(),
    # begun == finished and every result is a StopReason member

@given(EVENTS)
def test_cancel_always_resolves_every_pending_permission(events: list[str]) -> None:
    # after request_cancel(), its returned ids equal the pending set before the call,
    # and finish_turn returns StopReason.CANCELLED

def test_cancel_without_a_turn_does_not_leak_into_the_next_turn() -> None:
    s = AcpSessionState("s"); s.request_cancel(); s.begin_turn("t1")
    assert s.finish_turn(StopReason.END_TURN) is StopReason.END_TURN

def test_a_second_begin_while_active_is_refused() -> None: ...   # TurnAlreadyRunning
def test_close_is_idempotent_and_refuses_new_turns() -> None: ...  # SessionClosed

# tests/domain/acp/test_modes.py
def test_observe_is_view_only_and_drive_never_contains_spend() -> None:
    modes = AcpModes(AcpSettings())
    assert modes.scopes_for("observe", AGENT_DEFAULT_SCOPES) == {HubScope.VIEW}
    assert HubScope.SPEND not in modes.scopes_for("drive", frozenset(HubScope))
def test_drive_is_narrowed_by_hub_agent_scopes() -> None:
    assert AcpModes(AcpSettings()).scopes_for("drive", frozenset({HubScope.VIEW})) == {HubScope.VIEW}
def test_session_modes_dict_validates_against_the_sdk_schema() -> None:
    from acp.schema import SessionModeState
    SessionModeState.model_validate(AcpModes(AcpSettings()).session_modes("drive"))

# tests/domain/acp/test_protocol.py
def test_enums_match_the_sdk_schema_literals() -> None:
    # for each enum, every value validates through the matching acp.schema model field

# tests/infrastructure/acp/test_acp_settings_loader.py
def test_missing_table_gives_defaults(tmp_path) -> None: ...
def test_unknown_key_is_refused_by_name(tmp_path) -> None: ...   # "[acp] probe_secs is not a known key"
@pytest.mark.parametrize("key,value", [("probe_seconds", 4), ("modes", []), ("default_mode", "spend"),
    ("services", ["delivery"]), ("restart", "never"), ("max_message_bytes", 1024), ("install_postgres", "yes")])
def test_out_of_bound_values_are_refused_by_name(tmp_path, key, value) -> None: ...
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv add --dev "agent-client-protocol==1.0.0" && uv run pytest -q tests/domain/acp tests/infrastructure/acp/test_acp_settings_loader.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'vibey.domain.acp'`.

- [ ] **Step 3: Implement the modules**

`AcpSessionState` holds `_turn: str | None`, `_cancelled: bool` (reset by `begin_turn` and `finish_turn`), `_pending: set[str]`, `_closed: bool`. `AcpModes` reads `settings.modes` for what it offers; mode names are `"Observe"` ("Read projects, gates and the ledger. Never answers or starts anything.") and `"Drive"` ("Read, answer non-spending gates, and start, pause or unwind work."). The loader mirrors `SupervisorSettingsLoader` (`infrastructure/supervisor.py`).

- [ ] **Step 4: Run tests, floors, gates**

Run: `uv run pytest -q tests/domain/acp tests/infrastructure/acp && uv run pytest -q tests/domain/test_domain_purity.py && uv run mypy --strict src/vibey && uv run lint-imports && uv lock --check`
Expected: PASS; purity test green over `domain/acp/`; lock consistent.

- [ ] **Step 5: Commit**

```bash
git add src/vibey/domain/acp src/vibey/infrastructure/acp tests/domain/acp tests/infrastructure/acp pyproject.toml uv.lock .importlinter
git commit -m "feat(acp): domain protocol types, [acp] settings, modes and the session state machine"
```

---

### Task 3: `vibey acp`: initialize, session/new, session/prompt over the hub chat, cancel

**Files:**
- Create: `src/vibey/domain/acp/update_mapper.py` + interface; `src/vibey/application/acp/{__init__,dto,acp_agent,acp_prompt_turn}.py`; `src/vibey/application/acp/interfaces/{__init__,client_channel_interface,acp_hub_port_interface,acp_agent_interface,acp_prompt_turn_interface}.py`; `src/vibey/infrastructure/acp/{stdio_transport,acp_hub_client}.py` + interfaces; `src/vibey/cli/acp.py`, `src/vibey/cli/interfaces/acp_interface.py`
- Modify: `src/vibey/bootstrap.py` (`build_acp_agent`), `src/vibey/cli/main.py` (one line: `app.command("acp")(acp_command)` next to `mcp`), `.importlinter`
- Test: `tests/domain/acp/test_update_mapper.py`, `tests/application/acp/test_acp_agent.py`, `tests/application/acp/test_acp_prompt_turn.py`, `tests/infrastructure/acp/test_stdio_transport.py`, `tests/infrastructure/acp/test_acp_hub_client.py`, `tests/cli/test_acp_cli.py`

**Interfaces:**
- Consumes: `JsonRpcPeer` and `RpcError` (Task 1); `AcpSettings`, `AcpSessionState`, `AcpModes`, `StopReason`, protocol constants (Task 2); `HubGatewayInterface.call(call: HubCall) -> HubGatewayResponse`, `HubGatewayInterface.agent_scopes()`; `HostToolsInterface.by_name(name) -> HostTool | None`, `.build_call(name, arguments, *, request_id) -> HubCall`, `.truncate(text, *, limit)`; `HubChatInterface.parse(message, *, project_id, open_gates) -> ChatIntent`, `.slash_commands()`.
- Produces:
  - `dto.py`: `HubTurn(reply: str, tool_calls: tuple[Mapping[str, Any], ...], gates: tuple[Mapping[str, Any], ...], project_id: UUID | None)`; `HubToolResult(ok: bool, status_code: int, text: str)`; `LedgerPage(events: tuple[Mapping[str, Any], ...], last_seq: int | None)`.
  - `ClientChannelInterface`: `async notify_update(session_id: str, update: Mapping[str, Any]) -> None`; `async request_permission(session_id: str, tool_call: Mapping[str, Any], options: Sequence[Mapping[str, Any]], *, timeout: float) -> str | None` (the selected `optionId`, or `None` for `cancelled`, timeout or a client error); `client_capabilities: Mapping[str, Any]` (set by `initialize`).
  - `AcpHubPortInterface`: `async chat(message: str, *, project_id: UUID | None, request_id: str) -> HubTurn`; `async call_tool(name: str, arguments: Mapping[str, Any], *, request_id: str) -> HubToolResult`; `async ledger_after(project_id: UUID, after: int, limit: int) -> LedgerPage`; `async healthy() -> bool`; `agent_scopes() -> frozenset[HubScope]`. Errors surface as `VibeyError` subclasses.
  - `AcpUpdateMapper`: `agent_text(text: str) -> dict[str, Any]` (`{"sessionUpdate": "agent_message_chunk", "content": {"type": "text", "text": text}}`), `user_text(text: str) -> dict[str, Any]`, `tool_call(tool_call_id: str, title: str, kind: ToolKind, raw_input: Mapping[str, Any]) -> dict[str, Any]` (status `pending`), `tool_call_update(tool_call_id: str, status: ToolCallStatus, text: str | None = None) -> dict[str, Any]`, `notice(title: str, severity: NoticeSeverity, description: str, *, client_notices: bool) -> dict[str, Any]` (an `agent_message_chunk` "title: description" when `client_notices` is false), `tool_kind_for(scope: HubScope) -> ToolKind` (`VIEW` to `read`, `RUN` to `execute`, else `other`).
  - `AcpAgent(channel, hub, settings, modes, mapper, chat, tools, turn_factory, *, version: str, new_id: Callable[[], str])`: `async handle_request(method: str, params: Mapping[str, Any]) -> Mapping[str, Any]` and `async handle_notification(method: str, params: Mapping[str, Any]) -> None` (the peer's two handlers); `sessions: Mapping[str, AcpSessionState]`.
  - `AcpPromptTurn.run(session: AcpSessionContext, prompt: Sequence[Mapping[str, Any]], *, turn_id: str) -> StopReason`.
  - `StdioTransport(*, stdin_fd: int = 0, stdout_fd: int = 1, stderr_fd: int = 2)`: `guard() -> int` (duplicates fd 1 to a private fd, points fd 1 at stderr with `os.dup2`, rebinds `sys.stdout` to `sys.stderr`; returns the private fd); `async reader(limit: int) -> asyncio.StreamReader` (`connect_read_pipe`; a thread reader fallback when stdin is not a pipe); `async write_line(line: str) -> None` (`asyncio.to_thread(os.write, private_fd, ...)` until every byte is written).
  - `AcpSessionContext` (a mutable dataclass in `application/acp/dto.py`, owned by the agent): `session_id: str`, `state: AcpSessionState`, `mode_id: str`, `project_id: UUID | None`, `offered_gates: set[str]`, `cwd: str`.
  - `bootstrap.build_acp_agent(*, settings: AcpSettings, channel: ClientChannelInterface, gateway: HubGatewayInterface = HUB_GATEWAY) -> AcpAgentInterface` (Task 7 adds `doctor_probes`, `connector`, `postgres`; Task 8 adds `services`, `lock`).
  - CLI: `AcpCommand.run(*, no_bootstrap: bool) -> None`; `def acp(no_bootstrap: Annotated[bool, typer.Option("--no-bootstrap", help=...)] = False) -> None` (module function because Typer builds commands from functions; reason written at the definition).

Behaviour the tests pin:
- `initialize` returns `{"protocolVersion": 1, "agentCapabilities": {"loadSession": true, "promptCapabilities": {"image": false, "audio": false, "embeddedContext": true}, "mcpCapabilities": {"http": false, "sse": false}, "sessionCapabilities": {"list": {}, "close": {}, "resume": {}}}, "agentInfo": {"name": "vibey", "title": "vibey", "version": <__version__>}, "authMethods": []}` whatever version the client asks for, and stores `clientCapabilities`.
- `session/new` requires an absolute `cwd` (else `INVALID_PARAMS`), allocates `sessionId` with `new_id`, returns `{"sessionId", "modes": AcpModes.session_modes(settings.default_mode)}`. If `mcpServers` is non-empty, one `agent_text` after the response says how many were ignored and why. If `cwd` is inside a project worktree it attaches (Task 5 implements the lookup; here `project_id` stays `None`).
- `session/prompt`: `state.begin_turn(turn_id)` is the first statement, before any `await`. Text blocks join with `"\n"`; `resource` blocks with `resource.text` append after a blank line. The turn parses locally with `HubChat.parse` only to learn `intent.tool_name`; if that tool's scope is outside the session mode's scopes, it replies "`/start` needs drive mode; switch with the mode picker" style text and returns `end_turn` with no hub call. Otherwise it sends `tool_call(f"{turn_id}-1", spec.title, kind, {"message": text})`, then `tool_call_update(..., in_progress)`, calls `hub.chat(text, project_id=..., request_id=f"acp-{session_id}-{turn_id}")`, then `tool_call_update(completed, <truncated JSON of tool_calls[0].result>)` or `failed` with the error text, then `agent_text(reply)`, and returns `end_turn`. A `LifecycleInvalid` from parsing returns `end_turn` after one `agent_text` with its message.
- `session/cancel` calls `state.request_cancel()` and cancels the turn task. A hub call already in flight is awaited for at most `cancel_grace_seconds`; if it returns, its real status is reported; if not, the update is `failed` with "cancelled before the hub answered; the hub may still apply it (request id {rid})". The prompt then answers `{"stopReason": "cancelled"}`. No exception from an aborted operation surfaces as a JSON-RPC error.
- A second `session/prompt` while one is active answers `INVALID_REQUEST` "a turn is already running in this session". Unknown `sessionId` answers `RESOURCE_NOT_FOUND`. `authenticate` answers `{}`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/application/acp/test_acp_agent.py  (FakeChannel records updates; FakeHub returns canned HubTurn)
async def test_initialize_advertises_v1_and_the_capability_set() -> None:
    result = await agent.handle_request("initialize", {"protocolVersion": 7, "clientCapabilities": {}})
    assert result["protocolVersion"] == 1 and result["authMethods"] == []
    InitializeResponse.model_validate(result)                       # acp.schema
async def test_session_new_refuses_a_relative_cwd() -> None: ...       # RpcError code -32602
async def test_session_new_returns_modes_with_the_default_mode() -> None:
    NewSessionResponse.model_validate(result); assert result["modes"]["currentModeId"] == "drive"
async def test_client_mcp_servers_are_ignored_with_one_message() -> None: ...
async def test_unknown_session_is_resource_not_found() -> None: ...    # -32002
async def test_second_prompt_while_running_is_invalid_request() -> None: ...

# tests/application/acp/test_acp_prompt_turn.py
async def test_prompt_streams_tool_call_pending_in_progress_completed_then_reply() -> None:
    kinds = [(u["sessionUpdate"], u.get("status")) for u in channel.updates]
    assert kinds == [("tool_call", "pending"), ("tool_call_update", "in_progress"),
                     ("tool_call_update", "completed"), ("agent_message_chunk", None)]
    for u in channel.updates: SessionNotification.model_validate({"sessionId": "s", "update": u})
    assert stop is StopReason.END_TURN
async def test_hub_refusal_marks_the_tool_call_failed_and_still_ends_turn() -> None: ...
async def test_observe_mode_refuses_run_intents_without_calling_the_hub() -> None:
    assert hub.calls == [] and "drive mode" in channel.texts[-1]
async def test_request_id_is_stable_per_session_and_turn() -> None:
    assert hub.calls[0].request_id == "acp-s-t1"
async def test_cancel_in_the_same_read_as_prompt_returns_cancelled() -> None:
    # through a real JsonRpcPeer: feed the prompt line and the cancel line in one chunk
    assert response["result"] == {"stopReason": "cancelled"}
async def test_cancel_during_slow_hub_call_reports_real_outcome_within_grace() -> None: ...
async def test_cancel_after_grace_reports_failed_with_request_id() -> None: ...
async def test_parse_error_is_a_message_not_a_jsonrpc_error() -> None: ...
async def test_embedded_resource_text_is_appended_to_the_message() -> None: ...

# tests/infrastructure/acp/test_stdio_transport.py
def test_guard_moves_fd1_to_stderr_and_returns_a_private_stdout() -> None: ...  # run in a subprocess

# tests/cli/test_acp_cli.py
def test_acp_stdout_carries_only_protocol_lines_when_code_and_children_print() -> None:
    # spawn [sys.executable, "-c", NOISY] where NOISY builds AcpCommand(before_serve=noisy) and calls
    # .run(no_bootstrap=True); noisy() print()s, typer.echo()s and runs `echo noise` as a child.
    # Send initialize; close stdin; read stdout to EOF
    for line in stdout.splitlines(): assert json.loads(line)["jsonrpc"] == "2.0"
    assert "noise" in stderr
def test_acp_command_is_registered_next_to_mcp() -> None: ...
```

`AcpCommand.__init__` takes `before_serve: Callable[[], None] = lambda: None`, called after `transport.guard()` and before the peer starts. It is an ordinary injection seam, so the guard is proven against a real `print`, `typer.echo` and an inheriting child without a test-only switch in the product.

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest -q tests/application/acp tests/domain/acp/test_update_mapper.py tests/infrastructure/acp tests/cli/test_acp_cli.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'vibey.application.acp'`.

- [ ] **Step 3: Implement**

`AcpHubClient` wraps every `HubGateway.call` in `asyncio.to_thread`. `chat` builds `HubCall(tool="vibey_chat", method="POST", route="/api/v1/chat/messages", body={"message": ..., "project_id": str(pid) or None, "request_id": rid})` and parses the JSON into `HubTurn`; a non-2xx becomes `HubGatewayError(f"hub refused ({status}): {text}")`. `healthy` is `GET /health/live`. `AcpCommand.run` order: `transport.guard()` first, then load `AcpSettings` from `Path.cwd() / "vibey.toml"`, configure logging to stderr, build the peer and the agent through `build_acp_agent`, `asyncio.run(peer.run())`.

- [ ] **Step 4: Run tests and the layer floors**

Run: `uv run pytest -q tests/application/acp tests/domain/acp tests/infrastructure/acp tests/cli/test_acp_cli.py && uv run coverage run -m pytest -q tests/application/acp tests/domain/acp tests/infrastructure/acp tests/cli/test_acp_cli.py && uv run coverage report --include='src/vibey/*/acp/*,src/vibey/cli/acp.py' --fail-under=100`
Expected: PASS, 100%.

- [ ] **Step 5: Gates and commit**

Run: `uv run ruff check . && uv run mypy --strict src/vibey && uv run lint-imports && uv run bandit -q -r src/vibey`
Expected: clean.

```bash
git add src/vibey/domain/acp src/vibey/application/acp src/vibey/infrastructure/acp src/vibey/cli/acp.py src/vibey/cli/interfaces/acp_interface.py src/vibey/cli/main.py src/vibey/bootstrap.py .importlinter tests
git commit -m "feat(acp): vibey acp serves initialize, session/new and streamed prompt turns over the hub chat"
```

---

### Task 4: Gates as permission requests; spend gates refused

**Files:**
- Create: `src/vibey/domain/acp/gate_permission.py` + `interfaces/gate_permission_interface.py`
- Modify: `src/vibey/application/acp/acp_prompt_turn.py`, `src/vibey/infrastructure/acp/acp_hub_client.py` (if `call_tool` needs it), the peer-backed channel in `src/vibey/cli/acp.py` or `infrastructure/acp/` (`request_permission` over `JsonRpcPeer.request`)
- Test: `tests/domain/acp/test_gate_permission.py`, `tests/application/acp/test_acp_gates.py`

**Interfaces:**
- Consumes: `SPEND_GATE_KINDS` (`domain/hub_scope.py`); `HubChat.parse_gate_answer(kind: str, raw: str) -> dict[str, Any]`; `HubTurn.gates` (dicts with `gate_id`, `project_id`, `kind`, `prompt`, `options`, `default_answer`, `is_spend`, `requires_scope`, `grant_key` from `HubChat.format_gate_prompt`); `ClientChannelInterface.request_permission` (Task 3); `AcpHubPortInterface.call_tool` (Task 3); `AcpSessionState.register_permission/resolve_permission` (Task 2).
- Produces:
  - `GatePermissionMapper(reject_words: tuple[str, ...], chat: HubChatInterface)`: `options_for(gate: Mapping[str, Any]) -> tuple[PermissionChoice, ...]` where `PermissionChoice(option_id: str, name: str, kind: PermissionKind, answer: Mapping[str, Any] | None)`; empty when `kind in SPEND_GATE_KINDS` or `gate["is_spend"]` is true, and empty when no option can be built. Choice and verdict gates get one choice per option (`reject_once` when the option, lower-cased, is in `reject_words`, else `allow_once`; `answer = chat.parse_gate_answer(kind, option)`). A `question` gate gets "Accept the defaults" (`allow_once`, `{"accept_defaults": true}`) and "Leave it open" (`reject_once`, `answer=None`). An `ANY_ANSWER_GATE_KINDS` gate gets "Acknowledge" (`allow_once`, `{}`) and "Leave it open". Any other kind (grant kinds that need a number) gives `()`. `option_id` is `f"{gate_id}:{index}"`.
  - `GatePermissionMapper.refusal_text(gate: Mapping[str, Any]) -> str`: for spend gates exactly `"Gate {gate_id} ({kind}) spends money, so I cannot answer it. Answer it on the host (`vibey answer {gate_id}`) or in the desktop or mobile app."`; for unmappable gates `"Gate {gate_id} ({kind}) needs a value. Answer it with `/answer {gate_id} <value>`."`.

Behaviour: after the hub reply, for each gate in `HubTurn.gates` not in `context.offered_gates`, oldest first, up to `max_gate_prompts_per_turn`: if `options_for` is empty, send `agent_text(refusal_text(gate))`; else send a `tool_call` titled `f"Answer gate: {prompt}"` (kind `other`), register the permission, call `request_permission(session_id, {"toolCallId": id}, options, timeout=permission_timeout_seconds)`. A selected allow option, or a reject option whose `answer` is not `None`, calls `hub.call_tool("vibey_answer_gate", {"gate_id": ..., "answer": ...}, request_id=f"acp-{session_id}-{gate_id}")` and closes the tool call `completed`; "Leave it open", `None` (cancelled or timeout) close it `failed` with "left open; nothing was answered". The gate id goes into `offered_gates` either way, so the same gate is not asked twice in a session.

- [ ] **Step 1: Write the failing tests**

```python
# tests/domain/acp/test_gate_permission.py
@pytest.mark.parametrize("kind", sorted(SPEND_GATE_KINDS))
def test_spend_gates_are_never_offered_even_with_approve_options(kind: str) -> None:
    assert MAPPER.options_for({"gate_id": "g", "kind": kind, "options": ["approve", "accept"], "is_spend": True}) == ()
    assert "spends money" in MAPPER.refusal_text({"gate_id": "g", "kind": kind})
def test_is_spend_flag_alone_refuses_an_unknown_kind() -> None: ...
def test_choice_options_map_to_allow_and_reject_by_reject_words() -> None:
    kinds = [c.kind for c in MAPPER.options_for({"gate_id": "g", "kind": "choice", "options": ["yes", "no"]})]
    assert kinds == [PermissionKind.ALLOW_ONCE, PermissionKind.REJECT_ONCE]
def test_question_gate_offers_defaults_or_leave_open() -> None: ...
def test_grant_gates_needing_a_number_are_not_offered() -> None: ...   # attempts_exhausted
def test_options_validate_against_the_sdk_permission_option() -> None: ...  # acp.schema.PermissionOption

# tests/application/acp/test_acp_gates.py
async def test_selected_allow_answers_the_gate_with_its_parsed_answer() -> None:
    assert hub.tool_calls == [("vibey_answer_gate", {"gate_id": G, "answer": {"choice": "yes"}}, f"acp-s-{G}")]
async def test_spend_gate_in_a_turn_sends_no_permission_request() -> None:
    assert channel.permission_requests == [] and "on the host" in channel.texts[-1]
async def test_permission_timeout_leaves_the_gate_open() -> None: ...
async def test_cancel_while_permission_pending_resolves_it_and_ends_turn() -> None:
    # channel.request_permission blocks; send session/cancel; expect stopReason cancelled,
    # state.pending_permissions empty, no vibey_answer_gate call
async def test_a_gate_is_offered_once_per_session() -> None: ...
async def test_at_most_max_gate_prompts_per_turn() -> None: ...
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest -q tests/domain/acp/test_gate_permission.py tests/application/acp/test_acp_gates.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'vibey.domain.acp.gate_permission'`.

- [ ] **Step 3: Implement the mapper and the turn's gate phase**

On `session/cancel` the agent calls `peer.cancel_outbound(lambda method, params: method == REQUEST_PERMISSION and params["sessionId"] == sid)` for the ids `request_cancel()` returned, so a client that never answers cannot hold the turn.

- [ ] **Step 4: Run tests and floors**

Run: `uv run pytest -q tests/domain/acp tests/application/acp && uv run coverage run -m pytest -q tests/domain/acp tests/application/acp && uv run coverage report --include='src/vibey/domain/acp/*,src/vibey/application/acp/*' --fail-under=100`
Expected: PASS, 100%.

- [ ] **Step 5: Commit**

```bash
git add src/vibey/domain/acp src/vibey/application/acp src/vibey/infrastructure/acp src/vibey/cli/acp.py tests/domain/acp tests/application/acp
git commit -m "feat(acp): offer answerable gates as permission requests and refuse spend gates"
```

---

### Task 5: Live ledger to plan and message updates; slash commands; modes

**Files:**
- Create: `src/vibey/application/acp/acp_live_feed.py` + `interfaces/acp_live_feed_interface.py`
- Modify: `src/vibey/domain/acp/update_mapper.py`, `src/vibey/application/acp/acp_agent.py`
- Test: `tests/domain/acp/test_update_mapper_live.py`, `tests/application/acp/test_acp_live_feed.py`, `tests/application/acp/test_acp_modes_and_commands.py`

**Interfaces:**
- Consumes: `AcpHubPortInterface.ledger_after` (Task 3); `Phase` (`domain/phase.py`); `CHAT_SLASH_COMMANDS` via `HubChatInterface.slash_commands()`; `AcpModes` (Task 2); `ClientChannelInterface.notify_update`.
- Produces:
  - `AcpUpdateMapper.phase_plan(phases_seen: Sequence[str], current: str) -> dict[str, Any]`: `{"sessionUpdate": "plan", "entries": [...]}` with one entry per phase in order DESIGN, VISUAL_DESIGN (only if seen), BUILD, REVIEW, DEPLOY_DESIGN, DEPLOY_EXECUTE, DEPLOY_REVIEW. Entry `content` is the phase label ("Design", "Visual design", "Build", "Review", "Deploy design", "Deploy execute", "Deploy review"), `priority` `high` for design to review and `low` for the deploy three, `status` `completed` before the current phase, `in_progress` at it, `pending` after. Going back from REVIEW to BUILD marks REVIEW `pending`. `done` with no deploy phase seen drops the deploy three and marks the rest `completed`. `abandoned` keeps statuses and the feed sends one `agent_text` "Project abandoned.".
  - `AcpUpdateMapper.ledger_summary(event: Mapping[str, Any], *, limit: int) -> dict[str, Any]`: `agent_text(f"[{phase}] {kind}: {summary}")` where `summary` is `payload["summary"]` or `payload["message"]` if a string, else omitted; truncated to `limit` with a trailing "...".
  - `AcpUpdateMapper.available_commands(specs: Sequence[ChatSlashSpec]) -> dict[str, Any]`: `{"sessionUpdate": "available_commands_update", "availableCommands": [{"name": spec.slash, "description": spec.description, "input": {"hint": <usage after the command word>} or None}]}`.
  - `AcpUpdateMapper.current_mode(mode_id: str) -> dict[str, Any]`.
  - `AcpLiveFeed(hub, channel, mapper, settings)`: `async follow(session_id: str, project_id: UUID, *, after: int) -> None` (runs until cancelled); `watermark(session_id: str) -> int`.
  - `AcpAgent` gains `session/set_mode` (`modeId` must be in `settings.modes`, else `INVALID_PARAMS`; replies `{}` and sends `current_mode_update`), sends `available_commands_update` right after every `session/new`, `session/load` and `session/resume` response, attaches when `cwd` is under a project root (the agent asks `hub.call_tool("vibey_projects", {}, ...)` and matches `cwd` against each project's `repo` path, longest match wins) and when a turn's `HubTurn.project_id` changes, starting or restarting the feed with `after` equal to the project's newest `seq` at attach time.

Watermark rule (sub-doctrine 10.g): the watermark is the last `seq` whose update `notify_update` returned for. A failed `ledger_after` (hub down, refused) leaves it unmoved and retries after `live_poll_seconds`; an event with `seq <= watermark` is skipped. The plan update is re-sent only when the phase changes. With `live_between_turns = false`, events that arrive outside a turn are buffered (at most `pending_events_max`) and flushed at the start of the next turn.

- [ ] **Step 1: Write the failing tests**

```python
# tests/domain/acp/test_update_mapper_live.py
def test_plan_marks_phases_before_current_completed() -> None:
    plan = MAPPER.phase_plan(["design", "build"], "build")
    assert [(e["content"], e["status"]) for e in plan["entries"]][:3] == [
        ("Design", "completed"), ("Build", "in_progress"), ("Review", "pending")]
def test_review_back_to_build_reopens_review() -> None: ...
def test_done_without_deploy_drops_the_deploy_entries() -> None: ...
def test_visual_design_appears_only_when_seen() -> None: ...
def test_available_commands_cover_every_chat_slash_command() -> None:
    names = {c["name"] for c in MAPPER.available_commands(CHAT_SLASH_COMMANDS)["availableCommands"]}
    assert names == {spec.slash for spec in CHAT_SLASH_COMMANDS}
def test_every_live_update_validates_against_the_sdk() -> None: ...

# tests/application/acp/test_acp_live_feed.py
async def test_live_stream_resumes_from_watermark_without_duplicates() -> None:
    # pages: [1,2,3], then HubGatewayError, then [3,4] (overlap after a hub restart)
    assert channel.seqs == [1, 2, 3, 4] and feed.watermark("s") == 4
async def test_failed_poll_leaves_watermark_unmoved() -> None: ...
async def test_plan_is_resent_only_on_phase_change() -> None: ...
async def test_between_turn_events_are_buffered_when_configured() -> None: ...

# tests/application/acp/test_acp_modes_and_commands.py
async def test_available_commands_follow_session_new() -> None: ...
async def test_set_mode_rejects_unknown_mode() -> None: ...           # -32602
async def test_set_mode_sends_current_mode_update_and_changes_scopes() -> None: ...
async def test_cwd_inside_a_project_repo_attaches_the_session() -> None: ...
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest -q tests/domain/acp/test_update_mapper_live.py tests/application/acp/test_acp_live_feed.py tests/application/acp/test_acp_modes_and_commands.py`
Expected: FAIL with `AttributeError: 'AcpUpdateMapper' object has no attribute 'phase_plan'`.

- [ ] **Step 3: Implement the mapper methods, the feed and the agent changes**

The feed polls with `hub.ledger_after(pid, after=watermark, limit=200)`, then `asyncio.sleep(live_poll_seconds)` when a page is short. A session close or a re-attach cancels its feed task.

- [ ] **Step 4: Run tests and floors**

Run: `uv run pytest -q tests/domain/acp tests/application/acp && uv run coverage run -m pytest -q tests/domain/acp tests/application/acp && uv run coverage report --include='src/vibey/domain/acp/*,src/vibey/application/acp/*' --fail-under=100`
Expected: PASS, 100%.

- [ ] **Step 5: Commit**

```bash
git add src/vibey/domain/acp src/vibey/application/acp tests/domain/acp tests/application/acp
git commit -m "feat(acp): stream the project ledger as a phase plan and messages; slash commands and modes"
```

---

### Task 6: Session persistence: migration, hub routes, load, list, close, resume

**Files:**
- Create: `src/vibey/infrastructure/db/migrations/0023_acp_session.sql`; `src/vibey/infrastructure/db/acp_session_repository.py`; `src/vibey/application/acp/interfaces/acp_session_repository_interface.py`; `src/vibey/application/acp/acp_session_service.py` + interface; `src/vibey/application/acp/acp_session_journal.py` + interface
- Modify: `src/vibey/domain/hub_scope.py` (`HubAction.RECORD_ACP_SESSION = "record_acp_session"`, `REQUIRED_SCOPE[...] = HubScope.VIEW`); `src/vibey/infrastructure/hub/app.py` (four routes, offered only when `acp_sessions` is passed to `HubAppFactory.build`); `src/vibey/cli/serve.py` (wire it); `src/vibey/infrastructure/acp/acp_hub_client.py`; `src/vibey/application/acp/acp_agent.py`; `docs/reference/hub-api.json`; `docs/reference/hub-api.md`
- Test: `tests/infrastructure/db/test_acp_session_repository.py`, `tests/application/acp/test_acp_session_service.py`, `tests/application/acp/test_acp_session_journal.py`, `tests/infrastructure/hub/test_hub_acp_sessions.py`, `tests/application/acp/test_acp_load_resume.py`

**Interfaces:**
- Consumes: `HubPrincipal` and `HubScopePolicy.permits`; `pg_pool` fixture; `AcpUpdateMapper` (Tasks 3, 5).
- Produces:
  - Migration `0023_acp_session.sql`: `CREATE TABLE acp_session (session_id text PRIMARY KEY, cwd text NOT NULL, created_by text NOT NULL, created_at timestamptz NOT NULL DEFAULT now())`; `CREATE TABLE acp_session_event (session_id text NOT NULL REFERENCES acp_session, seq bigint NOT NULL CHECK (seq >= 1), kind text NOT NULL CHECK (kind IN ('user_message','agent_message','tool_call','tool_call_update','plan','mode','attach','title','closed')), payload jsonb NOT NULL, recorded_at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY (session_id, seq))`; `BEFORE UPDATE OR DELETE` and `BEFORE TRUNCATE` triggers on both tables executing `public.ledger_refuse_rewrite()`; the grants the existing migrations give the application role (read the pattern from `0020_triaged_ticket.sql`).
  - `dto.py` additions: `SessionRecord(session_id: str, cwd: str, title: str | None, updated_at: datetime, closed: bool)`, `SessionEvent(seq: int, kind: str, payload: Mapping[str, Any])`.
  - `AcpSessionRepositoryInterface`: `async create(session_id: str, cwd: str, created_by: str) -> None` (idempotent: `ON CONFLICT DO NOTHING`); `async append(session_id: str, seq: int, kind: str, payload: Mapping[str, Any]) -> bool` (`True` on insert or on an identical replay, raises `SessionEventConflict` when the same `(session_id, seq)` has a different payload); `async events_after(session_id: str, after: int, limit: int) -> tuple[SessionEvent, ...]`; `async list(created_by: str, *, cwd: str | None, cursor: tuple[datetime, str] | None, limit: int) -> tuple[SessionRecord, ...]` (keyset on `(updated_at DESC, session_id DESC)`, `updated_at` being the newest event's `recorded_at`); `async owner(session_id: str) -> str | None`.
  - `AcpSessionService(repository, policy)`: the same four operations taking a `HubPrincipal` first, each authorised with `HubAction.RECORD_ACP_SESSION`, and each refusing a session owned by another principal with `HubForbidden`. The list cursor is an opaque URL-safe base64 of `updated_at.isoformat()|session_id`.
  - Routes (all `tags=["acp"]`): `POST /api/v1/acp/sessions` body `{session_id, cwd}` returns 201 `{session_id}`; `GET /api/v1/acp/sessions?cwd=&cursor=&limit=` returns `{sessions: [{session_id, cwd, title, updated_at, closed}], next_cursor}`; `POST /api/v1/acp/sessions/{session_id}/events` body `{seq, kind, payload}` returns 200 `{stored: true}` or 409; `GET /api/v1/acp/sessions/{session_id}/events?after=&limit=` returns `{events: [...], last_seq}`.
  - `AcpHubPortInterface` additions: `async create_session(session_id: str, cwd: str) -> None`, `async append_event(session_id: str, seq: int, kind: str, payload: Mapping[str, Any]) -> None`, `async session_events(session_id: str, after: int) -> tuple[SessionEvent, ...]` (pages until a short page), `async list_sessions(*, cwd: str | None, cursor: str | None) -> tuple[tuple[SessionRecord, ...], str | None]`.
  - `AcpSessionJournal(hub, settings)`: `record(session_id: str, kind: str, payload: Mapping[str, Any]) -> int` (assigns the next `seq`, queues, returns it); `async flush() -> None` (sends in `seq` order; stops at the first failure and keeps the queue, so a later flush resends from there; drops the oldest beyond `pending_events_max` and reports it once with a `notice`); `persisted_seq(session_id: str) -> int`.
  - `AcpAgent` additions: `session/load` (replays every event as its `session/update`: `user_message` to `user_message_chunk`, `agent_message` to `agent_message_chunk`, `tool_call`, `tool_call_update`, `plan`, `mode` to `current_mode_update`; folds `attach` and `mode` into the context; then answers `{"modes": ...}`), `session/resume` (folds without replay; answers `{"modes": ...}`), `session/list` (answers `{"sessions": [{"sessionId", "cwd", "title", "updatedAt"}], "nextCursor"}`), `session/close` (records `closed`, cancels any turn and feed, answers `{}`; unknown or already closed also answers `{}`). Load or resume of an unknown id answers `RESOURCE_NOT_FOUND`. A closed session refuses `session/prompt` with `RESOURCE_NOT_FOUND`.

Live ledger summaries are not persisted: they are re-readable from the ledger, and persisting them would copy the ledger into a second table.

- [ ] **Step 1: Write the failing tests**

```python
# tests/infrastructure/db/test_acp_session_repository.py  (pg_pool)
async def test_append_is_idempotent_for_an_identical_replay(pg_pool) -> None: ...
async def test_append_conflicting_payload_raises(pg_pool) -> None: ...
async def test_update_and_delete_are_refused_by_the_database(pg_pool) -> None:
    with pytest.raises(asyncpg.InsufficientPrivilegeError, match="append-only"):
        await conn.execute("UPDATE acp_session_event SET kind = 'plan'")
async def test_list_pages_by_keyset_with_no_gap_or_repeat_under_equal_timestamps(pg_pool) -> None:
    # 25 sessions whose newest events share one recorded_at; page size 10; union == all, no duplicates
async def test_list_is_scoped_to_the_creator(pg_pool) -> None: ...

# tests/application/acp/test_acp_session_service.py
async def test_another_principal_cannot_read_or_append() -> None: ...   # HubForbidden

# tests/infrastructure/hub/test_hub_acp_sessions.py  (TestClient; agent principal)
def test_routes_absent_without_acp_sessions() -> None: ...             # 404
def test_agent_principal_can_create_append_list_and_read() -> None: ...
def test_conflicting_append_is_409() -> None: ...

# tests/application/acp/test_acp_session_journal.py
async def test_flush_sends_in_order_and_resumes_after_a_failure() -> None: ...
async def test_overflow_drops_oldest_and_notices_once() -> None: ...

# tests/application/acp/test_acp_load_resume.py
async def test_load_replays_history_before_responding() -> None:
    assert channel.log[-1] == ("response", "session/load") and channel.kinds[:3] == [
        "user_message_chunk", "tool_call", "tool_call_update"]
async def test_resume_does_not_replay() -> None: ...
async def test_close_is_idempotent_and_unknown_close_is_empty_result() -> None: ...
async def test_list_maps_to_acp_shape_and_validates() -> None: ...       # acp.schema.ListSessionsResponse
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest -q tests/infrastructure/db/test_acp_session_repository.py tests/application/acp tests/infrastructure/hub/test_hub_acp_sessions.py`
Expected: FAIL (`relation "acp_session" does not exist` and missing modules).

- [ ] **Step 3: Implement migration, repository, service, routes, journal and agent methods**

Then regenerate the API document: `uv run vibey serve --openapi > docs/reference/hub-api.json`, and add the four routes to `docs/reference/hub-api.md`.

- [ ] **Step 4: Run tests, the API-document test and floors**

Run: `uv run pytest -q tests/infrastructure/db/test_acp_session_repository.py tests/application/acp tests/infrastructure/hub tests/cli/test_serve_cli.py::test_the_committed_openapi_document_is_what_serve_prints tests/meta/test_migration_numbering.py`
Expected: PASS. Then the four floors for the touched layers as in Task 3 step 4, plus `--include='src/vibey/infrastructure/db/acp_session_repository.py,src/vibey/infrastructure/hub/app.py'`.

- [ ] **Step 5: Commit**

```bash
git add src/vibey tests docs/reference/hub-api.json docs/reference/hub-api.md
git commit -m "feat(acp): persist ACP sessions through the hub; load, resume, list and close"
```

---

### Task 7: `DoctorChecks` extraction and `AcpBootstrap` steps 1, 2 and 4

**Files:**
- Create: `src/vibey/application/acp/doctor_checks.py` + interface; `src/vibey/application/acp/interfaces/{doctor_probe_interface,host_connector_interface,postgres_installer_interface}.py`; `src/vibey/application/acp/acp_bootstrap.py` + interface; `src/vibey/cli/doctor_probes.py` + `cli/interfaces/doctor_probes_interface.py`; `src/vibey/infrastructure/acp/{host_connector,acp_command_runner}.py` + interfaces
- Modify: `src/vibey/cli/main.py` (the `doctor` body only), `src/vibey/bootstrap.py` (`build_acp_agent` gains `doctor_probes`, `connector`, `postgres`), `src/vibey/application/acp/acp_agent.py`
- Test: `tests/application/acp/test_doctor_checks.py`, `tests/cli/test_doctor_probes.py`, `tests/application/acp/test_acp_bootstrap.py`, `tests/infrastructure/acp/test_host_connector.py`, `tests/infrastructure/acp/test_acp_command_runner.py`; the existing `tests/cli/test_doctor_json.py` and `tests/cli/test_doctor_database.py` unchanged

**Interfaces:**
- Consumes: `HostInstallerInterface.build_plan(requested) -> tuple[ConnectPlanItem, ...]`, `.apply_plan(plan)`; `HostClientSpec.scope`; `PostgresLocalService(command_runner=...)` `.status() -> PostgresStatus`, `.install() -> PostgresInstallResult`; `SERVE.exposure_line`, `SABBATH.doctor_lines()`, `SUPERVISOR.doctor_lines()`, `HOST_HEALTH.doctor_lines()`, `GATE_NOTICE_DOCTOR.line()`, `_database_security_section`, `_passwordless_reach_section` (moved into `cli/doctor_probes.py`); `ClientChannelInterface`; `AcpUpdateMapper`.
- Produces:
  - `dto.DoctorResult(mark: Literal["PASS", "WARN", "FAIL", "UNKNOWN"], name: str, detail: str)`.
  - `DoctorProbeInterface`: `name: str`; `async run() -> tuple[DoctorResult, ...]`. A probe never writes to stdout; the CLI-level probes that wrap printing helpers capture with `contextlib.redirect_stdout` and parse `DoctorFormat` lines.
  - `DoctorChecks(probes: Sequence[DoctorProbeInterface])`: `async run() -> tuple[DoctorResult, ...]` (a probe that raises becomes one `FAIL` result named after it; the rest still run); `passed(results) -> bool` (no `FAIL`).
  - `cli/doctor_probes.py`: `LOCAL_DOCTOR_PROBES: Final[tuple[DoctorProbeInterface, ...]]` (hub exposure, sabbath, gate notice, supervisor, host health, database security, passwordless reach) and `LOCAL_DOCTOR_CHECKS: Final = DoctorChecks(LOCAL_DOCTOR_PROBES)`. `cli/main.py`'s `doctor` replaces its seven sequential calls with one `LOCAL_DOCTOR_CHECKS.run()` and prints each result through `out`; the printed text and the `--json` document stay byte-identical (the existing doctor tests are the proof).
  - `HostConnectorInterface`: `async connect_detected() -> tuple[DoctorResult, ...]`: applies `HostInstaller` plans only for clients with `scope == "user"` whose config file's parent directory exists; a `HostClientError` for one client is a `WARN` for that client and the others continue; writes `<state_dir>/acp-connect-<version>.json` listing the applied client ids; `already_connected() -> bool` reads that marker.
  - `PostgresInstallerInterface`: `status() -> PostgresStatus`, `install() -> PostgresInstallResult`, implemented by `PostgresLocalService(command_runner=AcpCommandRunner())`.
  - `AcpCommandRunner.__call__(argv: tuple[str, ...]) -> PostgresCommandResult`: `subprocess.run(..., stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=...)`; an argv starting with `"sudo"` without `"-n"` becomes `("sudo", "-n", *rest)`.
  - `AcpBootstrap(settings, checks, connector, postgres, channel, mapper, lock)`: `start(session_id: str) -> None` (schedules steps 1 to 3 as one task after the `session/new` response is written; no-op when `auto_bootstrap` is false or when a bootstrap for this process already finished healthy); `async before_first_prompt(context: AcpSessionContext) -> None` (waits for the background task up to `bootstrap_timeout_seconds`, then runs step 4 once per process); `done: bool`.
  - Step 1 sends `tool_call("bootstrap-doctor", "vibey doctor", read)`, one `tool_call_update` per completed probe with the result lines, then `completed` (or `failed` when any `FAIL`).
  - Step 2 runs when `auto_connect` and not `already_connected()`, as `tool_call("bootstrap-connect", "vibey connect", edit)`.
  - Step 4 runs when PostgreSQL `status().ready` is false and `install_postgres == "ask"`: a `tool_call("bootstrap-postgres", "Install PostgreSQL", execute)` and a permission with options "Install PostgreSQL" (`allow_once`) and "Not now" (`reject_once`), titled "Install PostgreSQL with {brew|apt-get|dnf}? On Linux this needs sudo; if sudo asks for a password, run `vibey doctor --install-postgres` in your own terminal." On allow, `install()` runs in `asyncio.to_thread`; its `detail` is reported; a failure whose detail says sudo needs a password is reported with that exact command. On reject, timeout or cancel, one message says what is missing and that the hub runs degraded.

- [ ] **Step 1: Write the failing tests**

```python
# tests/application/acp/test_acp_bootstrap.py
async def test_session_new_answers_before_slow_bootstrap_finishes() -> None:
    # a probe that awaits an Event never set during the request; session/new response is written,
    # and only then does the "vibey doctor" tool_call appear
    assert channel.log.index(("response", "session/new")) < channel.log.index(("update", "tool_call"))
async def test_second_session_skips_connect_by_marker() -> None: ...
async def test_postgres_is_asked_inside_the_first_prompt_only() -> None:
    assert channel.permission_requests[0]["session"] == "s" and len(channel.permission_requests) == 1
async def test_postgres_never_setting_never_asks() -> None: ...
async def test_rejected_postgres_continues_degraded_with_a_message() -> None: ...
async def test_auto_bootstrap_false_runs_nothing() -> None: ...
async def test_bootstrap_timeout_lets_the_prompt_proceed_with_a_notice() -> None: ...

# tests/application/acp/test_doctor_checks.py
async def test_a_raising_probe_is_one_fail_and_the_rest_run() -> None: ...

# tests/cli/test_doctor_probes.py
async def test_printing_helpers_are_captured_not_leaked(capsys) -> None:
    results = await LOCAL_DOCTOR_CHECKS.run(); assert capsys.readouterr().out == ""

# tests/infrastructure/acp/test_host_connector.py
def test_only_user_scope_clients_with_an_existing_config_dir_are_connected(tmp_path) -> None:
    # .mcp.json and .vscode/mcp.json are never written into cwd
def test_one_client_error_is_a_warn_and_others_continue(tmp_path) -> None: ...

# tests/infrastructure/acp/test_acp_command_runner.py
def test_sudo_becomes_non_interactive_and_stdin_is_closed(monkeypatch) -> None:
    assert seen.argv == ("sudo", "-n", "apt-get", "update") and seen.stdin is subprocess.DEVNULL
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest -q tests/application/acp/test_acp_bootstrap.py tests/application/acp/test_doctor_checks.py tests/cli/test_doctor_probes.py tests/infrastructure/acp`
Expected: FAIL with missing modules.

- [ ] **Step 3: Implement, keeping `vibey doctor` output identical**

- [ ] **Step 4: Run the new tests, the existing doctor tests and floors**

Run: `uv run pytest -q tests/application/acp tests/cli/test_doctor_probes.py tests/cli/test_doctor_json.py tests/cli/test_doctor_database.py tests/infrastructure/acp` then the four floors (`domain`, `application`, `infrastructure`, `cli`) as in `CLAUDE.md`.
Expected: PASS; four floors at 100%.

- [ ] **Step 5: Commit**

```bash
git add src/vibey tests
git commit -m "feat(acp): run doctor and connect on first contact and ask before installing PostgreSQL"
```

---

### Task 8: Service loading, keep-alive, ADR-0101, and the canon note

**Files:**
- Create: `src/vibey/infrastructure/supervisor_installer.py` + `infrastructure/interfaces/supervisor_installer_interface.py`; `src/vibey/infrastructure/acp/{service_loader,bootstrap_lock}.py` + interfaces; `src/vibey/application/acp/interfaces/service_loader_interface.py`; `src/vibey/application/acp/acp_keep_alive.py` + interface; `docs/architecture/decisions/0101-the-acp-agent-and-self-installing-services.md`
- Modify: `src/vibey/domain/supervisor.py`, `src/vibey/infrastructure/driver/timer_units.py`, `src/vibey/infrastructure/supervisor.py` (docstring), `src/vibey/cli/supervisor.py` (`install` delegates; docstring), `src/vibey/application/acp/acp_bootstrap.py` (step 3), `src/vibey/bootstrap.py` (gateway `starter` and `build_acp_agent(services=..., lock=...)`), `properdocs.yml`, `docs/agents/instructions.toml` and the rendered `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md`, `docs/index.md` (100 to 101 ADRs)
- Test: `tests/domain/test_supervisor.py` (added cases), `tests/infrastructure/test_timer_units_restart.py`, `tests/infrastructure/test_supervisor_installer.py`, `tests/infrastructure/acp/test_service_loader.py`, `tests/infrastructure/acp/test_bootstrap_lock.py`, `tests/application/acp/test_acp_services.py`, `tests/application/acp/test_acp_keep_alive.py`; existing `tests/cli/test_supervisor_cli.py` unchanged

**Interfaces:**
- Consumes: `SupervisorSettings`, `SupervisedService`, `SupervisorPaths`, `SupervisorPlanner` (`domain/supervisor.py`); `TimerUnitRenderer.launchd_service/systemd_service`; `SupervisorHost.state(label) -> str`, `.unit_dir()`, `.unit_path(label, out)`, `.default_env_file()`, `.volatile_roots()`; `ServingRecord` and `LocalTokenStore(state_dir).serving()`; `HubGateway(starter=...)`; `AcpHubPortInterface.healthy()`.
- Produces:
  - `domain/supervisor.py`: `HUB: Final = "hub"`; `SupervisedService.restart: Literal["on-failure", "always"] = "on-failure"`; `SupervisorPlanner.acp_services(settings: SupervisorSettings, paths: SupervisorPaths, *, names: tuple[str, ...], restart: Literal["on-failure", "always"]) -> tuple[SupervisedService, ...]` (hub argv `(*launcher, vibey, "serve")`, worker argv as `services` builds it, labels `f"{label_prefix}.{name}"`, logs `hub.log` and `worker.log`; never delivery or state-sync).
  - `TimerUnitRenderer`: `restart="always"` renders launchd `<key>KeepAlive</key>\n  <true/>` and systemd `Restart=always`; `on-failure` output is unchanged byte for byte.
  - `SupervisorInstaller(host, planner, renderer, *, which, python, linked_worktree)`: `paths(settings: SupervisorSettings, repo: Path) -> SupervisorPaths` (moved from `SupervisorCommand._paths`, same refusals and messages); `write(services: Sequence[SupervisedService], settings: SupervisorSettings, *, out: Path | None, overwrite: bool) -> tuple[UnitOutcome, ...]` where `dto.UnitOutcome(label: str, path: str, action: Literal["created", "unchanged", "kept-differing", "updated", "loaded", "already-loaded", "restarted", "deferred", "failed"], detail: str)`. `vibey supervisor install` calls it with `overwrite=True` (today's behaviour); ACP calls it with `overwrite=False`.
  - `ServiceLoaderInterface` (application port) implemented by `ServiceLoader(host: SupervisorHostInterface, run: ServiceRunner, uid: int)`: `state(label: str) -> str`; `load(label: str, unit: Path) -> UnitOutcome` (launchd: `launchctl print gui/<uid>/<label>`; when not loaded, `launchctl bootstrap gui/<uid> <unit>`; systemd: `systemctl --user daemon-reload` then `systemctl --user enable --now <label>.service`); `restart(label: str) -> UnitOutcome` (`launchctl kickstart -k gui/<uid>/<label>` or `systemctl --user restart <label>.service`); `available() -> bool` (systemd: `systemctl --user is-system-running` exits with a bus error when there is no user manager). Every argv it may issue starts with `launchctl` or `systemctl --user`, never names the `system` launchd domain, never `sudo`.
  - `BootstrapLock(state_dir: Path)`: `async hold(timeout: float) -> AsyncContextManager[bool]` (flock on `<state_dir>/acp-bootstrap.lock` taken in a thread; yields `False` on timeout, never raises).
  - `AcpBootstrap` step 3 (inside the lock): when `auto_services`, plan `acp_services(names=settings.services, restart=settings.restart)` with `repo = settings.service_workdir or <env_file dir>`; `write(..., overwrite=False)`; for each service: if `state(label) == "running"`, leave it ("already loaded"); if it is the hub and a live `ServingRecord` exists whose pid the service manager does not own, do not load the hub unit now and send a notice "the hub is running outside the service manager (pid N); keep-alive takes it over when it exits"; else `load`. Then poll `hub.healthy()` up to `bootstrap_timeout_seconds`. When `available()` is false, fall back to `vibey hub start` once and notice that services cannot be kept alive on this host. A first-time load sends a notice listing each label and the unload commands from `SupervisorHost.load_commands`'s counterpart (`launchctl bootout gui/<uid>/<label>`, `systemctl --user disable --now <label>.service`).
  - `AcpKeepAlive(loader, hub, lock, channel, mapper, settings)`: `async probe(context) -> None` (called at the start of every prompt and every `probe_seconds` while any session is open; when `healthy()` is false or a worker label is not `running`: take the lock, probe again, and only then `restart`; one `notice` per state transition per label, not per probe); `start()`/`stop()` manage the timer task.
  - `bootstrap.build_acp_agent` passes `HubGateway(starter=lambda: loader.restart(hub_label).action != "failed")` when `auto_services` is on, so the gateway never spawns a detached hub that races the unit.

- [ ] **Step 1: Write the failing tests**

```python
# tests/domain/test_supervisor.py (added)
def test_acp_services_plans_hub_and_worker_only_with_always_restart() -> None: ...
# tests/infrastructure/test_timer_units_restart.py
def test_always_renders_keepalive_true_and_restart_always() -> None: ...
def test_on_failure_output_is_unchanged() -> None: ...       # equals a committed golden string
# tests/infrastructure/test_supervisor_installer.py
def test_overwrite_false_keeps_a_differing_operator_unit(tmp_path) -> None:
    assert outcome.action == "kept-differing" and unit.read_text() == operator_text
# tests/infrastructure/acp/test_service_loader.py
def test_every_issued_argv_is_user_scoped_and_never_sudo() -> None:
    for argv in runner.calls:
        assert argv[0] in ("launchctl", "systemctl") and "sudo" not in argv
        assert argv[0] != "systemctl" or argv[1] == "--user"
        assert not any(a.startswith("system/") for a in argv)
def test_existing_loaded_label_is_left_alone() -> None:
    assert not any(a[1] in ("bootstrap", "bootout") for a in runner.calls)
def test_no_user_systemd_bus_is_reported_unavailable() -> None: ...
# tests/infrastructure/acp/test_bootstrap_lock.py
async def test_second_holder_waits_then_times_out_false(tmp_path) -> None: ...
# tests/application/acp/test_acp_services.py
async def test_running_detached_hub_defers_the_hub_unit() -> None:
    assert ("load", "dev.vibey.hub") not in loader.calls and "outside the service manager" in channel.texts[-1]
async def test_first_load_notices_the_unload_commands() -> None: ...
async def test_unavailable_service_manager_falls_back_to_hub_start_once() -> None: ...
# tests/application/acp/test_acp_keep_alive.py
async def test_dead_hub_is_restarted_and_noticed_once() -> None: ...
async def test_two_processes_serialise_bootstrap_and_restart_once(tmp_path) -> None:
    # two AcpKeepAlive instances sharing one BootstrapLock dir and one fake loader;
    # after the first restart the second's re-probe sees healthy and does nothing
    assert loader.calls.count(("restart", "dev.vibey.hub")) == 1
async def test_crash_looping_worker_notices_once_per_transition() -> None: ...
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest -q tests/domain/test_supervisor.py tests/infrastructure/test_timer_units_restart.py tests/infrastructure/test_supervisor_installer.py tests/infrastructure/acp tests/application/acp`
Expected: FAIL (`AttributeError: 'SupervisorPlanner' object has no attribute 'acp_services'` and missing modules).

- [ ] **Step 3: Implement code, then write ADR-0101**

ADR-0101 follows ADR-0100's header (`**Status:** proposed`, date, `**Cites:** SD-01 v1.0; proposed sub-doctrine 12.q; sub-doctrines 10.g, 10.h, 12.c, 12.d, 12.e`, `**Related:** ADR-0016, ADR-0017, ADR-0018, ADR-0023, ADR-0046, ADR-0055, ADR-0068, ADR-0070, ADR-0071, ADR-0091, ADR-0100`, an `**Owes:**` line like ADR-0100's). Sections: Context (an editor launches agents; first contact on a fresh machine; the "operator loads" stance of ADR-0070 and #1189); Decision: (1) vibey is an ACP v1 agent over newline-delimited stdio JSON-RPC on a shared stdlib peer; (2) every action goes through the hub as the agent principal, spend gates never offered, a permission prompt never answers by silence; (3) sessions persist through the hub, append-only; (4) the amendment: "vibey loads user-level units only (launchd `gui/<uid>`, `systemctl --user`), never system ones, never with sudo, only while `[acp] auto_bootstrap` and `[acp] auto_services` are true, and it says what it loaded and how to unload it"; (5) privileged steps are asked through the client and run non-interactively or not at all; (6) one bootstrap lock per user. Consequences, including the default-true grant ruled by the operator on 2026-11-20 and its tension with 12.d, recorded for the canon PR to settle. Amend the two docstrings to cite ADR-0101. Add the nav entry in `properdocs.yml`; change both ADR counts in `docs/agents/instructions.toml` (the `100 ADRs` phrase and the `0001` to `0100` range become `101 ADRs` and `0001` to `0101`), then `python3 scripts/agent_instructions.py render`; edit `README.md` and `docs/index.md` by hand.

- [ ] **Step 4: Run tests, meta tests and floors**

Run: `uv run pytest -q tests/domain tests/infrastructure tests/application/acp tests/cli/test_supervisor_cli.py tests/meta/test_adr_counts.py && python3 scripts/agent_instructions.py check && uv run vibey-gh corpus-index --check` then the four floors.
Expected: PASS; `test_the_advertised_count_matches_the_adrs_on_disk` passes for all five files.

- [ ] **Step 5: Commit**

```bash
git add src/vibey tests docs/architecture/decisions/0101-the-acp-agent-and-self-installing-services.md properdocs.yml docs/agents/instructions.toml CLAUDE.md AGENTS.md GEMINI.md README.md docs/index.md
git commit -m "feat(acp): install, load and keep alive the user-level hub and worker units (ADR-0101)"
```

- [ ] **Step 6: Open the separate canon PR (the operator merges it; never this branch)**

Branch `docs/canon-12q-acp-grant` from `origin/develop`. Edit only `src/vibey_tools/gh/docs/doctrines.md` (append after 12.o in doctrine 12, "Humans first") and regenerate the index with `uv run vibey-gh corpus-index` (then `--check`). Proposed text, marked `*(proposed; ratification requires the operator's merge)*`:

> **12.q, a driven surface acts within a declared grant**: a surface a model drives (MCP, ACP, chat) holds a scoped principal that can never spend, and the hub, not the surface, enforces it. What such a surface keeps running on the person's machine runs as that person, at user level, never system-wide, and only while a grant declared in configuration says so; it says what it started and how to stop it. A step that needs more authority than the person's own is asked of the person through the surface's own prompt, runs without a password typed into the machine on their behalf, or does not run. Silence, a timeout or a dropped connection is never a yes (12.d).

The PR body names ADR-0101 and says the operator's merge ratifies it (Article II.3). Do not merge, approve or enable auto-merge.

---

### Task 9: `vibey connect` registers vibey as a Zed ACP agent; the documentation

**Files:**
- Modify: `src/vibey/domain/host_clients.py`, `src/vibey/infrastructure/mcp/host_installer.py` (launch per protocol), `src/vibey/cli/connect.py` (plan print shows the protocol), `docs/reference/cli.md`, `docs/reference/configuration.md`, the `vibey-chat-driver` skill in all six places, `properdocs.yml`
- Create: `docs/guides/acp.md`, `changelog.d/acp-agent.feature.md`
- Test: `tests/domain/test_host_clients.py` (added cases), `tests/cli/test_connect_cli.py` (added cases), `tests/meta/test_agent_tree_parity.py` (unchanged, must pass)

**Interfaces:**
- Consumes: `HostClientSpec`, `HostClients.plan_one`, `_merge_json`, `McpLaunchCommand`.
- Produces:
  - `HostClientSpec.protocol: Literal["mcp", "acp"] = "mcp"` and `HostClientSpec.entry_type: str | None = None`.
  - A new spec `HostClientSpec(client_id="zed", label="Zed", scope="user", format="json", root_key="agent_servers", include_stdio_type=False, description="User-level `~/.config/zed/settings.json` (`agent_servers.vibey`) registers `vibey acp` as an external agent.", protocol="acp", entry_type="custom")`; `config_path` returns `f"{home}/.config/zed/settings.json"` on both platforms.
  - `HostClients.resolve_launch(*, which_vibey: str | None, python_executable: str, protocol: Literal["mcp", "acp"] = "mcp") -> McpLaunchCommand` (args `("acp",)` or the Python fallback with `run(['acp'])`).
  - `_merge_json` writes `{"type": entry_type, "command", "args", "env": {}}` when `entry_type` is set. A Zed file that is not strict JSON raises `HostClientError` whose message ends with the exact snippet to paste: `"agent_servers": {"vibey": {"type": "custom", "command": "<path>", "args": ["acp"], "env": {}}}`. The file is never rewritten in that case.

- [ ] **Step 1: Write the failing tests**

```python
# tests/domain/test_host_clients.py
def test_zed_entry_is_a_custom_agent_server_running_vibey_acp() -> None:
    doc = json.loads(item.new_content)
    assert doc["agent_servers"]["vibey"] == {"type": "custom", "command": "/usr/local/bin/vibey", "args": ["acp"], "env": {}}
def test_zed_keeps_other_settings_and_other_agent_servers() -> None: ...
def test_commented_zed_settings_are_refused_with_the_snippet_and_not_rewritten() -> None:
    with pytest.raises(HostClientError, match=r'"args": \["acp"\]'): ...
def test_mcp_clients_still_launch_vibey_mcp() -> None: ...
# tests/cli/test_connect_cli.py
def test_connect_list_names_zed_as_an_acp_client() -> None: ...
```

- [ ] **Step 2: Run them to see them fail**

Run: `uv run pytest -q tests/domain/test_host_clients.py tests/cli/test_connect_cli.py`
Expected: FAIL (`unknown client 'zed'`).

- [ ] **Step 3: Implement, then write the documentation**

- `docs/reference/cli.md`: a `## \`vibey acp\`` section after `vibey mcp` (what it is, `--no-bootstrap`, what bootstrap does, exit behaviour, stdout rule), and `vibey connect` names Zed.
- `docs/reference/configuration.md`: `## \`[acp]\` { #acp }` with the table from this plan and a TOML example; the `[supervisor]` section notes the `hub` unit and `restart` added by ACP.
- `docs/guides/acp.md`: connect Zed (by `vibey connect --yes` or by hand), first contact on a fresh machine (what is installed and loaded, how to unload), modes, gates and why spend gates go to the host, cancel, sessions, troubleshooting (`launchctl print gui/$UID/dev.vibey.hub`, `systemctl --user status dev.vibey.hub`, logs under `[supervisor] log_dir`). Add it to `properdocs.yml` nav under guides.
- The `vibey-chat-driver` skill: a section "Driving vibey over ACP (Zed and other ACP clients)" with the same security boundary. Edit `.claude/skills/vibey-chat-driver/SKILL.md`, copy to `.agents/skills/vibey-chat-driver/SKILL.md` and `src/vibey_tools/skills/plugins/vibey/skills/vibey-chat-driver/SKILL.md`, mirror into `.cursor/rules/vibey-chat-driver.mdc` and `.agent/rules/vibey-chat-driver.md` (keep their front matter and mirror note), then regenerate slices with `python3 src/vibey_tools/skills/tools/slice_markdown.py --all-root src/vibey_tools/skills/plugins --all-output docs/microslices/skills --level 2` and review the diff.
- `changelog.d/acp-agent.feature.md`: one paragraph: `vibey acp`, Zed registration, self-installing user-level services, ADR-0101.

- [ ] **Step 4: Run tests and the documentation checks**

Run: `uv run pytest -q tests/domain/test_host_clients.py tests/cli/test_connect_cli.py tests/meta && uv run vibey-gh corpus-index --check && uv run python -m pip install --quiet -r docs/requirements.txt && uv run properdocs build --strict --site-dir "$TMPDIR/docs-site"`
Expected: PASS; the strict build (the `docs` CI job's own command) reports no warnings.

- [ ] **Step 5: Commit**

```bash
git add src/vibey/domain/host_clients.py src/vibey/infrastructure/mcp/host_installer.py src/vibey/cli/connect.py tests docs .claude/skills/vibey-chat-driver .agents/skills/vibey-chat-driver .cursor/rules/vibey-chat-driver.mdc .agent/rules/vibey-chat-driver.md src/vibey_tools/skills/plugins/vibey/skills/vibey-chat-driver changelog.d/acp-agent.feature.md properdocs.yml
git commit -m "feat(connect): register vibey acp as a Zed agent server; document ACP"
```

---

### Task 10: Conformance with the official SDK client, in CI, and the manual end to end

**Files:**
- Create: `tests/system/test_acp_conformance.py`, `tests/system/acp_stub_hub.py`
- Test: the file above

**Interfaces:**
- Consumes: everything above; the SDK's client API (re-read in step 1).
- Produces: a test that launches `vibey acp` as a subprocess with `cwd` set to a temporary directory holding a `vibey.toml` that sets `[hub] state_dir` to that directory and `[acp] auto_services = false`, `auto_connect = false`, `install_postgres = "never"`, and a stub hub (stdlib `http.server` in a thread, class `StubHub` with an interface beside it under `tests/`) that serves `/health/live`, `/api/v1/chat/messages`, `/api/v1/gates`, `/api/v1/gates/{id}/answer`, `/api/v1/projects`, `/api/v1/projects/{id}/ledger/after` and the four `/api/v1/acp/sessions` routes, writing a `serving.json` and `agent.token` the way `LocalTokenStore` reads them.

- [ ] **Step 1: Confirm the SDK surface from the installed wheel**

Run: `uv run python -c "import acp, inspect; print(acp.__all__ if hasattr(acp, '__all__') else dir(acp)); from acp.core import ClientSideConnection as C; print([m for m in dir(C) if not m.startswith('_')])"`
Expected: names including `connect_to_agent`, `Client`, `PROTOCOL_VERSION`, and connection methods `initialize`, `new_session`, `prompt`, `cancel`, `load_session`, `list_sessions`, `close_session`, `resume_session` (or their 1.0.0 spellings; use what is printed).

- [ ] **Step 2: Write the conformance test**

```python
# tests/system/test_acp_conformance.py
async def test_sdk_client_drives_initialize_new_prompt_permission_cancel_load() -> None:
    init = await conn.initialize(protocol_version=PROTOCOL_VERSION, client_capabilities=ClientCapabilities(), client_info=...)
    assert init.protocol_version == 1 and init.agent_capabilities.load_session
    session = await conn.new_session(cwd=str(workdir), mcp_servers=[])
    reply = await conn.prompt(session_id=session.session_id, prompt=[TextContentBlock(type="text", text="/gates")])
    assert reply.stop_reason == "end_turn"
    assert {"tool_call", "tool_call_update", "agent_message_chunk", "available_commands_update"} <= client.update_kinds
    # stub hub returns one choice gate and one budget_exhausted gate in the turn:
    assert len(client.permission_requests) == 1                     # the spend gate is not offered
    assert stub.answers == [(CHOICE_GATE, {"choice": "yes"})]        # the client selected allow_once
    slow = asyncio.create_task(conn.prompt(session_id=..., prompt=[... "/status" ...]))  # stub delays chat
    await conn.cancel(session_id=session.session_id)
    assert (await slow).stop_reason == "cancelled"
    await conn.load_session(session_id=session.session_id, cwd=str(workdir), mcp_servers=[])
    assert client.replayed_user_texts[:1] == ["/gates"]
async def test_every_stdout_line_was_valid_acp() -> None:
    # the SDK parsed every line without a validation error; stderr captured separately
```

- [ ] **Step 3: Run it**

Run: `uv run pytest -q tests/system/test_acp_conformance.py -p no:cacheprovider`
Expected: PASS on macOS and Linux. It runs in the `gates` job's single pytest run with no workflow change, because the root suite collects `tests/system/`. Confirm with `uv run pytest --collect-only -q tests/system/test_acp_conformance.py` and `tests/meta/test_every_test_file_is_collected.py`.

- [ ] **Step 4: Full gates from `CLAUDE.md`**

Run, in order: `uv lock --check`; `uv run vibey-gh corpus-index --check`; `uv run ruff check .`; `uv run ruff format --check .`; `uv run mypy --strict src/vibey`; `uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=`; the four `coverage report --include=... --fail-under=100`; `uv run lint-imports`; `uv run bandit -q -r src/vibey`; `uv run pip-audit --skip-editable`.
Expected: every command exits 0.

- [ ] **Step 5: Commit**

```bash
git add tests/system
git commit -m "test(acp): drive vibey acp end to end with the official ACP SDK client"
```

- [ ] **Step 6: Manual end to end (recorded in the PR body, not automated)**

In a clean user account or a fresh VM with no vibey state: launch `vibey acp` from Zed (after `vibey connect --yes`, or by hand); confirm the doctor and connect tool calls, `launchctl print gui/$UID/dev.vibey.hub` and `dev.vibey.worker` (or `systemctl --user status dev.vibey.hub dev.vibey.worker`) show running; kill the hub and see it return and one notice in Zed; start a project and watch the phase plan; answer a non-spend gate through the permission prompt; see a spend gate refused with the host message; cancel mid-turn; reload the session. Record each observation with its time and the command output, per sub-doctrine 10.f.

---

## Self-review against the spec

- Target behaviour table: `initialize` (Task 3), `session/new` with cwd binding and bootstrap (Tasks 3, 5, 7), `session/prompt` via the chat planner with tool-call streaming (Task 3), live project plan and messages (Task 5), gates as permissions and spend refusal (Task 4), `available_commands_update` (Task 5), `session/set_mode` (Task 5), `session/cancel` (Tasks 2, 3, 4), `session/load|list|close|resume` (Task 6), `fs/*` and `terminal/*`: deliberately not used by any task; vibey reads client `fs` and `terminal` capabilities in `initialize` and stores them, and no core path needs them (the spec allows this: "never needed for core function"). A follow-up may add "show me the diff" answers.
- Bootstrap steps 1, 2, 4 (Task 7), 3 and 5 (Task 8). `[acp]` keys `auto_bootstrap`, `auto_connect`, `auto_services`, `probe_seconds`, `modes` all present.
- Code layout: as specified, with the two placements argued in "Facts verified" (repository in `infrastructure/db`, live stream by polling).
- Task breakdown: the ten approved tasks map one to one.
- Verification: the full gates (Task 10 step 4), the SDK conformance test (Task 10), the MCP tests unchanged (Task 1), the manual end to end (Task 10 step 6).
