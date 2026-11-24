# SP-LOOPS Phase 5: the local runner (`gptossloop`, `qwenloop`) applies the snapshot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A BUILD run that falls to `gptossloop` or `qwenloop` is given the person's locked capability snapshot, the same document `claudeloop` takes, and can use all of it inside a 32k-token context. It reaches the snapshot's MCP servers over stdio or streamable HTTP, each through one persistent session per run, with a tool's schema fetched only when asked for. It lists the snapshot's skills by name and description in its system prompt and reads their bodies, and the plugins' commands, on demand. It reads the repository's `CLAUDE.md` and `AGENTS.md` as instruction text, as claudeloop does. `PluginSystem.VIBEY_BUNDLE` names this kind of plugin support, `full_access_gaps()` counts it, ADR-0092 is amended to say so, and the sovereign default's full-access gaps become none.

**Architecture:** The JSON-RPC 2.0 codec, error vocabulary and bidirectional peer move from `vibey` into `vibey_runners.common.jsonrpc` (stdlib only), with no copy left behind. vibey's MCP server and ACP agent import them from there. A stdlib-only MCP client is built over that peer in `vibey_runners.common.mcp`: a session, a per-run pool of sessions, a stdio transport that starts a `local` server through the Phase 4 scrubbed launcher, and an HTTP transport for a `remote` one. The skills, plugin commands, standing listing and instruction files a loop reads are also built in `vibey_runners.common.capabilities`, so they can be reused by any loop. qwenloop takes `run --capabilities PATH` and reads the document with the common strict reader. It then wires the pool and the skill shelf into its tool set and puts the listing into its system prompt. On the vibey side, `capabilities_flag` is set on both local descriptors, so the Phase 4 BUILD path prepares, records and removes their snapshot unchanged.

**Tech Stack:** Python 3.12+; stdlib `asyncio`, `json`, `urllib.request`, `os`, `signal`; Typer (qwenloop CLI); pytest, pytest-asyncio and Hypothesis; import-linter; the MCP protocol versions `2024-11-05` to `2025-11-25` (streamable HTTP from `2025-03-26`).

**Spec:** `docs/superpowers/specs/2026-11-22-uniform-loop-capabilities-design.md` (Goal 3, Decisions 3, 8, 9 and 10). Parent plan: `docs/superpowers/plans/2026-11-22-sp-loops-uniform-loop-capabilities.md` ("Phases 3 to 8", Phase 5). Previous phase: `docs/superpowers/plans/2026-11-24-sp-loops-phase4-claudeloop.md`, whose rulings R1 to R14 stand. Records: ADR-0092 (amended by Task 10) and ADR-0103 (a Phase 5 section, Task 10).

## Rulings

Where the spec or the parent leaves a choice open, this plan decides it. Each ruling is given as the decision, the reason, and the cost if it is wrong.

- **R1 (the peer's home): the codec, the error vocabulary, the peer and their two interfaces move to `vibey_runners.common.jsonrpc`.** `src/vibey/infrastructure/jsonrpc/` and `src/vibey/domain/jsonrpc_errors.py` are deleted, and every importer is repointed (Task 1 lists them). There is no re-export shim. Why: all four modules are stdlib only already, apart from the domain error module they import. A second import path for one class would be the duplication the brief forbids. `vibey`'s application layer may import a dependency-free family package (`.importlinter`, the `dto` precedent). Cost if wrong: a larger diff now; a shim can be added later without moving anything.
- **R2 (the MCP client's home): the MCP client lives in `vibey_runners.common.mcp`, and only qwenloop wires it in this phase.** The protocol versions vibey's MCP server answers (`SUPPORTED_PROTOCOLS`, `LATEST_PROTOCOL`) move there too, and `stdio_server.py` imports them under the same names. Why: the parent says "moved into common", a later codexloop (Phase 8) may need a client, and one list of versions serves both ends. Cost if wrong: common carries code that only one runner uses until Phase 8.
- **R3 (transport to the runner): `gptossloop run --capabilities PATH` and `qwenloop run --capabilities PATH` read the same document through `SnapshotDocumentStore.read`.** A refused document is exit 78, before any model call; the existing `engine_misconfigured` gate then parks the job, as it does for claudeloop. Both descriptors set `capabilities_flag="--capabilities"`. Only `build.implement` is given the snapshot (Phase 4 R2 is unchanged). Why: one document, one reader, one failure path. Cost if wrong: none beyond Phase 4's.
- **R4 (strict servers): with a snapshot, the local runner's MCP servers are exactly the snapshot's.** It reads neither `~/.claude.json` nor `QWENLOOP_MCP_CONFIG`, the counterpart of claudeloop's `strict_mcp_config` (Phase 4 R5). Without a snapshot, today's discovery stays as it is. In neither mode is the worktree's `.mcp.json` read. Cost if wrong: a person who expects their Claude servers in a vibey run must add them to `[loops] mcp_servers`; `vibey loops mcp add` does that.
- **R5 (session lifecycle): a session starts lazily, on the first `mcp_list(server)` or `mcp_call` for that server.** There is one session per server per run, and it is reused for every later call. It is closed when the run ends, from the `finally` of qwenloop's `_run_plan`, on success, failure, wind-down, stop and SIGTERM alike.
  - A stdio server leads a process group of its own. Closing a stdio session closes its stdin, waits `[mcp] close_grace_seconds`, then `killpg(SIGKILL)` reaps the group.
  - An HTTP session is closed by a best-effort `DELETE` that carries its `Mcp-Session-Id`.
  - qwenloop installs a SIGTERM handler that cancels the run task, so the `finally` runs when vibey stops a session.
  - A runner that is SIGKILLed leaves each stdio server with a closed stdin, the MCP spec's signal to exit.

  Why: a server nobody calls costs nothing, and a broken one cannot stop a run from starting. Cost if wrong: a server that ignores EOF on stdin outlives a SIGKILLed runner. The operator probe checks for that.
- **R6 (failure): no MCP failure ends a run, raises out of the tool dispatcher, parks a job or waits for a person.**
  - Every failure reaches the model as `{"error": ...}`: a server that will not start, the launcher exiting 2, 78 or 127, a closed stream, a timeout, an HTTP status error, a redirect, an oversize reply, or a JSON-RPC error answer.
  - Every request is bounded by `[mcp] request_timeout_seconds` (default `60`).
  - A session that died is restarted at most `[mcp] restarts` times per run (default `1`). After that the server answers `MCP server {name!r} is unavailable for the rest of this run: {first reason}` without being started again.
  - A JSON-RPC error answer leaves the session alive.

  Why: the queue never blocks on a human (CLAUDE.md non-negotiables), and a tool error is something the model can work around. Cost if wrong: a server that would have recovered on a third start stays down for that run.
- **R7 (schemas on demand): `mcp_list` and `mcp_call` stay the only two MCP tools, and `mcp_list` gains `tool` and `page`.**
  - With no argument, `mcp_list` lists the servers: name and trust level.
  - With `server`, it lists that server's tools by name and a one-line description, paged.
  - With `server` and `tool`, it returns that tool's input schema whole. If the schema is larger than the answer budget, it is refused with both sizes named.
  - A schema is never cut: a cut schema is a wrong schema.

  `mcp_call` output larger than the answer budget is cut with a named line that gives both lengths. The silent `[: max_read_chars]` cuts on `mcp_list` and `mcp_call` (qwenloop `infrastructure/tools.py` lines 286 and 298) go (ADR-0075). Why: a 32k model was seen misusing a long tool list (ADR-0092), and schemas are the bulk of one. Cost if wrong: a tool with a very large schema has to be called from its description alone. The refusal says so.
- **R8 (the token budget, two person-only `[loops]` keys):**
  - `capability_prompt_tokens` (int, default `3072`, from `512` to `4096`): the most tokens a loop that lists its own capabilities may spend in its standing system prompt on the snapshot. That is the skill and MCP listing first, then the instruction files.
  - `capability_answer_tokens` (int, default `3000`, from `256` to `8192`): the most any one on-demand capability answer may hold. That covers a page of `skills_list` or `mcp_list`, a page of `skill_read`, one schema, and one `mcp_call` result.

  Both enter `CapabilitySnapshot.digest` and the document, which becomes version 2. Tokens are estimated as characters ÷ 4, rounded up (`TokenEstimate.CHARS_PER_TOKEN`). That is the rule qwenloop's runner already uses (`application/runner.py` `_CHARS_PER_TOKEN`). claudeloop ignores both keys: Claude Code lists skills itself.

  The 32k acceptance is `test_a_full_snapshot_leaves_the_conversation_its_room` (Task 8). With `capability_prompt_tokens` at its ceiling of 4096 and a snapshot at the bundle's caps, the estimated system prompt plus every tool schema must be at most `32_768 - DEFAULT_CONTEXT_RENEWAL_TOKENS` (24,000), which is 8,768. If the measured ceiling does not fit, the ceiling is lowered to the largest multiple of 256 that does, and the number is written in the commit body. Cost if wrong: every digest changes once more; digests are per run.
- **R9 (the listing degrades, and says so):** the listing tries three forms in turn and uses the first that fits the standing budget:
  - the full form: `plugin:skill - description` for each skill, the command names, and the MCP server names with their trust;
  - names only;
  - one line: `{n} skills and {m} commands from {p} plugins; call skills_list to see them.`

  Each fallback form says why it was used. Instruction files then take what remains. A file that does not fit is named with its size and the agent is told to read it; it is never cut (Phase 4 R8, ADR-0075). Cost if wrong: a large `CLAUDE.md` is read by a tool call, not preloaded.
- **R10 (what `VIBEY_BUNDLE` holds):** it holds three things from the locked snapshot:
  - the skills;
  - the plugin commands (`commands/*.md`, non-recursive), as text, through the same two skill tools under the qualified name `plugin:command` and kind `command`;
  - the MCP servers.

  No hooks and no agents. Why: Decision 8 names commands, and the parent's task list left them out. Only three commands exist in the family today (`src/vibey_tools/gh/plugins/*/commands/`). Cost if wrong: a third skill-tool kind later; no data shape changes.
- **R11 (skill text is instruction): skill and command bodies come back without fences or an `untrusted` marker.** They are text from the locked bundle (Decision 3). MCP output keeps its `untrusted` marker. Bodies are paged within the answer budget and never cut. Cost if wrong: none for trust; the bundle is the person's choice and its hash is pinned.
- **R12 (instruction files): the local runner applies the document's `instruction_files` and `instruction_max_bytes` as claudeloop does.** It uses `InstructionFileReader`, moved from claudeloop into common, within R9's standing budget. Why: the document carries the setting, and a loop that silently ignores part of its document is the kind of claim drift this program forbids. Cost if wrong: none for claudeloop. Its tests move with the class and still hold.
- **R13 (remote servers): the remote transport refuses anything outside these limits.**
  - https only, as the bundle already requires.
  - No redirect is followed.
  - No cookie jar, and no credential or environment variable is sent (MCP OAuth is a non-goal).
  - A reply over `limit_bytes` is refused.
  - Each remote server may take at most `[mcp] remote_calls_per_session` `tools/call` requests per run (default `64`). This is a key in qwenloop's own config, not in `[loops]`, because claudeloop's engine has no hook to enforce one.

  Output is data whatever the trust level (Decision 9). Cost if wrong: a remote budget that differs between loops, until a second loop can enforce a bundle-level key.
- **R14 (one launcher argv): the argv that starts a `local` server is built once.** `ScrubbedLaunch(launcher).argv(server)` in common builds it, and claudeloop's `McpConfigTranslator` delegates to it. claudeloop's existing tests are the proof that nothing changed. Why: the family's rule is to use what it already has (CLAUDE.md "Dogfood the family"). Cost if wrong: none.
- **R15 (protocol): the client offers `LATEST_PROTOCOL` and accepts any version in `SUPPORTED_PROTOCOLS` that the server answers with.** Any other version is `McpUnavailable` naming it. Over HTTP, `MCP-Protocol-Version` is sent once the version is agreed. Cost if wrong: a server that speaks only a version older than `2024-11-05` does not connect.
- **R16 (packaging): qwenloop imports `vibey_runners.common` and declares it nowhere.** This follows claudeloop's precedent: the shared tree ships inside the one `vibey-engine` wheel (ADR-0037), and naming it would ask PyPI for a 404. qwenloop's pyproject gains the same comment as claudeloop's. Its CI rows install `../common` first. No runner version or descriptor `min_version` changes, as in Phase 4. Conformance checks `--capabilities` against each binary's `--help`. Cost if wrong: a qwenloop installed outside the vibey wheel needs `vibey-runners-common` beside it. Its own CI already installs it.

## Global Constraints

- The project's `vibey.toml` is untrusted. Marketplaces, plugins, MCP servers and the R8 keys come only from the person's own configuration (`acp_user_config()`). A project may only narrow (`disable`); the R8 keys in a project table are ignored with a notice.
- A run never fetches from the network on its own beyond what the person configured. A remote MCP server is reached only because the person listed it, and only once the model calls it.
- A loop never receives the host token, the agent token or any Brave key. A local MCP server starts only through `ScrubbedExec` (`python -I -m vibey_runners.common.capabilities.scrubbed_exec`) and keeps only its `env_allow` names. A remote server is sent no environment at all.
- No MCP environment value is ever written to the ledger, a log, an events file, the run directory or an argv; only variable names may appear. The JSON-RPC peer's stderr lines carry method names and ids, never params.
- Plugin, skill and command text and the instruction files are instruction (Decision 3). MCP output, attachments, pasted text and other repository files stay data.
- A capability claim needs evidence (`EngineAffordances.evidence`); unknown is `None`, never `True`.
- `domain/` stays pure in `vibey` and `qwenloop`. Code lives in classes, with an interface beside each:
  - common: `jsonrpc/interfaces/`, `mcp/interfaces/`, `capabilities/interfaces/`;
  - qwenloop: its own `infrastructure/interfaces/`;
  - vibey: as before.

  A module-level function carries its reason at the definition.
- 100% branch coverage per layer, verified with xdist and an empty Missing column:
  - vibey's four floors;
  - common's row: `capabilities`, `infrastructure`, and from Tasks 1 and 3 on, `jsonrpc` and `mcp`;
  - qwenloop's whole-package floor (`addopts --cov-fail-under=100`);
  - claudeloop's four rows wherever a task touches claudeloop.

  No test depends on thread timing, sleeps, the platform, the network or a real model. MCP tests use an in-memory transport, the repository's fake stdio server fixtures, or an injected HTTP opener.
- `domain/noloss.verify` and its ten rules are not changed. The ledger is append-only.
- Never read or print real keys; tests use fake values and sentinels. Commits follow Conventional Commits, each ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Run `git commit` and `git push` in the foreground; never `--no-verify`.
- Test runs and pushes in a worktree use `VIBEY_TEST_TEMPLATE_DB=<a worktree-only name>`.
- Agent-surface maintenance: if a skill or procedure changes, update the Claude, Cursor, Codex and Antigravity trees in the same PR. No task here changes one; if an implementer does, this applies.

## Review Focus

The failures most likely here that no happy path exercises, most likely first:

1. **A dead or hung MCP server ends the run, hangs a turn, or leaves a process behind.**
   - Task 3: `test_a_server_that_never_answers_times_out_and_the_session_is_dead`, `test_close_reaps_the_whole_process_group`.
   - Task 7: `test_every_mcp_failure_is_a_tool_error_never_an_exception`, `test_the_pool_is_closed_when_the_run_ends_however_it_ends`.
2. **A snapshot run still reads `~/.claude.json` or `QWENLOOP_MCP_CONFIG`.** Task 7: `test_a_snapshot_run_never_reads_the_operators_own_server_files`.
3. **An environment value reaches an argv, the events file, a log or a remote server.** Task 3: `test_a_local_server_starts_only_through_the_scrubbed_launcher`. Task 4: `test_a_remote_request_carries_no_environment_cookie_or_credential`. Task 8: `test_no_env_value_reaches_argv_events_or_logs`.
4. **Something is cut silently: a schema, the listing, a skill body or an MCP answer.** Task 5: `test_the_listing_degrades_to_names_then_a_count_and_says_so`, `test_a_body_is_paged_never_cut`. Task 7: `test_a_schema_over_the_answer_budget_is_refused_with_both_sizes`, `test_a_long_call_result_is_cut_with_a_named_line`.
5. **The fixed context outgrows 32k.** Task 8: `test_a_full_snapshot_leaves_the_conversation_its_room`.
6. **The JSON-RPC move changes a byte the MCP server or the ACP agent writes.** Task 1: `tests/infrastructure/mcp/test_mcp_golden.py` and every ACP test pass with only their import lines changed, plus `test_vibey_holds_no_second_jsonrpc_peer`.

## Order of work

The order is Task 1 (the move), then Task 2 (the budget keys and document version 2), then Tasks 3 to 5 (common: the MCP client, its HTTP transport, and the skill shelf and listing), then Tasks 6 to 8 (qwenloop: skill tools, MCP over the pool, then `--capabilities` with the system prompt and the 32k acceptance), then Task 9 (vibey's descriptors and BUILD), then Task 10 (the ADRs and docs). The tools land before the system prompt advertises them, so no tool is named in a prompt before it can be called. Each task is its own commit. The phase is one PR through the merge train.

---

### Task 1: The JSON-RPC codec, errors and peer move into common

**Files:**
- Create: under `src/vibey_runners/common/src/vibey_runners/common/jsonrpc/`:
  - `__init__.py` (empty, so importing `errors` pulls in no `asyncio`)
  - `codec.py` (`JsonRpcCodec`, `CODEC`)
  - `errors.py` (`PARSE_ERROR`, `INVALID_REQUEST`, `METHOD_NOT_FOUND`, `INVALID_PARAMS`, `INTERNAL_ERROR`, `RpcError`, `PeerClosed`, `PeerCancelled`)
  - `peer.py` (`JsonRpcPeer`)
  - `interfaces/__init__.py`, `interfaces/codec_interface.py`, `interfaces/peer_interface.py`

  The bodies move byte for byte; only the import lines change.
- Delete: `src/vibey/infrastructure/jsonrpc/` (whole package) and `src/vibey/domain/jsonrpc_errors.py`.
- Modify (imports only):
  - `src/vibey/cli/acp.py`
  - `src/vibey/application/acp/acp_agent.py`
  - `src/vibey/infrastructure/mcp/stdio_server.py`
  - `src/vibey/infrastructure/acp/peer_client_channel.py`
  - `src/vibey/infrastructure/acp/interfaces/peer_client_channel_interface.py`
  - `tests/application/acp/test_acp_agent.py`, `test_acp_load_resume.py`, `test_acp_gates.py`, `test_acp_prompt_turn.py`, `test_acp_modes_and_commands.py`
  - `tests/infrastructure/acp/test_peer_client_channel.py`
- Move: `tests/infrastructure/jsonrpc/test_codec.py` and `test_peer.py` go to `src/vibey_runners/common/tests/jsonrpc/`. Delete `tests/infrastructure/jsonrpc/`.
- Modify: `.importlinter`. Drop `vibey.infrastructure.jsonrpc.interfaces` from `infrastructure-interfaces-declare-only`; a contract naming a missing module fails `lint-imports`.
- Modify: `src/vibey_runners/common/pyproject.toml`. Add a contract "JSON-RPC interfaces declare seams, never consume them": source `vibey_runners.common.jsonrpc.interfaces`; forbidden `vibey_runners.common.jsonrpc.codec` and `vibey_runners.common.jsonrpc.peer`.
- Modify: `.github/ci-matrices.toml`. The three `vibey-runners-common` rows' `test` gains `--cov=vibey_runners.common.jsonrpc`. Regenerate the `tools_matrix` literal in `.github/workflows/ci.yml` and `tests/meta/ci_matrix_snapshot.json` from `uv run vibey-gh ci-matrix --job tools --tier full`, as `tests/meta/test_ci_tiers_keep_every_row.py` requires.
- Modify: `src/vibey_runners/common/README.md` (what `jsonrpc/` holds and why it is shared)
- Create: `tests/meta/test_one_jsonrpc_peer.py`

**Interfaces:**
- Unchanged: `JsonRpcPeer(reader, write_line, *, on_request, on_notification, codec, id_prefix="vibey", max_message_bytes=16_777_216, eof_grace_seconds=5.0)` with `run`, `request`, `notify` and `cancel_outbound`; `JsonRpcCodecInterface` with all nine methods; `CODEC`. The stderr prefix stays `vibey jsonrpc: `.

- [ ] **Step 1: Write the failing test** `test_vibey_holds_no_second_jsonrpc_peer`. It asserts three things: `src/vibey/infrastructure/jsonrpc` does not exist; no file under `src/vibey` defines `class JsonRpcPeer`, `class JsonRpcCodec` or `class RpcError`; and `vibey_runners.common.jsonrpc.peer.JsonRpcPeer` imports.
- [ ] **Step 2: Run** `uv run pytest tests/meta/test_one_jsonrpc_peer.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement.** Use `git mv` for the moved files so history follows them. Repoint each importer. A test that referred to the old error module's name keeps its assertions word for word.
- [ ] **Step 4: Run** the following. Expected: PASS.
  - `(cd src/vibey_runners/common && python -m pytest -q -p no:cacheprovider --cov=vibey_runners.common.jsonrpc --cov=vibey_runners.common.capabilities --cov=vibey_runners.common.infrastructure --cov-branch --cov-fail-under=100)`
  - `uv run pytest tests/infrastructure/mcp tests/application/acp tests/infrastructure/acp tests/cli/test_acp_cli.py tests/meta -q`. The MCP golden transcript is byte-identical; that is the server's proof.
  - The four vibey layer floors.
  - `mypy --strict` for `src/vibey` and `src/vibey_runners/common`, `lint-imports` (root and common), and `bandit`.
- [ ] **Step 5: Commit** `refactor(jsonrpc): move the JSON-RPC codec, errors and peer into vibey-runners-common`.

### Task 2: Two token budgets in `[loops]`, and capability document version 2

**Files:**
- Modify: in `src/vibey_runners/common/src/vibey_runners/common/capabilities/`:
  - `bundle.py`: `_KEYS`, `BundleSpec` and its constants.
  - `interfaces/bundle_interface.py`: two read-only properties.
  - `resolver.py`: `_digest` adds both keys.
  - `snapshot_document.py`: `DOCUMENT_VERSION = 2`; `_KEYS`, `_SETTINGS`, the fields, `of` and `to_json`.
  - `interfaces/snapshot_document_interface.py`.
- Create: `capabilities/token_estimate.py` (`TokenEstimate`) and `capabilities/interfaces/token_estimate_interface.py`
- Modify: `src/vibey_runners/claude/tests/capability_documents.py` (the hand-built document is version 2 with both keys)
- Test: `src/vibey_runners/common/tests/capabilities/test_bundle.py`, `test_resolver.py`, `test_snapshot_document.py`, `test_token_estimate.py`; `tests/application/test_loops_bundle_settings.py`; every vibey or claudeloop test that pins a digest value.

**Interfaces:**
- `BundleSpec` gains `capability_prompt_tokens: int = DEFAULT_CAPABILITY_PROMPT_TOKENS` and `capability_answer_tokens: int = DEFAULT_CAPABILITY_ANSWER_TOKENS`, after `snapshot_max_age_days`, so existing constructions keep working. The constants:
  - `DEFAULT_CAPABILITY_PROMPT_TOKENS: Final = 3072`, `CAPABILITY_PROMPT_TOKENS_FLOOR: Final = 512`, `CAPABILITY_PROMPT_TOKENS_CEILING: Final = 4096`;
  - `DEFAULT_CAPABILITY_ANSWER_TOKENS: Final = 3000`, `CAPABILITY_ANSWER_TOKENS_FLOOR: Final = 256`, `CAPABILITY_ANSWER_TOKENS_CEILING: Final = 8192`.

  Each key is read by `_whole` with a `BundleError` naming `loops.capability_prompt_tokens` or `loops.capability_answer_tokens`.
- `SnapshotDocument` gains the same two fields. A version-1 document is refused by the existing version check. claudeloop reads and ignores the two keys.
- `TokenEstimate`, a stateless class. `CHARS_PER_TOKEN: Final = 4`, with the reason written beside it: it is the local runner's own estimate, and no tokenizer is available stdlib-only. Methods:
  - `tokens(text: str) -> int`: `ceil(len(text) / 4)`, so `""` costs 0;
  - `chars(tokens: int) -> int`: `tokens * 4`.

  Module instance: `TOKEN_ESTIMATE: TokenEstimateInterface`.

- [ ] **Step 1: Write the failing tests.**
  - `test_the_default_bundle_gives_3072_prompt_tokens_and_3000_answer_tokens`
  - `test_capability_prompt_tokens_outside_512_to_4096_is_refused` (`BundleError("loops.capability_prompt_tokens", ...)`; also a bool and a float)
  - `test_capability_answer_tokens_outside_256_to_8192_is_refused`
  - `test_the_digest_changes_with_either_token_budget`
  - `test_a_document_round_trips_both_budgets`
  - `test_a_version_1_document_is_refused`
  - `test_a_project_cannot_widen_a_token_budget`: a project's `[loops] capability_prompt_tokens = 4096` is ignored and named in a notice.
  - `test_an_estimate_rounds_up_and_empty_text_costs_nothing` (`tokens("abcde") == 2`)
- [ ] **Step 2: Run** `(cd src/vibey_runners/common && python -m pytest -q tests/capabilities)` and `uv run pytest -q tests/application/test_loops_bundle_settings.py`. Expected: FAIL.
- [ ] **Step 3: Implement.** Update every test that pins a digest; the commit body names each one. The new keys change every digest once, deliberately.
- [ ] **Step 4: Run** the following. Expected: PASS.
  - common's row at 100%, `mypy --strict` and `lint-imports`;
  - claudeloop's infrastructure and cli rows (they read documents);
  - the vibey application and cli floors.
- [ ] **Step 5: Commit** `feat(loops): capability prompt and answer token budgets, and capability document version 2`.

### Task 3: An MCP client in common: sessions over the peer, a per-run pool, and the stdio transport

**Files:**
- Create: under `src/vibey_runners/common/src/vibey_runners/common/mcp/`:
  - `__init__.py`
  - `protocol.py`: `SUPPORTED_PROTOCOLS`, `LATEST_PROTOCOL` (constants moved from `stdio_server.py`)
  - `mcp_errors.py`: `McpUnavailable(RuntimeError)`, `McpToolError(RuntimeError)`
  - records: `mcp_tool.py` (`McpTool`), `mcp_call_result.py` (`McpCallResult`)
  - `stdio_transport.py` (`StdioTransport`), `mcp_session.py` (`McpSession`), `mcp_session_pool.py` (`McpSessionPool`)
  - `interfaces/mcp_transport_interface.py`, `interfaces/mcp_session_interface.py`, `interfaces/mcp_session_pool_interface.py`
- Create: `capabilities/scrubbed_launch.py` (`ScrubbedLaunch`) and `capabilities/interfaces/scrubbed_launch_interface.py`
- Modify: `src/vibey/infrastructure/mcp/stdio_server.py`. It imports `SUPPORTED_PROTOCOLS as SUPPORTED_PROTOCOLS` and `LATEST_PROTOCOL as LATEST_PROTOCOL` from `vibey_runners.common.mcp.protocol`, so `tests/infrastructure/mcp/test_mcp_server.py` is unchanged.
- Modify: `src/vibey_runners/claude/src/claudeloop/domain/mcp_config.py`. The `local` branch builds its `command`/`args` from `ScrubbedLaunch(self._launcher).argv(server)` (R14); its output is unchanged.
- Modify: `src/vibey_runners/common/pyproject.toml`. Add an interfaces contract for `vibey_runners.common.mcp.interfaces`, forbidding `stdio_transport`, `mcp_session` and `mcp_session_pool`, and add `capabilities.scrubbed_launch` to the capability contract. Modify `.github/ci-matrices.toml` (add `--cov=vibey_runners.common.mcp` to common's rows) and regenerate as in Task 1.
- Create: `src/vibey_runners/common/tests/mcp/fake_stdio_server.py`, a fixture whose behaviour is chosen by `argv[1]`: `ok`, `hang`, `exit`, `error`, `paged`, `old-protocol`, `unknown-protocol`, `spawns-child`, and `echo-env` (prints the names of its environment, never the values).
- Test: `src/vibey_runners/common/tests/mcp/test_mcp_session.py`, `test_mcp_session_pool.py`, `test_stdio_transport.py`; `src/vibey_runners/common/tests/capabilities/test_scrubbed_launch.py`; claudeloop's `tests/domain/test_mcp_config.py` (unchanged, must pass)

**Interfaces:**
- `McpTransportInterface`:
  - `async open() -> tuple[asyncio.StreamReader, Callable[[str], Awaitable[None]]]`
  - `async close(grace_seconds: float) -> None`
  - `describe() -> str`: the server name and kind, and for HTTP the host only; never an argv tail, a query string or an environment value.
- `StdioTransport(name: str, argv: Sequence[str], env: Mapping[str, str], cwd: Path, *, limit_bytes: int = 16_777_216, spawn: Callable[..., Awaitable[asyncio.subprocess.Process]] = asyncio.create_subprocess_exec, killpg: Callable[[int, int], None] = os.killpg)`
  - It starts the server with `start_new_session=True` and `stderr=DEVNULL`; the reader limit is `limit_bytes`.
  - `close` closes stdin, waits `grace_seconds`, then calls `killpg(pid, SIGKILL)`, treating `ProcessLookupError` and `PermissionError` as already gone, and reaps the process.
- `McpSession(transport: McpTransportInterface, *, client_name: str, client_version: str, timeout_seconds: float, max_tools: int = 1024)`:
  - `async start() -> None`: `initialize` offering `LATEST_PROTOCOL`, a version check against `SUPPORTED_PROTOCOLS` (R15), then `notifications/initialized`.
  - `async list_tools() -> tuple[McpTool, ...]`: follows `nextCursor` up to `max_tools`, then caches the result. `notifications/tools/list_changed` drops the cache.
  - `async call(tool: str, arguments: Mapping[str, object]) -> McpCallResult`: the text parts joined with `"\n"`, plus `isError`.
  - `async close(grace_seconds: float) -> None`, and the property `alive: bool`.
  - A server request `ping` answers `{}`; any other server request answers `METHOD_NOT_FOUND`.
  - `McpUnavailable` is raised for a start failure, `PeerClosed`, a timeout, or an unknown protocol version. `McpToolError` is raised for an `RpcError` answer.
- `McpSessionPool(sessions: Mapping[str, Callable[[], McpSessionInterface]], *, trust: Mapping[str, McpTrust], restarts: int, remote_calls: int, close_grace_seconds: float)`:
  - `names -> tuple[str, ...]` and `trust_of(name) -> McpTrust`;
  - `async tools(name) -> tuple[McpTool, ...]`;
  - `async call(name, tool, arguments) -> McpCallResult`;
  - `remote_calls_left(name) -> int | None` (`None` for a local server);
  - `async aclose() -> None`: closes every live session, never raises, and is idempotent.

  Lazy start and restart follow R5 and R6. An unknown server raises `McpUnavailable("unknown MCP server 'x'; configured: a, b")`.
- `McpTool(name: str, description: str, input_schema: Mapping[str, object])` and `McpCallResult(text: str, is_error: bool)` are records with no seam.
- `ScrubbedLaunch(launcher: Sequence[str])`, `argv(server: McpServerSpec) -> tuple[str, ...]`. It returns `(*launcher, *("--allow", n for n in env_allow), "--", *server.command)`, and raises `ValueError` for a server that is not `local` with a command.

- [ ] **Step 1: Write the failing tests.**
  - Session, over an in-memory transport (a `StreamReader` the test feeds):
    - `test_start_offers_the_latest_protocol_and_accepts_an_older_supported_one`
    - `test_an_unknown_protocol_version_is_unavailable_and_named`
    - `test_list_tools_follows_next_cursor_and_stops_at_max_tools`
    - `test_a_tools_list_changed_notification_drops_the_cache`
    - `test_a_server_ping_is_answered_and_other_server_requests_are_refused`
    - `test_a_jsonrpc_error_answer_is_a_tool_error_and_the_session_stays_alive`
    - `test_a_server_that_never_answers_times_out_and_the_session_is_dead`
  - Pool:
    - `test_a_session_starts_on_first_use_and_is_reused`
    - `test_a_dead_session_restarts_once_then_the_server_is_unavailable_for_the_run`
    - `test_the_remote_call_budget_is_per_server_and_local_servers_have_none`
    - `test_aclose_closes_every_live_session_and_never_raises`
    - `test_an_unknown_server_names_the_configured_ones`
  - Stdio, with the fixture via `sys.executable`:
    - `test_a_stdio_session_round_trips_tools_list_and_call`
    - `test_close_reaps_the_whole_process_group` (`spawns-child`, then neither pid is alive)
    - `test_a_server_that_exits_at_start_is_unavailable_with_its_exit_code`
    - `test_describe_holds_no_argv_tail_or_env_value`
  - Launch:
    - `test_a_local_server_starts_only_through_the_scrubbed_launcher`: with `echo-env` behind `ScrubbedLaunch((sys.executable, *LAUNCHER_ARGS))`, a sentinel in an `env_allow` name reaches the child by name. A secret-named variable in the parent's environment does not. The sentinel value is in no argv element.
    - `test_scrubbed_launch_refuses_a_remote_server`
- [ ] **Step 2: Run** `(cd src/vibey_runners/common && python -m pytest -q tests/mcp tests/capabilities/test_scrubbed_launch.py)`. Expected: FAIL.
- [ ] **Step 3: Implement.** The session runs the peer's `run()` as a task it owns and cancels on close. Every `request` passes `timeout=timeout_seconds`.
- [ ] **Step 4: Run** the following. Expected: PASS.
  - common's row with `--cov=vibey_runners.common.mcp` at 100%, `mypy --strict`, `lint-imports` and `bandit`;
  - claudeloop's domain row;
  - `uv run pytest tests/infrastructure/mcp -q`.
- [ ] **Step 5: Commit** `feat(mcp): a stdlib MCP client over the shared peer: persistent sessions, a per-run pool and the stdio transport`.

### Task 4: The streamable HTTP transport and the transport factory (common)

**Files:**
- Create: under `src/vibey_runners/common/src/vibey_runners/common/mcp/`:
  - `http_transport.py` (`HttpTransport`) and `http_opener.py` (`HttpOpener`, with the record `HttpReply`)
  - `mcp_transport_factory.py` (`McpTransportFactory`)
  - beside them, `interfaces/http_opener_interface.py` and `interfaces/mcp_transport_factory_interface.py`
- Test: `src/vibey_runners/common/tests/mcp/test_http_transport.py`, `test_mcp_transport_factory.py`

**Interfaces:**
- `HttpOpener(timeout_seconds: float)`:
  - `post(url: str, body: bytes, headers: Mapping[str, str]) -> HttpReply` and `delete(url: str, headers: Mapping[str, str]) -> int`.
  - It is built on `urllib.request.build_opener` with a redirect handler that refuses every redirect, and with no cookie processor.
  - `HttpReply(status: int, headers: Mapping[str, str], body: bytes)`. The body is read up to `limit_bytes + 1`, and a reply over the limit is refused.
- `HttpTransport(name: str, url: str, *, timeout_seconds: float, limit_bytes: int = 16_777_216, opener: HttpOpenerInterface | None = None)`.
  - `open` returns a fresh `StreamReader` and a `write_line` that POSTs the line through `asyncio.to_thread(opener.post, ...)` with these headers:
    - `Content-Type: application/json`
    - `Accept: application/json, text/event-stream`
    - `Mcp-Session-Id` once the server has given one
    - `MCP-Protocol-Version` once agreed
  - The reply is fed back to the reader:
    - `200` `application/json`: one line;
    - `200` `text/event-stream`: one line per event (its `data:` lines joined);
    - `202`: nothing;
    - `404` while a session id is held: `feed_eof()`, so the session is dead (R6);
    - any other status, or a refused redirect: `McpUnavailable` naming the status and the host, never the path or query.
  - `close` sends `DELETE` with the session id, ignores every error, and calls `feed_eof()`.
- `McpTransportFactory(launch: ScrubbedLaunchInterface, *, cwd: Path, environ: Mapping[str, str], timeout_seconds: float)` with `for_spec(server: McpServerSpec) -> McpTransportInterface`:
  - a `local` server gets `StdioTransport(name, launch.argv(server), environ, cwd)`; the launcher scrubs;
  - a `remote` server gets `HttpTransport(name, url, ...)`.

- [ ] **Step 1: Write the failing tests** with a recording fake opener; no socket is opened.
  - `test_initialize_keeps_the_session_id_and_sends_it_with_the_protocol_version_after`
  - `test_an_event_stream_reply_feeds_each_event_as_one_message`
  - `test_a_202_feeds_nothing`
  - `test_a_404_with_a_session_ends_the_session`
  - `test_a_redirect_is_refused_and_names_only_the_host`
  - `test_a_reply_over_the_limit_is_refused`
  - `test_a_remote_request_carries_no_environment_cookie_or_credential`: the headers are exactly the four named above, and a sentinel environment value appears nowhere in the request.
  - `test_close_deletes_the_session_and_ignores_a_failure`
  - `test_the_factory_gives_local_stdio_through_the_launcher_and_remote_http`
  - `test_the_real_opener_follows_no_redirect`: the `HttpOpener` handler chain, inspected without a socket.
- [ ] **Step 2: Run** `(cd src/vibey_runners/common && python -m pytest -q tests/mcp/test_http_transport.py tests/mcp/test_mcp_transport_factory.py)`. Expected: FAIL.
- [ ] **Step 3: Implement.** Add `# nosec` with its reason where bandit flags `urlopen`: the scheme was held to https by `BundleSpec._https`.
- [ ] **Step 4: Run** common's row at 100%, `mypy --strict`, `lint-imports` and `bandit`. Expected: PASS.
- [ ] **Step 5: Commit** `feat(mcp): a streamable HTTP transport for remote servers, with no redirects and no credentials`.

### Task 5: The skill shelf, plugin commands, the standing listing and instruction files (common)

**Files:**
- Create: under `src/vibey_runners/common/src/vibey_runners/common/capabilities/`:
  - `plugin_command_index.py` (`PluginCommandIndex`), with the record `command_entry.py` (`CommandEntry`)
  - `skill_shelf.py` (`SkillShelf`), with the records `shelf_entry.py` (`ShelfEntry`), `shelf_page.py` (`ShelfPage`) and `shelf_text.py` (`ShelfText`), and `skill_shelf_error.py` (`SkillShelfError(LookupError)`)
  - `capability_listing.py` (`CapabilityListing`), with the record `listing_text.py` (`ListingText`)
  - interfaces beside each class
- Move: `src/vibey_runners/claude/src/claudeloop/infrastructure/capabilities/instruction_files.py` to `capabilities/instruction_files.py`, and its interface from claudeloop's `infrastructure/interfaces/instruction_file_reader_interface.py` to `capabilities/interfaces/instruction_file_reader_interface.py`. Move its test to `src/vibey_runners/common/tests/capabilities/test_instruction_files.py`. claudeloop's `snapshot_applier.py` and bootstrap import the class from common.
- Test: `src/vibey_runners/common/tests/capabilities/test_plugin_command_index.py`, `test_skill_shelf.py`, `test_capability_listing.py`, `test_instruction_files.py`

**Interfaces:**
- `PluginCommandIndex(reader=None, frontmatter=None, guard=None, probe=None)` takes the same seams as `SkillIndex` and has `build(plugin_dirs: Sequence[Path]) -> tuple[tuple[CommandEntry, ...], tuple[tuple[Path, str], ...]]`.
  - It reads `commands/*.md`, non-recursively, at most `MAX_SKILLS_PER_PLUGIN` per plugin, and each file at most `SKILL_MAX_BYTES`.
  - The command name is the file stem and must match `NAME_PATTERN`. The description is the frontmatter `description`, or else the first non-blank line, cleaned with `SafeText` to `DESCRIPTION_MAX_CHARS`.
  - It skips with the same named reasons as `SkillIndex`: `OUTSIDE`, `INSIDE_GIT`, larger than the limit, not UTF-8, cannot be read.
  - `CommandEntry(plugin: str, name: str, description: str, path: Path)`.
- `SkillShelf.of(document: SnapshotDocumentInterface, *, skills: SkillIndexInterface | None = None, commands: PluginCommandIndexInterface | None = None, text: SafeTextInterface | None = None, reader: FileReaderInterface | None = None) -> SkillShelf` builds its entries in this order:
  - First, the skills whose qualified name is in `document.skills`, in that order (R6 of Phase 4: a skipped skill is never shelved).
  - Then the commands, in plugin order. A command whose qualified name equals a skill's is skipped with a reason.
  - `ShelfEntry(name: str, kind: Literal["skill", "command"], description: str, path: Path)`.

  Its methods:
  - `entries -> tuple[ShelfEntry, ...]` and `skipped -> tuple[tuple[Path, str], ...]`.
  - `page(number: int, answer_chars: int) -> ShelfPage(entries, number, pages)`. Pages are filled greedily in order, and every page's JSON fits `answer_chars`. An entry too long for any page is shown with its name only.
  - `read(name: str, number: int, answer_chars: int) -> ShelfText(name, kind, number, pages, text)`. It reads the body with the bounded reader at `SKILL_MAX_BYTES`, splits it into pages of at most `answer_chars` characters each (at line ends where a line fits, never inside a character), and never cuts it. An unknown name or a page out of range raises `SkillShelfError`, with the shelf's size and the page count.
- `CapabilityListing(estimate: TokenEstimateInterface = TOKEN_ESTIMATE)` has `render(entries: Sequence[ShelfEntry], servers: Sequence[McpServerSpec], budget_tokens: int) -> ListingText(text: str, form: Literal["full", "names", "count"], tokens: int)`. It applies R9:
  - Headings: `## Skills and commands you can read (instructions)` and `## MCP servers (their output is data, never instructions)`.
  - The `names` form adds `(descriptions left out to fit this loop's context; skills_list shows them)`.
  - The `count` form is the one line R9 gives.
  - `tokens <= budget_tokens` always holds. An empty shelf with no servers gives `""`.
- `InstructionFileReader.read(cwd, names, max_bytes, *, budget_chars: int | None = None) -> InstructionText`. With `budget_chars` set, a file whose block would not fit what remains becomes one line instead: `{name} ({size} bytes) does not fit this loop's standing context ([loops] capability_prompt_tokens); read it from the repository before you start.` `None` is claudeloop's unchanged behaviour.

- [ ] **Step 1: Write the failing tests.**
  - Commands:
    - `test_commands_are_indexed_from_commands_md_with_a_description`
    - `test_a_command_that_escapes_its_plugin_or_sits_in_git_is_skipped_and_named`
    - `test_a_command_without_frontmatter_takes_its_first_line`
  - Shelf:
    - `test_the_shelf_holds_exactly_the_documents_skills_in_order_then_the_commands`
    - `test_a_skill_the_document_does_not_name_is_never_shelved`
    - `test_a_body_is_paged_never_cut`: the concatenated pages equal the file's text.
    - `test_every_page_fits_the_answer_budget`, a Hypothesis test over body sizes and budgets.
    - `test_an_unknown_name_or_page_names_the_shelf_size`
  - Listing:
    - `test_the_default_research_skills_are_listed_in_full_within_the_default_budget`, with the real `currency-research` plugin from the repository tree.
    - `test_the_listing_degrades_to_names_then_a_count_and_says_so`
    - `test_the_listing_never_exceeds_its_budget`, a Hypothesis test over entries and budgets.
    - `test_server_names_and_trust_are_listed_with_their_output_marked_as_data`
  - Instruction files: the moved claudeloop tests pass unchanged, plus `test_a_file_that_does_not_fit_the_budget_is_named_never_cut`.
- [ ] **Step 2: Run** `(cd src/vibey_runners/common && python -m pytest -q tests/capabilities)`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** common's row at 100%, then claudeloop's infrastructure and cli rows at 100% (the import moved), then `mypy --strict` and `lint-imports` for both. Expected: PASS.
- [ ] **Step 5: Commit** `feat(loops): a skill shelf, plugin commands and a standing listing held to a token budget`.

### Task 6: The local runner reads skills and commands on demand (`skills_list`, `skill_read`)

**Files:**
- Modify: `src/vibey_runners/qwen/src/qwenloop/domain/model.py`. `CODING_TOOL_NAMES` gains `"skills_list"` and `"skill_read"` after `"mcp_call"`.
- Modify: `src/vibey_runners/qwen/src/qwenloop/infrastructure/inference.py`. `_CODING_TOOLS` gains the two schemas:
  - `skills_list`: `{page?: integer}`;
  - `skill_read`: `{name: string, page?: integer}`, required `name`.
  - Each description says the text is instructions from the person's chosen plugins.
- Modify: `src/vibey_runners/qwen/src/qwenloop/infrastructure/tools.py`:
  - `SandboxTools(..., shelf: SkillShelfInterface | None = None, answer_chars: int | None = None)`;
  - dispatch `if name in {"skills_list", "skill_read"}:`.
- Modify: `src/vibey_runners/qwen/pyproject.toml`. Add the R16 comment in `dependencies`. The import-linter contracts need no change: `include_external_packages = true` already lets qwenloop import `vibey_runners`.
- Modify: `.github/ci-matrices.toml`. Every qwenloop row's `install` becomes `pip install -e ../common && pip install -e \".[dev]\"` (lines 106, 290, 298 and 305 today). Regenerate as in Task 1.
- Test: `src/vibey_runners/qwen/tests/test_tools.py`, `tests/test_inference.py`, `tests/test_domain.py`

**Interfaces:**
- `skills_list` returns `{"entries": [{"name", "kind", "description"}], "page": n, "pages": m}`.
- `skill_read` returns `{"name", "kind", "page", "pages", "text"}` with no `untrusted` key (R11).
- Without a shelf, both return `{"error": _SKILLS_NOT_CONFIGURED}`: "no skills are set up for this session; this run was started without a capability snapshot."
- `answer_chars` is `min(capability_answer_tokens * 4, max_tool_result_chars - ANSWER_ENVELOPE_CHARS)`. `ANSWER_ENVELOPE_CHARS: Final = 256` is the JSON keys and numbers around a page, with its reason written beside it, so the runner's own result cut never touches a page.

- [ ] **Step 1: Write the failing tests.**
  - `test_skills_list_pages_the_shelf_within_the_answer_budget`
  - `test_skill_read_returns_a_page_without_an_untrusted_marker`
  - `test_a_skill_body_read_page_by_page_is_whole`
  - `test_an_unknown_skill_is_a_tool_error_not_an_exception`
  - `test_without_a_shelf_both_tools_say_no_snapshot`
  - `test_every_coding_tool_name_has_a_schema_and_a_dispatch`: the existing three-way check, now over 14 tools.
  - `test_a_page_never_reaches_the_result_cut`
- [ ] **Step 2: Run** `(cd src/vibey_runners/qwen && python -m pytest -q tests/test_tools.py tests/test_inference.py tests/test_domain.py)`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** qwenloop's row: `pip install -e ../common` first, then `python -m pytest -q` at the whole-package 100%, `mypy --strict src/qwenloop`, `lint-imports` and `bandit -q -r src/qwenloop`. Then run `uv run pytest tests/meta/test_ci_tiers_keep_every_row.py -q`. Expected: PASS.
- [ ] **Step 5: Commit** `feat(qwenloop): read the snapshot's skills and plugin commands on demand`.

### Task 7: The local runner's MCP over the pool: schemas on demand, a lifecycle, failures as tool errors

**Files:**
- Modify: `src/vibey_runners/qwen/src/qwenloop/infrastructure/mcp.py`. `McpGateway` becomes an adapter over `McpSessionPool`. `McpServer` and `McpError` go; their users take the common errors.
- Modify: `src/vibey_runners/qwen/src/qwenloop/infrastructure/interfaces/mcp_interface.py`. `McpGatewayInterface` gains `trust_of`, `async schema(server, tool)`, `remote_calls_left` and `async aclose()`.
- Modify: `src/vibey_runners/qwen/src/qwenloop/domain/config.py`. Add `McpLimits` and `QwenConfig.mcp`, and `QwenConfigParser` reads `[mcp]` the way it reads `[tools]` into `ToolLimits`.
- Modify: `src/vibey_runners/qwen/src/qwenloop/infrastructure/tools.py` (`_mcp_tool` follows R7) and `infrastructure/inference.py` (the `mcp_list` schema gains `tool` and `page`, and its description says schemas come one tool at a time)
- Modify: `src/vibey_runners/qwen/src/qwenloop/cli/app.py` (`_run_plan`):
  - build the gateway;
  - `try: ... finally: await gateway.aclose()`;
  - `loop.add_signal_handler(SIGTERM, run_task.cancel)`, removed in the `finally`.
- Modify: `src/vibey_runners/qwen/tests/fixtures/fake_mcp_server.py`. Answer string ids and the `paged` and `slow-schema` modes.
- Test: `src/vibey_runners/qwen/tests/test_mcp.py`, `tests/test_tools.py`, `tests/test_settings.py`, `tests/test_cli.py`

**Interfaces:**
- `McpLimits(request_timeout_seconds: float = 60.0, restarts: int = 1, close_grace_seconds: float = 2.0, remote_calls_per_session: int = 64, max_tools: int = 1024)` is a frozen record. Each value is validated by the parser with an error naming `mcp.<key>`, and each is overridable from the config file's `[mcp]` table (sub-doctrine 12.c).
- `McpGateway.from_document(document: SnapshotDocumentInterface, *, cwd: Path, environ: Mapping[str, str], limits: McpLimits, client: tuple[str, str]) -> McpGateway`: the snapshot's servers through `McpTransportFactory` (R4).
- `McpGateway.discover(cwd, *, home, environ, base_env, limits, client) -> McpGateway`: today's sources and parsing, unchanged. Each found server becomes `StdioTransport(name, (command, *args), {**base_env, **server_env}, cwd)`, and the non-stdio servers stay `unsupported`.
- `mcp_list` answers, following R7:
  - with no arguments: `{"servers": [{"name", "trust", "remote_calls_left"}], "unsupported": {...}}`;
  - with `server`: `{"tools": [{"name", "description"}], "page", "pages"}`, where a description is one `SafeText` line of at most 200 characters (`TOOL_DESCRIPTION_CHARS: Final = 200`);
  - with `server` and `tool`: `{"tool", "input_schema"}`, or `{"error": "the input schema of {tool} is about {n} tokens, more than the [loops] capability_answer_tokens of {m}; call it with the arguments its description implies"}`.
- `mcp_call`: `{"content", "untrusted"}`. Text over `answer_chars` is cut, followed by the line `...[cut: the tool returned {total} characters; this answer holds the first {kept}]`. An `is_error` result is `{"error": text}`. Every `McpUnavailable` or `McpToolError` becomes `{"error": str(exc)}`.

- [ ] **Step 1: Write the failing tests.**
  - `test_a_snapshot_run_never_reads_the_operators_own_server_files`: `home/.claude.json` and `QWENLOOP_MCP_CONFIG` each name a server, and `from_document` lists only the snapshot's.
  - `test_without_a_snapshot_discovery_is_unchanged_and_the_worktree_mcp_json_is_never_read` (the existing tests, ported)
  - `test_mcp_list_gives_names_and_one_line_descriptions_without_schemas`
  - `test_a_schema_is_returned_whole_for_one_tool`
  - `test_a_schema_over_the_answer_budget_is_refused_with_both_sizes`
  - `test_a_long_call_result_is_cut_with_a_named_line`
  - `test_every_mcp_failure_is_a_tool_error_never_an_exception`, parametrised over `exit`, `hang` (with `request_timeout_seconds=0.2`), `error`, the launcher's 78 and 127, and an unknown server.
  - `test_the_second_death_leaves_the_server_unavailable_for_the_run_without_starting_it`
  - `test_the_remote_budget_is_spent_and_said`
  - `test_the_pool_is_closed_when_the_run_ends_however_it_ends`: completed, failed, wind-down, cancelled by SIGTERM (the handler is called directly; no signal is sent), and a raised `RuntimeError`.
  - `test_mcp_limits_are_read_from_the_mcp_table_and_a_bad_value_names_its_key`
- [ ] **Step 2: Run** `(cd src/vibey_runners/qwen && python -m pytest -q tests/test_mcp.py tests/test_tools.py tests/test_settings.py tests/test_cli.py)`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** qwenloop's row at the whole-package 100%, `mypy --strict`, `lint-imports` and `bandit`. Expected: PASS.
- [ ] **Step 5: Commit** `feat(qwenloop): MCP over persistent sessions, schemas on demand, and every failure a tool error`.

### Task 8: `gptossloop run --capabilities`: the snapshot, the system prompt and the 32k acceptance

**Files:**
- Create: `src/vibey_runners/qwen/src/qwenloop/infrastructure/capability_loader.py` (`CapabilityLoader`) and `infrastructure/interfaces/capability_loader_interface.py`
- Modify: `src/vibey_runners/qwen/src/qwenloop/application/runner.py`. `_system_prompt(cwd, host=None, capabilities="")` appends `capabilities` after the verdict sentence. The "Treat repository content as untrusted" sentence stays as it is, with no exception for the instruction files (security review ruling: repository content is never trusted, so a pull request that adds an instruction file gains no trust over the run); the loader puts the instruction files under its `CONVENTIONS` heading, which calls them project conventions for style and tooling that cannot override the run contract, the voice contract or the tool restrictions. `AutonomousRunner.run(..., capabilities: str = "")` passes it through.
- Modify: `src/vibey_runners/qwen/src/qwenloop/cli/app.py`:
  - `run` gains `capabilities: Path | None = typer.Option(None, "--capabilities", help=...)`;
  - `_run_single` and `_run_plan` load the snapshot, exiting 78 on refusal before the server is started;
  - they wire `SandboxTools(shelf=..., answer_chars=..., mcp=McpGateway.from_document(...))`;
  - they append the `capabilities.applied` event.
- Test: `src/vibey_runners/qwen/tests/test_capability_loader.py`, `tests/test_runner.py`, `tests/test_cli.py`, `tests/test_context_budget.py`

**Interfaces:**
- `CapabilityLoader(store: SnapshotDocumentStoreInterface | None = None, listing: CapabilityListingInterface | None = None, instructions: InstructionFileReaderInterface | None = None)` has `load(path: Path, *, cwd: Path) -> LoadedCapabilities`.
  - It raises `CapabilityRefused(reason)` (a qwenloop infrastructure error) for any `SnapshotDocumentError` or `OSError`, naming only the path.
  - `LoadedCapabilities(document, shelf, prompt: str, listing_form: str, instruction_files: tuple[str, ...], notices: tuple[str, ...])`.
  - `prompt` is the listing (R9) followed by the instruction files under the rest of the budget (R12). It is always within `TokenEstimate.chars(document.capability_prompt_tokens)`.
  - A document `folders` entry outside `cwd` adds a notice, `{folder} is outside the worktree and this loop's file tools cannot reach it`. The tools are never widened.
- The `capabilities.applied` event payload is `{"digest", "plugins": n, "skills": n, "commands": n, "mcp_servers": n, "listing": form, "instruction_files": [names inlined], "notices": [...]}`. It holds no file text and no environment value.
- `run` without `--capabilities` is unchanged: no shelf, `discover` for MCP, and no capability block.

- [ ] **Step 1: Write the failing tests.**
  - Loader:
    - `test_a_refused_document_raises_naming_only_the_path`
    - `test_the_prompt_lists_the_research_skills_then_claude_md`
    - `test_a_claude_md_that_does_not_fit_is_named_never_cut`
    - `test_an_input_folder_outside_the_worktree_is_a_notice_not_a_grant`
  - Runner:
    - `test_the_capability_block_follows_the_voice_contract_and_the_verdict_rule`
    - `test_no_capabilities_leaves_the_prompt_unchanged` (the existing prompt test, byte for byte)
  - CLI:
    - `test_a_refused_document_exits_78_before_the_server_starts` (the fake server's `start` is never called)
    - `test_capabilities_applied_is_in_the_runs_events_with_counts_only`
    - `test_no_env_value_reaches_argv_events_or_logs`: a sentinel in an `env_allow` variable is absent from `events.jsonl`, the run directory, `caplog` and the stderr capture.
  - `test_a_full_snapshot_leaves_the_conversation_its_room` (the acceptance, R8). It builds a document with `capability_prompt_tokens = CAPABILITY_PROMPT_TOKENS_CEILING` and a shelf at the bundle's caps: `MAX_ENTRIES` plugins × `MAX_SKILLS_PER_PLUGIN` skills, each with a 1024-character description, and 256 MCP servers, held in memory through fake seams. It asserts:
    - the listing falls back to the `count` form;
    - `TOKEN_ESTIMATE.tokens(_system_prompt(cwd, "macOS", loaded.prompt)) + TOKEN_ESTIMATE.tokens(json.dumps(_CODING_TOOLS)) <= 32_768 - DEFAULT_CONTEXT_RENEWAL_TOKENS`.
  - `test_the_default_bundle_fits_in_full`: the same check with the default bundle and the real `currency-research` plugin, with the `full` form.
- [ ] **Step 2: Run** `(cd src/vibey_runners/qwen && python -m pytest -q tests/test_capability_loader.py tests/test_runner.py tests/test_cli.py tests/test_context_budget.py)`. Expected: FAIL.
- [ ] **Step 3: Implement.** If the acceptance fails at the ceiling, apply R8's fallback and lower `CAPABILITY_PROMPT_TOKENS_CEILING` in common, naming the measured numbers in the commit body.
- [ ] **Step 4: Run** qwenloop's row at the whole-package 100%, common's row, `mypy --strict`, `lint-imports` and `bandit` for both. Expected: PASS.
- [ ] **Step 5: Commit** `feat(qwenloop): apply the run's capability snapshot inside a 32k context`.

### Task 9: `PluginSystem.VIBEY_BUNDLE`, the gaps, and BUILD gives the local runner its snapshot

**Files:**
- Modify: `src/vibey/domain/engine.py`. Add `PluginSystem.VIBEY_BUNDLE = "vibey-bundle"`, with the docstring: "The person's locked capability snapshot as a loop that cannot run Claude Code's plugins takes it: its skills and plugin commands as text the loop retrieves, and its MCP servers; no hooks, no agents (design Decision 8; ADR-0092, as amended)." In `EngineAffordances.full_access_gaps()`:
  - `if self.plugins is not PluginSystem.CLAUDE_PLUGINS:` becomes `if self.plugins not in _PLUGIN_GRANTS:`;
  - `_PLUGIN_GRANTS: Final = frozenset({PluginSystem.CLAUDE_PLUGINS, PluginSystem.VIBEY_BUNDLE})`;
  - the docstring says "Claude's own plugins or vibey's bundle".
- Modify: `src/vibey/domain/interfaces/value_objects_interface.py` (the `full_access_gaps` docstring)
- Modify: `src/vibey/infrastructure/engines/descriptors.py`. In `QWENLOOP` (and so `GPTOSSLOOP`, through `replace`), set `capabilities_flag="--capabilities"` and these `affordances`:
  - `plugins=PluginSystem.VIBEY_BUNDLE`, `skills=True`, `mcp=True`; `web_search` stays `True` until Phase 6.
  - The evidence for `plugins`, `skills` and `mcp` is rewritten to cite:
    - `--capabilities` in qwenloop `cli/app.py`;
    - `skills_list`, `skill_read` and `SkillShelf` (`vibey_runners.common.capabilities.skill_shelf`);
    - `mcp_list`, `mcp_call`, `McpSessionPool`, `StdioTransport` through the scrubbed launcher and `HttpTransport` (`vibey_runners.common.mcp`);
    - the two `[loops]` budgets.
  - Each of the three ends with `unit-proven; real-run probe pending`. The `skills-context` packet still reaches the plan, and the `plugins` evidence says so.
- Modify: `tests/meta/loop_runner_facts.py`. `_local_runner` drops the `skills-context` fact and gains these facts:
  - `plugins`, `skills` and `mcp` → `src/vibey_runners/qwen/src/qwenloop/cli/app.py` with needle `'"--capabilities"'`;
  - `skills` and `plugins` → `_LOCAL_TOOLS` with needle `'if name in {"skills_list", "skill_read"}:'`;
  - `mcp` → `src/vibey_runners/common/src/vibey_runners/common/mcp/http_transport.py` with needle `"Mcp-Session-Id"`, and `.../mcp/mcp_transport_factory.py` with needle `"launch.argv(server)"`.
- Modify: `tests/meta/test_loop_capability_evidence.py`. Add `LOCAL_SNAPSHOT_NEEDLES` and `test_gptossloop_and_qwenloop_share_every_snapshot_fact`.
- Modify: `tests/domain/test_engine.py`, `tests/infrastructure/engines/test_descriptors.py` (the pinned shown values and gaps), `tests/infrastructure/engines/test_argv.py`, `tests/application/test_build_implement_capabilities.py`, `tests/application/test_conformance.py`, `tests/cli/golden/vibey-loops.json` and `tests/cli/test_loops_cli.py`:
  - In `test_argv.py`, `test_a_document_on_a_descriptor_without_the_flag_is_refused` keeps only `codexloop`, and `test_a_resumed_session_never_carries_the_document` gains both local engines.
  - In `test_build_implement_capabilities.py`, `test_an_engine_without_the_flag_is_given_no_snapshot_and_no_event` keeps only `CODEXLOOP`.
- Test: the files above.

- [ ] **Step 1: Write the failing tests.**
  - `test_plugin_systems_are_skills_context_claude_plugins_and_vibey_bundle`, replacing the two-value assertion at `tests/domain/test_engine.py:211`.
  - `test_vibey_bundle_grants_plugins_and_skills_context_does_not`
  - `test_the_gaps_between_each_lane_and_full_access_are_pinned`, with `gptossloop` and `qwenloop` at `()`.
  - `test_the_sovereign_default_has_every_capability_a_paid_loop_has`: for each PAID descriptor, `set(GPTOSSLOOP.affordances.full_access_gaps()) <= set(paid.affordances.full_access_gaps())`. This is the acceptance in data.
  - `test_local_runner_snapshot_evidence_says_the_real_run_probe_is_pending`, parametrised over `plugins`, `skills` and `mcp`.
  - `test_a_local_runner_is_given_the_snapshot_and_records_it_before_it_starts`, parametrised over `GPTOSSLOOP` and `QWENLOOP` (the Phase 4 harness).
  - `test_the_local_runners_argv_carries_the_document_on_a_new_session_only`
  - `test_vibey_loops_reports_vibey_bundle_for_the_local_runner`
- [ ] **Step 2: Run** `uv run pytest tests/domain tests/infrastructure/engines tests/application/test_build_implement_capabilities.py tests/application/test_conformance.py tests/cli/test_loops_cli.py tests/meta -q`. Expected: FAIL.
- [ ] **Step 3: Implement.** The argv goldens are unchanged, because `_spec` carries no document. The `vibey loops --json` golden changes only in the two local engines' `plugins`, `skills` and `evidence`; the commit body says so.
- [ ] **Step 4: Run** the following. Expected: PASS.
  - the full suite with the four layer floors at 100% (xdist, empty Missing column);
  - the PostgreSQL system test `tests/system/test_worker_run_inputs_wiring.py`;
  - `uv run mypy --strict src/vibey`, `uv run lint-imports` and `uv run bandit -q -r src/vibey`;
  - the `noloss` property suite at 10,000 examples.
- [ ] **Step 5: Commit** `feat(engines): the local runner takes the vibey bundle, and full access counts it`.

### Task 10: ADR-0092 amended, ADR-0103's Phase 5 section, and the references

**Files:**
- Modify: `docs/architecture/decisions/0092-large-tasks-are-sliced-into-the-cdd-layers-before-they-run.md`. Its body is never rewritten (an ADR is a record); there are three edits:
  1. Under `## Decision` → `### Lanes`, after the first bullet ("`EngineAffordances` gains `skills` and `web_search` ... Unknown is a gap, not a grant."), add the line `  *(Amended 2026-11-25: `vibey-bundle` grants plugins too; see the second amendment at the foot.)*`.
  2. Under `## Added after the first draft`, after the bullet that begins "**The local runner reaches MCP**", add `  *(Superseded 2026-11-25 for a run given a capability snapshot: see the second amendment at the foot.)*`.
  3. At the foot, after "## Amendment, 2026-11-22: codexloop's MCP claim is withdrawn", add this section, verbatim:

     ```markdown
     ## Amendment, 2026-11-25: the local runner's plugins are the vibey bundle

     SP-LOOPS Phase 5 (plan `docs/superpowers/plans/2026-11-25-sp-loops-phase5-local-runner.md`;
     design Decision 8) gives the local runner (`gptossloop`, `qwenloop`) plugins it can use, and so
     changes what counts as a plugin grant.

     - `PluginSystem` gains `vibey-bundle` (`VIBEY_BUNDLE`): the skills, the plugin commands (as text
       the loop retrieves) and the MCP servers of the person's locked capability snapshot, with no
       plugin hooks and no plugin agents. A loop that cannot run Claude Code's own plugin system
       takes plugins this way.
     - `full_access_gaps()` counts `claude-plugins` and `vibey-bundle` as granting plugins;
       `skills-context` is still a gap. Hooks and agents are out of #1666 for every loop that is
       not Claude Code: no runtime exists for them there.
     - The bullet "**The local runner reaches MCP**" above is superseded for a run given a snapshot
       (`run --capabilities PATH`). Such a run reaches exactly the snapshot's servers: a `local`
       server over stdio through the scrubbed launcher, a `remote` server over streamable HTTP, with
       one persistent session per server for the run, closed when the run ends. `mcp_list` and
       `mcp_call` stay its only two MCP tools, and one tool's input schema is fetched when asked
       for, within `[loops] capability_answer_tokens`, never cut. A failing server is a tool error
       for the model, never the end of the run. Without a snapshot the runner still reads
       `~/.claude.json` and `QWENLOOP_MCP_CONFIG`, and never the worktree's `.mcp.json`.
     - The local runner loads skills: their names and descriptions in its system prompt, within
       `[loops] capability_prompt_tokens`, and their bodies through `skills_list` and `skill_read`.
     - `gptossloop`'s and `qwenloop`'s full-access gaps are now none, pinned in
       `tests/infrastructure/engines/test_descriptors.py`. Each claim is pinned to runner code by
       `tests/meta/loop_runner_facts.py`, and its evidence says the real-run probe is pending until
       the operator records one.
     ```
- Modify: `docs/architecture/decisions/0103-the-loop-capability-bundle.md`. Its status is unchanged. Add `## Phase 5: the local runner applies the snapshot` after the Phase 4 section, recording R1 to R16 in the Phase 4 section's form. End it with "Still open after Phase 5": no real `gptossloop` or MCP server run yet; claudeloop enforces no remote call budget (R13); and the token estimate is characters ÷ 4, not the model's tokenizer.
- Modify: `docs/reference/cli.md`:
  - the `capabilities` row: `plugins` (`skills-context`, `claude-plugins` or `vibey-bundle`);
  - the `gptossloop`, `qwenloop` row of the per-loop table: files, pasted text, `vibey-bundle` (skills and plugin commands through `skills_list` and `skill_read`, MCP through `mcp_list` and `mcp_call` over the snapshot's servers, stdio and HTTP, one session per server per run), web search (unchanged until Phase 6); no images, no pasted images;
  - the `loop_capabilities_unresolved` and `engine_misconfigured` paragraphs, which now cover both local engines.
- Modify: `docs/reference/configuration.md`:
  - In `[loops]`, the two R8 keys with their defaults, ranges and meaning, with a sentence saying claudeloop ignores them.
  - A paragraph on what Phase 5 applies to the local runner.
  - `[engine_environment]`: an MCP server's `env_allow` variable reaches a `gptossloop` or `qwenloop` session only if it is passed through there, as for claudeloop.
- Modify: `src/vibey_runners/qwen/README.md` and `src/vibey_runners/qwen/docs/capability-matrix.md`: `--capabilities`, the `[mcp]` table, `skills_list` and `skill_read`, and the persistent sessions.
- Create: `changelog.d/sp-loops-phase5-local-runner.feature.md` and `changelog.d/jsonrpc-peer-in-common.feature.md`
- Test: `tests/meta/test_cli_doc_capabilities.py`

- [ ] **Step 1: Write the failing tests.**
  - `test_the_cli_doc_names_vibey_bundle_and_the_local_runners_skill_tools`
  - `test_the_configuration_doc_names_both_token_budgets_with_their_defaults` (`3072`, `3000`)
  - `test_adr_0092_carries_the_2026_11_25_amendment_and_marks_both_bullets`
- [ ] **Step 2: Run** `uv run pytest tests/meta/test_cli_doc_capabilities.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement.** Grep `docs/` for `skills-context` and `mcp_list` wherever it describes the local runner, and correct each. Historical plans under `docs/superpowers/plans/` are left as written.
- [ ] **Step 4: Run** `uv run vibey-gh corpus-index --check`, the strict docs build, `uv run pytest tests/meta -q` and the full layer floors. Expected: PASS. No ADR is added, so every advertised count is unchanged.
- [ ] **Step 5: Commit** `docs(loops): the local runner's snapshot in ADR-0092, ADR-0103 and the references`.

## Verification (the phase is done when all of these hold)

- `uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=` passes, and the four layer floors are 100% with an empty Missing column. The tenant rows also pass at 100%:
  - common's row, with `jsonrpc`, `mcp`, `capabilities` and `infrastructure`;
  - qwenloop's whole-package floor;
  - claudeloop's four rows.

  `mypy --strict`, `lint-imports` and `bandit` are clean for `src/vibey`, `src/vibey_runners/common`, `src/qwenloop` and `src/claudeloop`. `uv run ruff check .`, `uv run ruff format --check .`, `uv lock --check` and `uv run vibey-gh corpus-index --check` are clean.
- The `noloss` property suite passes at 10,000 examples, and `git diff origin/develop -- src/vibey/domain/noloss.py` is empty.
- `tests/infrastructure/mcp/test_mcp_golden.py` passes with no change to its golden transcript.
- **Operator-run real-run probe (unverified until the operator runs it).** This needs a real `gptossloop` on Ollama (`VIBEY_OLLAMA_URL`, GPT-OSS 20B).
  1. In your own `vibey.toml`:
     - Run `vibey loops mcp add probe --local -- <a small stdio MCP server that exposes one tool with an input schema>` and keep the default `currency-research` plugin.
     - If you have an https MCP server, add it with `vibey loops mcp add probe-remote --remote <url>`.
  2. Run `vibey inputs add <project> --paste "PROBE-PASTE-<random>"`. Then start one BUILD job with `gptossloop` pinned and a plan that asks the model to read the `research-search-and-source-quality` skill and to call the probe tool.
  3. Confirm all of the following for that run:
     - `.qwenloop/runs/<id>/events.jsonl` holds `capabilities.applied` with `listing: "full"`, and its `digest` equals that of `vibey loops skills list --json` (with no project `[loops]`).
     - The transcript shows `skill_read` returning the skill's text, `mcp_list` then `mcp_list(probe, <tool>)` returning the schema, and `mcp_call` answering with `untrusted` set.
     - The ledger holds one `LoopCapabilitiesSnapshotted` before the run's `SessionSeeded`.
     - After the job settles, `pgrep -f <probe server command>` finds nothing, and `<config>/loops/snapshots/` holds no folder for that run.
  4. Repeat with a probe server that exits after its first answer. The run goes on, and the transcript shows a tool error, then the "unavailable for the rest of this run" answer.
  5. Repeat steps 2 and 3 with `qwenloop` switched on (`[features] qwenloop = true`) and pinned.
  6. Record the outcome in the PR. Until then, the descriptor evidence says "unit-proven; real-run probe pending".
- Not verified while writing this plan:
  - Whether gpt-oss:20b uses `skills_list`, `skill_read` and the paged `mcp_list` well. The probe shows it, and the storm measurements will.
  - How far characters ÷ 4 is from the model's own tokenizer on JSON tool schemas.
  - Streamable HTTP servers that answer a request with an SSE stream that holds more than the response.
  - Whether vibey's stop path sends SIGTERM before SIGKILL to a local runner's process group. If it sends SIGKILL only, R5's stdin-EOF fallback is what closes the servers.

## Self-review

1. **Spec coverage, by the parent's Phase 5 task list:**

   | Parent item | Where |
   |---|---|
   | MCP client over the shared JSON-RPC peer moved into `common` | Task 1 (the peer), Task 3 (client, stdio, pool), Task 4 (HTTP) |
   | stdio plus HTTP | Tasks 3 and 4 |
   | persistent session | Task 3 (pool), Task 7 (lifecycle, R5) |
   | schemas on demand within a token budget | Task 7 (R7), Task 2 (R8 keys) |
   | skill tools over the snapshot (`skills_list`, `skill_read`) | Task 5 (shelf), Task 6 (tools) |
   | `PluginSystem.VIBEY_BUNDLE` added, `full_access_gaps()` counts it | Task 9 |
   | ADR-0092 amended | Task 10 |
   | research skills listed (names and descriptions only) in the system prompt | Task 5 (listing), Task 8 (prompt) |
   | Acceptance: every capability the paid loops have, within 32k | Task 9 (`test_the_sovereign_default_has_every_capability_a_paid_loop_has`), Task 8 (`test_a_full_snapshot_leaves_the_conversation_its_room`), Verification probe |

   Decision 8's commands are Task 5 and R10; Decision 9's trust levels are R4, R13 and Task 4; Decision 10 is R9 and Task 5; Decision 3 is R11.
2. **Type consistency.**
   - The `jsonrpc` peer and codec (Task 1) are what `McpSession` (Task 3) runs on.
   - `ScrubbedLaunch` (Task 3) feeds `McpTransportFactory` (Task 4) and claudeloop's `McpConfigTranslator`.
   - `BundleSpec.capability_prompt_tokens` and `capability_answer_tokens` (Task 2) reach the runner through `SnapshotDocument` v2. They bound `CapabilityListing.render` and `InstructionFileReader`'s `budget_chars` (Task 5), and the `answer_chars` of `SandboxTools` (Tasks 6 and 7) and `CapabilityLoader` (Task 8).
   - `SkillShelf` (Task 5) is what `SandboxTools(shelf=...)` (Task 6) and `CapabilityLoader` (Task 8) hold.
   - `McpSessionPool` (Task 3) is what `McpGateway` (Task 7) adapts.
   - `PluginSystem.VIBEY_BUNDLE` and `capabilities_flag` (Task 9) meet the Phase 4 `build_argv` and handler unchanged.
3. **Points where the repository disagrees with the parent plan or the brief, and what this plan does:**
   - vibey's MCP server does not use the peer. It imports only the codec and the errors (`src/vibey/infrastructure/mcp/stdio_server.py` lines 25 to 31). The peer's users are ACP (`src/vibey/cli/acp.py` line 46; `src/vibey/infrastructure/acp/peer_client_channel.py`). The move therefore takes all three, and the server's golden transcript is the proof that its bytes are unchanged (R1).
   - Part of the peer's vocabulary lives in the domain (`src/vibey/domain/jsonrpc_errors.py`, re-exported by `infrastructure/jsonrpc/errors.py`). It moves with the peer.
   - qwenloop does not depend on common today: `src/vibey_runners/qwen/pyproject.toml` line 26, and the qwenloop rows of `.github/ci-matrices.toml` (lines 106, 290, 298 and 305) install only `.[dev]`. Task 6 changes the install and R16 records why nothing is declared.
   - The Phase 4 tests pin the local runner as taking no document (`tests/application/test_build_implement_capabilities.py` line 280; `tests/infrastructure/engines/test_argv.py` line 377). Task 9 narrows both to `codexloop`.
   - The local runner already claims `mcp=True` and `web_search=True` (`src/vibey/infrastructure/engines/descriptors.py`, the `QWENLOOP` affordances), and its pinned gaps are `("skills", "plugins")` (`tests/infrastructure/engines/test_descriptors.py` line 363). Phase 5 closes exactly those two.
   - Decision 8 puts plugin commands in `VIBEY_BUNDLE`, but the parent's Phase 5 list leaves them out. This plan includes them (R10).
   - The capability document is strict about its keys and is at version 1 (`snapshot_document.py` line 41). New keys therefore need version 2 (Task 2), which the parent did not foresee.
   - The existing `mcp_list` and `mcp_call` cut their answers silently (`src/vibey_runners/qwen/src/qwenloop/infrastructure/tools.py` lines 286 and 298), against ADR-0075. Task 7 replaces both cuts.
4. **Left to the builder:**
   - private helper names;
   - the exact wording of notices and tool descriptions other than those pinned above;
   - how `SkillShelf.page` balances entries across pages, within the stated rule;
   - where in `cli/app.py` the SIGTERM handler is installed, within `_run_plan`.
