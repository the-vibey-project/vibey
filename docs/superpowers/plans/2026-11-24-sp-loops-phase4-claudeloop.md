# SP-LOOPS Phase 4: `claudeloop` and `claudeloop-local` apply the snapshot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A BUILD run that falls to `claudeloop` or `claudeloop-local` is given exactly the person's locked capability snapshot and nothing else: the snapshot's plugins as local folders, its MCP servers with an explicit transport, its skills by name, no settings sources, the repository's `CLAUDE.md` and `AGENTS.md` as text, and the run's input folder. Claude Code's built-in `WebSearch` and `WebFetch` are switched off. `claudeloop run --attach` files reach the agent. The snapshot's digest is recorded in a new append-only ledger event, `LoopCapabilitiesSnapshotted`, before the engine is spawned. The descriptors' evidence says all of this.

**Architecture:** The conductor resolves the person's bundle into a snapshot with the existing `CapabilityResolver`. It then writes one JSON document, `capabilities.json`, into that run's 0700 snapshot folder. The document's format, writer and strict reader live once in `vibey_runners.common.capabilities` (stdlib only). vibey passes the document's path as `claudeloop run --capabilities PATH`, records the event, and removes the folder when the run ends. claudeloop reads the document with the common reader and turns it into an immutable `AppliedCapabilities` value. The gateway merges that value into every `ClaudeAgentOptions` it builds, so a mid-run resource change can add to the snapshot but never remove from it. A local MCP server starts through a common scrubbed-environment launcher, so environment values never appear on an argv, in a file or in a log. `claudeloop-local` is the same binary, so it runs the same code path.

**Tech Stack:** Python 3.12+; `claude-agent-sdk` 0.2.152 (`ClaudeAgentOptions.disallowed_tools`, `setting_sources`, `strict_mcp_config`, `skills`, `plugins`, `mcp_servers`, `add_dirs`); stdlib `json`, `os`, `shutil`; Typer; pytest and Hypothesis; import-linter.

**Spec:** `docs/superpowers/specs/2026-11-22-uniform-loop-capabilities-design.md` (Goal 3, Decisions 2, 3, 4, 7, 9). Parent plan: `docs/superpowers/plans/2026-11-22-sp-loops-uniform-loop-capabilities.md` ("Phases 3 to 8", Phase 4). Previous phase: `docs/superpowers/plans/2026-11-23-sp-loops-phase3c-store-handoff-doctor.md`. Record: ADR-0103 (its Consequences list items it leaves to Phase 4).

## Rulings

Where the spec leaves a choice open, this plan decides it. Each ruling is given as the decision, the reason, and the cost if it is wrong.

- **R1 (transport): the snapshot reaches the runner as a JSON document in the run's snapshot folder, named by `--capabilities PATH`.** The runners never import `vibey`, and a file in the person's own 0700 folder is outside the worktree the model edits. Cost if wrong: a second transport later; the document format stays.
- **R2 (scope): only `build.implement` runs are given the snapshot.** That is the job that "falls to any loop". `build.verify`'s reviewer, DESIGN and DECOMPOSE keep today's behaviour. Cost if wrong: reviewer sessions still load the person's own Claude settings until a follow-up gives them the snapshot.
- **R3 (event): a new `EventKind.LOOP_CAPABILITIES_SNAPSHOTTED = "LoopCapabilitiesSnapshotted"`, not an `ArtifactProduced`.** It is recorded only for an engine whose descriptor takes the snapshot (`capabilities_flag`), and it is withheld from ledger publication. No-loss rules match kinds by identity, so the new kind opens, closes and spends nothing. Cost if wrong: one more kind in the enum; a later move to an artifact type is a superseding event, never an edit.
- **R4 (built-in web): a generic person-only key, `[loops] builtin_web`, default `false`.** claudeloop maps `false` to `disallowed_tools = ["WebSearch", "WebFetch"]`, Claude Code's own tool names, held as one claudeloop domain constant with its reason written beside it. vibey stops passing `--web-search` and `--deep-research`. claudeloop's `web_search` affordance becomes `False` until Phase 6 gives every loop `vibey_search`. Cost if wrong: claudeloop has no web search between Phase 4 and Phase 6. A person who needs it sets `builtin_web = true`.
- **R5 (settings): `setting_sources=[]` and `strict_mcp_config=True` are set only when a snapshot is applied.** Without them the SDK defaults `setting_sources` to `["user", "project"]` as soon as `skills` is set (`subprocess_cli.py` `_apply_skills_defaults`). A standalone `claudeloop run` with no `--capabilities` is unchanged, and the existing `test_a_lane_with_nothing_named_is_not_narrowed` stays true for it. Cost if wrong: none for vibey's runs; standalone users keep their current behaviour.
- **R6 (skills): the options enable exactly the catalog's skills, by qualified name `plugin:skill`.** A skill the index skipped is therefore never enabled, even though Claude Code could discover it. `[loops] skills` (the names a loop is pointed at) is not applied in Phase 4; Phase 7 makes DESIGN and REVIEW name them. Cost if wrong: a skill Claude Code would accept but the index refused stays off.
- **R7 (MCP): `local` becomes `{"type": "stdio"}` and starts through the scrubbed launcher. `remote` becomes `{"type": "http"}` (streamable HTTP), never `sse`.** The launcher keeps only `env_allow` names, reads their values from its own inherited environment, and execs the server. A name that is absent is skipped, and that name is logged by claudeloop. Which variables reach the claudeloop session at all is still `[engine_environment]`'s decision; that is unchanged. Cost if wrong: an SSE-only server does not connect, or a server misses a variable the person did not pass through.
- **R8 (instruction files): claudeloop reads `CLAUDE.md` and `AGENTS.md` from the run's `cwd` only, and appends them to the system prompt, never to the plan.** A wind-down seed must reach the engine byte for byte (Phase 3c). A file over `[loops] instruction_max_bytes` is not inlined: it is named with its size and the agent is told to read it. It is never truncated (ADR-0075). A symlink is refused. Cost if wrong: a very large `CLAUDE.md` is read on demand rather than preloaded.
- **R9 (failure): a snapshot that cannot be resolved parks the job (`loop_capabilities_unresolved`); a run never starts without it.** At the runner, a document that is refused is exit 78. The existing `engine_misconfigured` gate then parks the job. Cost if wrong: a person answers a gate that a retry might have cleared.
- **R10 (lifetime): the run's snapshot folder is removed when `handle()` returns or raises.** A worker sweeps at start with an age of `max([loops] snapshot_max_age_days, engine run deadline + 1 hour)`. A session is bounded by its deadline, so no live marker is needed; that answers ADR-0103's open consequence. Cost if wrong: a manual `vibey loops snapshots prune --older-than-days 1` can still remove a running run's snapshot. That is a person's explicit act, and the docs say so.
- **R11 (`claudeloop-local`): the same code path, with one difference.** `builtin_web = true` does not re-enable the web tools on a local backend: the disallow list is always applied there, and claudeloop logs a notice. Everything else is identical: plugins, MCP, skills, settings sources, instruction files and folders. The descriptor's effort projection and profile are unchanged. Cost if wrong: a local backend that could serve `WebFetch` does not get it.
- **R12 (merge with flags): the snapshot and claudeloop's own `--plugin`, `--skill`, `--connector` and `--add-folder` are a union, with the snapshot first.** An MCP name in both is refused with exit 2. `--web-search` with `builtin_web = false` is also refused with exit 2. vibey never passes both. Cost if wrong: a person mixing them by hand gets a refusal, not a silent override.
- **R13 (new `[loops]` keys, person-only):**
  - `builtin_web` (bool, default `false`)
  - `instruction_files` (plain names, default `["CLAUDE.md", "AGENTS.md"]`, at most 16)
  - `instruction_max_bytes` (int, default `65536`, between 1 and 1048576)
  - `snapshot_max_age_days` (int, default `7`, at least 1)

  The first three are part of what a loop is given, so they enter `CapabilitySnapshot.digest`. `snapshot_max_age_days` does not. A project's `[loops]` may still only `disable`. Cost if wrong: every existing digest changes once; digests are per run and nothing compares them across versions.
- **R14 (document size): the reader refuses a document over 4 MiB.** This is a parser guard sized from the bundle's own caps (256 entries × 4096 characters, over four lists), not a policy limit, and it is stated at the constant. Cost if wrong: none in practice; the conductor writes the document itself.

## Global Constraints

- The project's `vibey.toml` is untrusted: marketplaces, plugins, MCP servers and the R13 keys come only from the person's own configuration (`acp_user_config()`). A project may only narrow (`disable`).
- A run never fetches from the network on its own; it uses the lock. Resolving a snapshot for a BUILD run reads only locked trees.
- A loop never receives the host token, the agent token or any Brave key. An MCP server's environment never keeps a name that `SECRET_ENV_NAMES` or `SECRET_ENV_PATTERN` (`capabilities/bundle.py`) refuses. That is checked when the bundle is read, when the document is read, and again in the launcher.
- An MCP server's environment values are never written to the ledger, a log, the run directory, an events file or an argv. Only variable names may appear, and only in claudeloop's own log.
- Plugin, skill and MCP-config text from the locked bundle is instruction. `CLAUDE.md` and `AGENTS.md` are instruction text by Decision 4. MCP output, attachments and pasted text stay data.
- A capability claim needs evidence (`EngineAffordances.evidence`); unknown is `None`, never `True`.
- `domain/` stays pure in both `vibey` and `claudeloop`. Code lives in classes, with an interface beside each class: `services/interfaces/` in vibey, `infrastructure/interfaces/` and `domain/interfaces/` in claudeloop, `capabilities/interfaces/` in common. A module-level function carries its reason at the definition.
- 100% branch coverage per layer: vibey's four floors; claudeloop's domain, application, infrastructure and cli rows (`.github/workflows/ci.yml` `tools` matrix); common's `capabilities` and `infrastructure`. All verified with xdist and an empty Missing column. No test depends on thread timing, sleeps, the platform, the network, a real `claude` binary or a real MCP server.
- `domain/noloss.verify` and its ten rules are not changed.
- The ledger is append-only: the new kind is only ever appended.
- Never read or print real keys; tests use fake values and sentinels. Conventional Commits, each ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Run `git commit` and `git push` in the foreground; never `--no-verify`.
- Pushes and test runs in a worktree use `VIBEY_TEST_TEMPLATE_DB=<a worktree-only name>`.
- Agent-surface maintenance: if a skill or procedure changes, update the Claude, Cursor, Codex and Antigravity trees in the same PR. No task here changes one; if an implementer does, this applies.

## Review Focus

The failures most likely here that no happy path exercises, most likely first:

1. **A mid-run resource change drops the snapshot.** `claudeloop attach`, `skill` or `connector` while a run is going calls `set_session_resources`, which today replaces `plugins`, `skills`, `mcp_servers` and `add_dirs` wholesale (`application/runner.py` ~line 1111, `infrastructure/agent/gateway.py` `set_session_resources`). Task 4: `test_a_mid_run_resource_change_keeps_every_snapshot_capability`.
2. **A snapshot run still loads the repository's or the person's own Claude settings.** The SDK sets `setting_sources = ["user", "project"]` whenever `skills` is set and `setting_sources` is None. Task 4: `test_the_cli_command_carries_empty_setting_sources_strict_mcp_and_the_disallow_list`.
3. **An MCP environment value or a secret-named variable leaks** onto an argv, into `events.jsonl`, `resources/*.json`, structlog or the ledger. Task 3: `test_values_never_reach_argv_and_only_allowed_names_reach_the_child`. Task 5: `test_no_env_value_reaches_argv_events_resources_or_logs`. Task 7: `test_the_payload_holds_only_the_digest_ids_and_counts`.
4. **A BUILD run starts without its snapshot.** A resolution error is swallowed, the flag is missing from the argv, or a follow-up job skips the snapshot. It must park instead. Task 8: `test_an_unresolvable_snapshot_parks_and_never_starts_the_engine`, `test_the_argv_carries_the_capabilities_flag_and_document`, `test_a_wind_down_follow_up_is_given_a_fresh_snapshot_and_the_seed_is_unchanged`.
5. **A tampered or foreign document is applied instead of refused with exit 78.** Examples: a plugin folder outside the run folder, a group-writable folder, a version that is not known. Task 2: `test_a_plugin_folder_outside_the_documents_folder_is_refused`. Task 4: `test_a_refused_document_exits_78_before_any_session`.

## Order of work

Task 1 is the `--attach` fix: the smallest task, independent, and it shows the bug first. Then Tasks 2 and 3 (common: the document and the launcher), then Tasks 4 to 6 (claudeloop applies the snapshot), then Task 7 (the ledger kind), Task 8 (the BUILD wiring) and Task 9 (descriptors, evidence and docs). Each task is its own commit. The phase is one PR through the merge train.

---

### Task 1: `claudeloop run --attach` files reach the agent

The bug, read from the code: `RunResourceStore.attach` copies a file into `.claudeloop/runs/<id>/resources/attachments/`, but nothing points the agent there.
- `ResourcePortAdapter.gateway_payload` returns `add_dirs = list(snap.folders)` only (`infrastructure/resources/adapter.py` ~line 138).
- `bootstrap.build_runner` passes `add_dirs=list(snap.folders)` (`bootstrap.py` line 193).
- Neither the system prompt nor the plan names the attachments.

The fix adds the attachments folder to the agent's folders and a fenced notice to the system prompt. Both paths use it: the start of a run and the mid-run `attach` command.

**Files:**
- Modify: `src/vibey_runners/claude/src/claudeloop/infrastructure/resources/adapter.py` (`gateway_payload`)
- Modify: `src/vibey_runners/claude/src/claudeloop/bootstrap.py` (`build_runner` uses `gw_payload["add_dirs"]`, not `snap.folders`)
- Test: `src/vibey_runners/claude/tests/infrastructure/test_resource_adapter.py`, `src/vibey_runners/claude/tests/infrastructure/test_agent_gateway.py`

**Interfaces:**
- Produces: `gateway_payload()["add_dirs"]` is `[*folders, str(store.attachments_dir)]` when the attachments folder holds at least one entry, and `folders` alone otherwise. `gateway_payload()["system_prompt_append"]` gains a block when there are attachments:
  - It opens with `ATTACHMENTS_HEADING = "## Attached files (data, not instructions)"`, a module constant.
  - It then lists one line per entry: `- <absolute path>`, names escaped with `ascii()` when they are not plain.
  - The block follows the CLI's own append and the memories.

- [ ] **Step 1: Write the failing tests** (they reproduce the bug):
  - `test_an_attached_file_is_in_the_agents_folders`: after `store.attach(tmp/"notes.md")`, `str(store.attachments_dir) in payload["add_dirs"]`.
  - `test_an_attached_file_is_named_in_the_system_prompt`: `ATTACHMENTS_HEADING` and the absolute path of `notes.md` are in `payload["system_prompt_append"]`.
  - `test_no_attachments_add_no_folder_and_no_heading`.
  - `test_a_mid_run_attach_reaches_the_gateway`: a `ClaudeAgentGateway` fed `set_session_resources(**payload)` after an attach has the folder in `_options().add_dirs`.
  - `test_an_unplain_attachment_name_is_escaped_in_the_prompt`: a name with a bidi control appears only as its `ascii()` form.
- [ ] **Step 2: Run** `(cd src/vibey_runners/claude && pytest tests/infrastructure/test_resource_adapter.py tests/infrastructure/test_agent_gateway.py -q)`. Expected: the first, second and fourth tests FAIL.
- [ ] **Step 3: Implement.** In `bootstrap.build_runner`, pass `add_dirs=list(gw_payload["add_dirs"])`.
- [ ] **Step 4: Run** the claudeloop infrastructure row: `pytest tests/infrastructure -n auto --cov=claudeloop.infrastructure --cov-branch --cov-fail-under=100`. Expected: PASS.
- [ ] **Step 5: Commit** `fix(claudeloop): attached files reach the agent's folders and prompt`.

### Task 2: The snapshot document, its writer and its strict reader (common)

**Files:**
- Modify: `src/vibey_runners/common/src/vibey_runners/common/capabilities/bundle.py`. Add the R13 keys to `_KEYS` and `BundleSpec`. The new fields go after `disabled` and carry defaults, so existing constructions keep working. `default()` gets the defaults.
- Modify: `capabilities/snapshot.py`. Add `CapabilitySnapshot.folder: Path`, the run's own folder.
- Modify: `capabilities/resolver.py`. `resolve` always makes the run folder, even when the bundle enables no plugin, and removes it on any failure as it does now. `_digest` adds `builtin_web`, `instruction_files` and `instruction_max_bytes`.
- Create: `capabilities/snapshot_document.py` (`SnapshotDocument`), `capabilities/snapshot_document_store.py` (`SnapshotDocumentStore`), `capabilities/snapshot_document_error.py` (`SnapshotDocumentError(ValueError)`), and beside them `capabilities/interfaces/snapshot_document_interface.py` and `capabilities/interfaces/snapshot_document_store_interface.py`.
- Modify: `src/vibey/cli/loops_bundle.py` (`_discard` removes `snapshot.folder`, not a folder derived from `plugin_dirs`)
- Test: `src/vibey_runners/common/tests/capabilities/test_bundle.py`, `test_resolver.py`, `test_snapshot_document.py`, `test_snapshot_document_store.py`; `tests/cli/test_loops_bundle.py`

**Interfaces:**
- `BundleSpec` gains these fields:
  - `builtin_web: bool = False`
  - `instruction_files: tuple[str, ...] = ("CLAUDE.md", "AGENTS.md")`
  - `instruction_max_bytes: int = 65536`
  - `snapshot_max_age_days: int = 7`

  Each is validated by `from_mapping` with a `BundleError` naming the key path. `instruction_files` reuses `_names`, at most 16 entries.
- `@dataclass(frozen=True, slots=True) class SnapshotDocument` has these fields:
  - `version: int` (`DOCUMENT_VERSION: Final = 1`)
  - `digest: str`
  - `plugin_dirs: tuple[Path, ...]`
  - `skills: tuple[str, ...]` (qualified `plugin:skill`, in catalog order)
  - `mcp_servers: tuple[McpServerSpec, ...]`
  - `builtin_web: bool`
  - `instruction_files: tuple[str, ...]`
  - `instruction_max_bytes: int`
  - `folders: tuple[Path, ...]` (the run's input folder, when there is one)

  Its methods:
  - `@classmethod of(snapshot: CapabilitySnapshot, bundle: BundleSpecInterface, folders: Sequence[Path]) -> SnapshotDocument`
  - `to_json() -> str`, canonical: sorted keys, `ensure_ascii=True`
  - `@classmethod from_json(text: str, folder: Path) -> SnapshotDocument`, which raises `SnapshotDocumentError`. `mcp_servers` is written in the `[[loops.mcp_servers]]` table shape and parsed back through `BundleSpec.from_mapping({"plugins": [], "mcp_servers": raw, ...})`, so one validator (the secret-name refusal included) governs both files.
- `SnapshotDocumentStore` has `DOCUMENT_NAME: Final = "capabilities.json"`, `DOCUMENT_MAX_BYTES: Final = 4 * 1024 * 1024` (R14), and two methods:
  - `write(document: SnapshotDocument, folder: Path) -> Path` writes 0600 through `O_CREAT | O_EXCL | O_NOFOLLOW`.
  - `read(path: Path) -> SnapshotDocument` reads through `BoundedFileReader.read_text(path, DOCUMENT_MAX_BYTES)` and refuses each of these:
    - a folder not owned by `os.getuid()`, or one with any group or other mode bit;
    - a document that is not mode 0600;
    - a version that is not known;
    - a `digest` not matching `^sha256:[0-9a-f]{64}$`;
    - any `plugin_dirs` entry whose realpath is not inside the folder's realpath, or that is not a folder holding `.claude-plugin/plugin.json`;
    - any `folders` entry that is not absolute;
    - a skill name not matching `^[A-Za-z0-9][A-Za-z0-9._-]*:[A-Za-z0-9][A-Za-z0-9._-]*$`.

- [ ] **Step 1: Write the failing tests.**
  - Bundle:
    - `test_the_default_bundle_turns_builtin_web_off_and_names_claude_md_and_agents_md`
    - `test_builtin_web_must_be_a_bool`, raising `BundleError("loops.builtin_web", ...)`
    - `test_an_instruction_file_with_a_slash_is_refused`
    - `test_instruction_max_bytes_outside_1_to_1048576_is_refused`
    - `test_snapshot_max_age_days_below_one_is_refused`
  - Resolver:
    - `test_a_bundle_with_no_plugins_still_gets_a_run_folder`
    - `test_a_failed_resolve_leaves_no_run_folder` (the existing guarantee, extended to the always-made folder)
    - `test_the_digest_changes_when_builtin_web_changes_and_not_when_the_max_age_does`
  - Document:
    - `test_a_document_round_trips_through_json`
    - `test_the_json_holds_no_env_value_only_env_allow_names`
    - `test_a_plugin_folder_outside_the_documents_folder_is_refused`, including through a symlink
    - `test_a_group_writable_folder_is_refused`
    - `test_an_unknown_version_is_refused`
    - `test_a_document_over_four_mib_is_refused_unread`
    - `test_a_secret_named_env_allow_in_a_document_is_refused` (`VIBEY_HUB_TOKEN`; `MY_API_KEY`)
    - `test_write_refuses_an_existing_document`
  - CLI: `test_skills_list_leaves_no_run_folder_behind` (the folder now always exists, so `_discard` must remove it).
- [ ] **Step 2: Run** `(cd src/vibey_runners/common && python -m pytest -q tests/capabilities)` and `uv run pytest -q tests/cli/test_loops_bundle.py`. Expected: FAIL.
- [ ] **Step 3: Implement.** Update every test that pins a digest value. The new bundle fields change it once, deliberately; each such update is named in the commit body.
- [ ] **Step 4: Run** common's CI row (`--cov=vibey_runners.common.capabilities --cov-branch --cov-fail-under=100`), `mypy --strict src/vibey_runners/common` and `lint-imports`. Then run the vibey cli floor. Expected: PASS.
- [ ] **Step 5: Commit** `feat(loops): the run's capability document, written once and read strictly`.

### Task 3: A scrubbed-environment launcher for local MCP servers (common)

**Files:**
- Create: `src/vibey_runners/common/src/vibey_runners/common/capabilities/scrubbed_exec.py` (`ScrubbedExec`) and `capabilities/interfaces/scrubbed_exec_interface.py`
- Test: `src/vibey_runners/common/tests/capabilities/test_scrubbed_exec.py`

**Interfaces:**
- `ScrubbedExec(execve: Callable[[str, Sequence[str], Mapping[str, str]], NoReturn] = os.execve, which: Callable[..., str | None] = shutil.which, err: TextIO = sys.stderr)`
- `run(argv: Sequence[str], environ: Mapping[str, str]) -> int` parses `--allow NAME` (repeatable), then `--`, then the command. It resolves `command[0]` with `which(command[0], path=environ.get("PATH"))` before scrubbing. It then calls `execve(resolved, command, {name: environ[name] for name in allow if name in environ})`. It returns only on refusal:
  - `2` when `--` or a command is missing;
  - `78` when a name matches `SECRET_ENV_NAMES` or `SECRET_ENV_PATTERN` (the message names the variable, never a value);
  - `127` when the command cannot be found.
- Module-level `main()` runs `ScrubbedExec().run(sys.argv[1:], os.environ)`, behind `if __name__ == "__main__"`. Its written reason: `python -m vibey_runners.common.capabilities.scrubbed_exec` needs a module-level entry point.
- `LAUNCHER_MODULE: Final = "vibey_runners.common.capabilities.scrubbed_exec"`

- [ ] **Step 1: Write the failing tests** with a recording fake `execve` and a fake `which`. No process is started.
  - `test_values_never_reach_argv_and_only_allowed_names_reach_the_child`: environ holds `HOME=/h`, `SENTINEL_URL=s3ntinel` and `ANTHROPIC_API_KEY=k`; allow is `HOME` and `SENTINEL_URL`. The child env is exactly those two, and `s3ntinel` is in no argv element.
  - `test_a_secret_named_allow_is_refused_with_78_naming_only_the_variable`: the stderr text holds `ANTHROPIC_API_KEY` and not `k`.
  - `test_an_allowed_name_absent_from_the_environment_is_skipped`
  - `test_the_command_is_resolved_with_the_inherited_path_before_scrubbing`
  - `test_a_missing_separator_is_2_and_an_unknown_command_is_127`
- [ ] **Step 2: Run** `(cd src/vibey_runners/common && python -m pytest -q tests/capabilities/test_scrubbed_exec.py)`. Expected: FAIL.
- [ ] **Step 3: Implement.** The launcher never writes a value anywhere; `err` receives only names. Add `# nosec` with its reason where bandit flags `execve`.
- [ ] **Step 4: Run** common's CI row and `bandit`. Expected: PASS.
- [ ] **Step 5: Commit** `feat(loops): a launcher that gives a local MCP server only the variables the person allowed`.

### Task 4: claudeloop applies the snapshot (plugins, skills, settings sources, disallowed tools, folders)

**Files:**
- Create: `src/vibey_runners/claude/src/claudeloop/domain/capabilities.py`. It holds `AppliedCapabilities`, a frozen record, and `CLAUDE_BUILTIN_WEB_TOOLS: Final = ("WebSearch", "WebFetch")`, whose reason is written beside it: these are Claude Code's own tool names, a fact of its vocabulary and not a policy (R4).
- Modify: `src/vibey_runners/claude/src/claudeloop/domain/errors.py`. Add `CapabilitySnapshotRefused(AutoclaudeError)`, the tenant's existing base error, with `reason: str`.
- Create: `src/vibey_runners/claude/src/claudeloop/infrastructure/capabilities/__init__.py`, `infrastructure/capabilities/snapshot_applier.py` (`CapabilitySnapshotApplier`), `infrastructure/interfaces/capability_snapshot_applier_interface.py`
- Create: `infrastructure/agent/capability_overlay.py` (`CapabilityOptionsOverlay`), `infrastructure/interfaces/capability_options_overlay_interface.py`
- Modify: `infrastructure/agent/options.py`:
  - `build_turn_options` takes `applied: AppliedCapabilities | None = None` and calls the overlay.
  - The dead "marketplace name" branch of the plugin loop goes; both of its arms built the same value.
- Modify: `infrastructure/agent/gateway.py`. `ClaudeAgentGateway.__init__(..., applied: AppliedCapabilities | None = None)` holds the value for the session's life, and `_options()` passes it every time.
- Modify: `cli/commands/run.py`. Add the `--capabilities PATH` option. Exit 78 on `CapabilitySnapshotRefused`, exit 2 on an R12 conflict, and emit `capabilities.applied` into the run's events.
- Modify: `src/vibey_runners/claude/src/claudeloop/bootstrap.py`. `build_runner(..., capabilities: Path | None = None)` reads the document through the applier, checks R12, and hands `applied` to the gateway.
- Test: `src/vibey_runners/claude/tests/domain/test_capabilities.py`, `tests/infrastructure/test_snapshot_applier.py`, `tests/infrastructure/test_options_and_bus.py`, `tests/infrastructure/test_agent_gateway.py`, `tests/cli/test_run_cmd.py`

**Interfaces:**
- `@dataclass(frozen=True, slots=True) class AppliedCapabilities` has these fields:
  - `digest: str`
  - `plugin_dirs: tuple[str, ...]`
  - `skills: tuple[str, ...]`
  - `mcp_servers: Mapping[str, Mapping[str, object]]` (Task 5 fills it)
  - `disallowed_tools: tuple[str, ...]`
  - `add_dirs: tuple[str, ...]`
  - `system_prompt_append: str` (Task 6 fills it)
  - `notices: tuple[str, ...]`
- `CapabilitySnapshotApplier(store: SnapshotDocumentStoreInterface, *, local_backend: bool)` has `load(path: Path) -> AppliedCapabilities`. It raises `CapabilitySnapshotRefused` for any `SnapshotDocumentError` or `OSError`, with no value from the document in the message beyond its path. It sets `disallowed_tools = CLAUDE_BUILTIN_WEB_TOOLS` when `builtin_web` is false or `local_backend` is true (R11), and adds a notice in the latter case when `builtin_web` is true.
- `CapabilityOptionsOverlay.apply(kwargs: dict[str, Any], applied: AppliedCapabilities) -> dict[str, Any]` returns new kwargs:
  - `setting_sources = []`, `strict_mcp_config = True` (R5)
  - `plugins` = the snapshot's `{"type": "local", "path": p}` first, then the session's own
  - `skills` = the snapshot's qualified names plus the session's own (R6; `[]` when both are empty)
  - `mcp_servers` = the union, refusing a duplicate name with `ValueError` (R12)
  - `disallowed_tools` = `list(applied.disallowed_tools)`
  - `add_dirs` = the snapshot's plus the session's own
  - `allowed_tools` with every disallowed tool removed

  It never removes a snapshot entry.
- The events entry has kind `capabilities.applied` and payload `{"digest", "plugins": n, "skills": n, "mcp_servers": n, "disallowed_tools": [...], "instruction_files": [names inlined], "notices": [...]}`. It carries no env value and no file text.

- [ ] **Step 1: Write the failing tests.**
  - Applier:
    - `test_builtin_web_false_disallows_websearch_and_webfetch`
    - `test_a_local_backend_disallows_them_even_when_builtin_web_is_true_and_says_so`
    - `test_a_refused_document_raises_capability_snapshot_refused_naming_only_the_path`
  - Options:
    - `test_snapshot_options_set_empty_setting_sources_and_strict_mcp`
    - `test_the_cli_command_carries_empty_setting_sources_strict_mcp_and_the_disallow_list`. This builds `SubprocessCLITransport(prompt="", options=build_turn_options(cwd=..., applied=..., cli_path="/fake/claude"))._build_command()` and asserts that it contains `--setting-sources=`, `--strict-mcp-config`, `--disallowedTools` followed by `WebSearch,WebFetch`, and one `--plugin-dir <snapshot path>` per plugin. It is the last point before the child's argv. It reaches a private SDK method on purpose, pinned by `uv.lock` to 0.2.152, and a rename fails it loudly.
    - `test_skills_are_the_catalog_qualified_names_and_an_empty_catalog_is_skills_off`
    - `test_a_lane_with_nothing_named_is_not_narrowed`: the existing test, unchanged, for `applied=None`.
    - `test_websearch_is_never_both_allowed_and_disallowed`
  - Gateway: `test_a_mid_run_resource_change_keeps_every_snapshot_capability`. Calling `set_session_resources(plugins=[], skills=None, mcp_servers={}, add_dirs=[])` leaves every snapshot plugin, skill, server, folder and disallowed tool in `_options()`.
  - CLI:
    - `test_a_refused_document_exits_78_before_any_session`: the scripted agent is never called.
    - `test_web_search_with_builtin_web_off_exits_2`
    - `test_a_connector_named_like_a_snapshot_server_exits_2`
    - `test_capabilities_applied_is_in_the_runs_events_with_counts_only`
- [ ] **Step 2: Run** the four claudeloop rows (domain, application, infrastructure, cli). Expected: FAIL.
- [ ] **Step 3: Implement.** `bootstrap.py` stays a composition root and holds no logic beyond the wiring; it is coverage-omitted, so every decision lives in the applier, the overlay or `run.py`.
- [ ] **Step 4: Run** all four claudeloop rows at 100%, then `mypy --strict src/claudeloop`, `lint-imports` and `bandit -q -r src/claudeloop`. Expected: PASS.
- [ ] **Step 5: Commit** `feat(claudeloop): apply a locked capability snapshot and switch off the built-in web tools`.

### Task 5: claudeloop gives MCP servers an explicit transport, through the launcher

**Files:**
- Create: `src/vibey_runners/claude/src/claudeloop/domain/mcp_config.py` (`McpConfigTranslator`), `domain/interfaces/mcp_config_translator_interface.py`
- Modify: `infrastructure/capabilities/snapshot_applier.py` (fills `AppliedCapabilities.mcp_servers`), `bootstrap.py` (passes the launcher prefix `(sys.executable, "-m", LAUNCHER_MODULE)`)
- Test: `src/vibey_runners/claude/tests/domain/test_mcp_config.py`, `tests/infrastructure/test_snapshot_applier.py`, `tests/cli/test_run_cmd.py`

**Interfaces:**
- `McpConfigTranslator(launcher: tuple[str, ...])` has `translate(server: McpServerSpec) -> dict[str, object]`. It is pure: no environment, no clock.
  - `local` becomes `{"type": "stdio", "command": launcher[0], "args": [*launcher[1:], *("--allow", n for each n in env_allow), "--", *command]}`. It has no `env` key, ever.
  - `remote` becomes `{"type": "http", "url": url}`.
  - It raises `ValueError` for a spec that is neither, which the document reader has already ruled out.

- [ ] **Step 1: Write the failing tests.**
  - `test_a_local_server_is_stdio_through_the_launcher_with_no_env_key`
  - `test_a_remote_server_is_http_and_never_sse`
  - `test_every_server_has_an_explicit_type`
  - `test_no_env_value_reaches_argv_events_resources_or_logs`. A run with a sentinel in `os.environ[ALLOWED]` and the scripted agent checks four places: the sentinel is absent from `_options().mcp_servers` rendered as JSON, from `events.jsonl`, from every file under `resources/`, and from `caplog`/structlog output. The snapshot's servers are never written through `RunResourceStore.set_connector`.
  - `test_a_snapshot_server_is_not_exported_by_claudeloop_snapshot`
- [ ] **Step 2: Run** the claudeloop domain and infrastructure rows. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** all four claudeloop rows at 100%. Expected: PASS.
- [ ] **Step 5: Commit** `feat(claudeloop): MCP servers from the snapshot, typed and started with a scrubbed environment`.

### Task 6: claudeloop injects the repository's `CLAUDE.md` and `AGENTS.md` as text

**Files:**
- Create: `src/vibey_runners/claude/src/claudeloop/infrastructure/capabilities/instruction_files.py` (`InstructionFileReader`), `infrastructure/interfaces/instruction_file_reader_interface.py`
- Modify: `infrastructure/capabilities/snapshot_applier.py`. `load(path, cwd=...)` fills `system_prompt_append` and the event's `instruction_files`.
- Test: `src/vibey_runners/claude/tests/infrastructure/test_instruction_files.py`

**Interfaces:**
- `InstructionFileReader(reader: FileReaderInterface = BoundedFileReader())` has `read(cwd: Path, names: Sequence[str], max_bytes: int) -> InstructionText`.
- `InstructionText(text: str, inlined: tuple[str, ...], named: tuple[str, ...])` is a record.
- Each existing file becomes a block under the heading `## Repository instructions ({name})`, in `names` order. A file over `max_bytes` becomes one line instead: `{name} ({size} bytes) is longer than the [loops] instruction_max_bytes of {max_bytes}; read it from the repository before you start.` A symlink, a non-regular file or bytes that are not UTF-8 also become one named line, saying why. A missing file is skipped.
- The text follows the voice contract and the autonomy fragment, so the repository's rules never outrank them.

- [ ] **Step 1: Write the failing tests.**
  - `test_claude_md_and_agents_md_are_inlined_in_order`
  - `test_a_file_over_the_cap_is_named_never_truncated`: no prefix of its body appears.
  - `test_a_symlinked_claude_md_is_refused_and_named`
  - `test_a_missing_file_is_skipped_silently_and_counted_nowhere`
  - `test_the_repository_text_follows_the_voice_contract`
  - `test_a_nested_claude_md_is_not_read`: only `cwd/<name>`.
- [ ] **Step 2: Run.** Expected: FAIL. **Step 3: Implement.** **Step 4: Run** the claudeloop infrastructure row at 100%. Expected: PASS.
- [ ] **Step 5: Commit** `feat(claudeloop): the repository's CLAUDE.md and AGENTS.md as instruction text when settings are off`.

### Task 7: The `LoopCapabilitiesSnapshotted` ledger event

**Files:**
- Modify: `src/vibey/domain/ledger.py`. Add `EventKind.LOOP_CAPABILITIES_SNAPSHOTTED = "LoopCapabilitiesSnapshotted"` with a comment: the snapshot a run was given, recorded by vibey before the engine starts; digests and counts only.
- Create: `src/vibey/domain/loop_capabilities.py` (`LoopCapabilitiesRecord`), `src/vibey/domain/interfaces/loop_capabilities_interface.py`
- Modify: `src/vibey/domain/publication_policy.py` (the kind joins `WITHHELD_KINDS`: it describes the operator's own plugin and server configuration)
- Modify: `docs/plans/handoff-protocol.md` (the kind table, a row: `vibey`, no, `run_id`, `digest`, the counts; and the member count in the sentence after the table, which already lags the enum and is set to the true count), `docs/plans/domain-model.md` (the `EventKind` listing)
- Test: `tests/domain/test_loop_capabilities.py`, `tests/domain/test_ledger.py`, `tests/domain/test_publication_policy.py`, `tests/domain/test_noloss.py`, `tests/infrastructure/engines/test_loop_events.py`

**Interfaces:**
- `LoopCapabilitiesRecord.payload(*, run_id: UUID, digest: str, plugins: int, skills: int, skills_skipped: int, mcp_local: int, mcp_remote: int, notices: int) -> dict[str, object]`. It is pure. It raises `ValueError` for a digest not matching `^sha256:[0-9a-f]{64}$` or a negative count. The keys are exactly `run_id`, `digest`, `plugins`, `skills`, `skills_skipped`, `mcp_local`, `mcp_remote` and `project_notices`. Module instance: `LOOP_CAPABILITIES_RECORD: LoopCapabilitiesRecordInterface`.

- [ ] **Step 1: Write the failing tests.**
  - `test_the_payload_holds_only_the_digest_ids_and_counts`: the key set is pinned. A server's `command`, `url` and `env_allow` are never passed in, so they cannot appear.
  - `test_a_malformed_digest_or_negative_count_is_refused`
  - `test_the_kind_round_trips_through_the_parser` (`EventKindParser`)
  - `test_loop_capabilities_snapshotted_is_withheld_whole`, together with the existing every-kind-classified-once test.
  - `test_a_capabilities_snapshotted_event_in_the_range_trips_no_rule`: a BUILD range holding the event with the deterministic brief gives `verify(...).ok is True` under STRICT, and `rules_run == tuple(GateRule)`. `noloss.verify` is not touched.
  - `test_no_loop_event_type_maps_to_capabilities_snapshotted`: no value in `LOOP_EVENT_MAP` is the new kind, so an engine can never emit it.
- [ ] **Step 2: Run** `uv run pytest tests/domain tests/infrastructure/engines/test_loop_events.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement.** Add no database migration: the ledger stores the kind as text (`EventKindParser`), and no CHECK constraint lists kinds.
- [ ] **Step 4: Run** `uv run pytest tests/domain -q`, the `noloss` property suite at 10,000 examples as CI runs it, and the domain floor. Expected: PASS.
- [ ] **Step 5: Commit** `feat(ledger): LoopCapabilitiesSnapshotted, the snapshot a run was given`.

### Task 8: BUILD gives `claudeloop` and `claudeloop-local` the snapshot and records it

**Files:**
- Modify: `src/vibey/domain/engine.py`. Add `EngineDescriptor.capabilities_flag: str | None = None`: the runner's `run` flag that takes a capability document, checked against its `--help` by conformance.
- Modify: `src/vibey/application/dto.py`:
  - `RunSpec.capabilities_file: Path | None = None`
  - `PreparedCapabilities(document: Path, folder: Path, digest: str, plugins: int, skills: int, skills_skipped: int, mcp_local: int, mcp_remote: int, notices: tuple[str, ...])`
- Modify: `src/vibey/domain/job.py`. Add `LOOP_CAPABILITIES_GATE_KIND: Final = "loop_capabilities_unresolved"`.
- Modify: `src/vibey/cli/gate_answers.py`. Add `LOOP_CAPABILITIES_GATE_KIND: FREE_FORM`.
- Create: `src/vibey/application/loop_capabilities_service.py` (`LoopCapabilitiesService`), `src/vibey/application/interfaces/loop_capabilities_interface.py`
- Modify: `src/vibey/infrastructure/loops/snapshot_pruner.py` and its interface. Add `remove(folder: Path, snapshots: Path) -> bool`, which removes only a `run-*` folder directly in `snapshots`. It never follows a symlink and refuses anything else.
- Modify: `src/vibey/application/build_implement_handler.py`:
  - a constructor parameter `capabilities: LoopCapabilitiesInterface | None = None`;
  - prepare after the inputs are materialized;
  - record the event, then start the engine;
  - release in `finally`.
- Modify: `src/vibey/infrastructure/engines/argv.py` (`build_argv`), `src/vibey/application/conformance.py` (claimed flags include `capabilities_flag`), `src/vibey/infrastructure/engines/descriptors.py` (`CLAUDELOOP` and `ClaudeloopLocalDescriptors.build` set `capabilities_flag="--capabilities"`)
- Modify: `src/vibey/bootstrap.py`. `loop_capabilities_service()` composes the service from:
  - `loops_bundle_settings()`, `loops_marketplace_store(acp_user_config())`, `loops_resolver`, `SnapshotDocumentStore()`, `loops_snapshot_pruner()`;
  - the person's path `acp_user_config()`;
  - the run deadline from `_engine_run_deadline`.

  `_implement` passes `capabilities=`.
- Modify: `src/vibey/cli/main.py` (`worker`: one `sweep()` before `run_worker()` starts; a refusal is logged, never fatal)
- Test: `tests/application/test_loop_capabilities_service.py`, `tests/application/test_build_implement_capabilities.py`, `tests/infrastructure/engines/test_argv.py`, `tests/application/test_conformance.py`, `tests/infrastructure/loops/test_snapshot_pruner.py`, `tests/cli/test_gate_answers.py`, `tests/unit/test_bootstrap_loop_capabilities.py`

**Interfaces:**
- `LoopCapabilitiesInterface.prepare(*, project_config: Path | None, folders: Sequence[Path]) -> PreparedCapabilities`. It is synchronous; the handler calls it through `asyncio.to_thread`, as `RunInputsService` does. It loads the trusted bundle, with the worktree's `vibey.toml` as the only project input (narrowing). It resolves against the person's lock and roots, writes the document, and returns the counts. Project notices are logged, never recorded. It raises `CapabilityResolutionError`, `ConfigError` or `SnapshotDocumentError`.
- `LoopCapabilitiesInterface.release(prepared: PreparedCapabilities) -> None` calls `SnapshotPruner.remove`.
- `LoopCapabilitiesInterface.sweep() -> PruneReport` prunes with an age of `max(bundle.snapshot_max_age_days days, run_deadline + 1 hour)` (R10).
- `build_argv`: on a new session with `spec.capabilities_file` set, it appends `(descriptor.capabilities_flag, str(spec.capabilities_file))` after `launch_flags`. If the descriptor has no flag, it raises `ValueError`: a document is never dropped silently. A resumed session never carries it.
- The handler's order: worktree, provision, prompt, inputs, then:
  - `prepare`, but only when `self._engine.descriptor.capabilities_flag is not None`;
  - record `LoopCapabilitiesSnapshotted` (`engine_id` = the selected engine, `causation_id = run_id`);
  - `engine.start(RunSpec(..., capabilities_file=prepared.document))`.

  `release` runs in `finally`, whatever the outcome. A `CapabilityResolutionError`, `ConfigError` or `SnapshotDocumentError` returns `Park(HumanGateRequest(kind=LOOP_CAPABILITIES_GATE_KIND, prompt=...))`. The prompt names the error text; for an unlocked or changed marketplace that text already holds `vibey loops marketplace update <name>`. An `OSError` while writing returns `Failure(VIBEY)`, a retry.

- [ ] **Step 1: Write the failing tests.**
  - Service:
    - `test_prepare_writes_one_document_in_the_run_folder_and_returns_counts`
    - `test_a_projects_loops_table_can_only_narrow`: a project `disable = ["currency-research"]` gives 0 plugins, and a project `builtin_web = true` is ignored with a notice.
    - `test_release_removes_the_run_folder_and_nothing_else`
    - `test_sweep_never_uses_an_age_below_the_run_deadline`
  - Handler:
    - `test_the_event_is_recorded_before_the_engine_starts`: the fake ledger and fake engine share one ordered log.
    - `test_the_argv_carries_the_capabilities_flag_and_document`
    - `test_an_unresolvable_snapshot_parks_and_never_starts_the_engine`, for an unlocked marketplace and for a lock mismatch.
    - `test_a_bad_loops_table_parks`
    - `test_an_engine_without_the_flag_is_given_no_snapshot_and_no_event` (gptossloop, codexloop)
    - `test_the_snapshot_folder_is_removed_on_success_failure_and_wind_down`
    - `test_the_input_folder_is_in_the_documents_folders`
    - `test_a_wind_down_follow_up_is_given_a_fresh_snapshot_and_the_seed_is_unchanged`: `prompt.startswith(seed)` still holds, as in Phase 3c.
  - Argv:
    - `test_a_document_on_a_descriptor_without_the_flag_is_refused`
    - `test_a_resumed_session_never_carries_the_document`
  - Conformance: `test_capabilities_flag_is_checked_against_help`
  - Pruner: `test_remove_refuses_a_symlink_or_a_folder_outside_snapshots`
  - Gate answers: `test_loop_capabilities_unresolved_takes_a_free_form_answer`
- [ ] **Step 2: Run** `uv run pytest tests/application tests/infrastructure/engines tests/infrastructure/loops tests/cli/test_gate_answers.py tests/unit -q`. Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the full suite with the four layer floors at 100% (xdist, empty Missing column), and the PostgreSQL system test `tests/system/test_worker_run_inputs_wiring.py` to show that inputs and the snapshot coexist. Then run `uv run mypy --strict src/vibey`, `uv run lint-imports` and `uv run bandit -q -r src/vibey`. Expected: PASS.
- [ ] **Step 5: Commit** `feat(build): claudeloop runs are given the locked snapshot, and the ledger records it before they start`.

### Task 9: The descriptors tell the truth; the docs follow

**Files:**
- Modify: `src/vibey/infrastructure/engines/descriptors.py`:
  - In `CLAUDELOOP`, `launch_flags=()` (R4: `--web-search` and `--deep-research` go).
  - In `_CLAUDELOOP_AFFORDANCES`, `web_search=False`.
  - The evidence entries for `files`, `plugins`, `mcp`, `skills` and `web_search` are rewritten to cite the new code: `--capabilities` in `cli/commands/run.py`; `CapabilityOptionsOverlay` (`setting_sources=[]`, `--plugin-dir`, `skills`); `McpConfigTranslator` (`"type": "stdio"` / `"http"`); `CLAUDE_BUILTIN_WEB_TOOLS`; the attachments folder in `gateway_payload`.
  - `claudeloop-local`'s `web_search` evidence adds R11.
- Modify: `tests/meta/loop_runner_facts.py`:
  - one `RunnerFact` per claim, with literal needles: `"--capabilities"`, `'"setting_sources": []'` or the overlay's literal, `'"type": "stdio"'`, `'"type": "http"'`, `"attachments_dir"`;
  - the `web_search` fact for claudeloop goes.
- Modify: the golden files under `tests/infrastructure/engines/golden/` (claudeloop and claudeloop-local argv) and the `vibey loops --json` golden.
- Modify: `docs/reference/cli.md`:
  - the per-loop capability table: claudeloop web search is off by default (`[loops] builtin_web`); MCP is typed; skills and plugins come from the snapshot;
  - `vibey worker`'s snapshot sweep;
  - the `loop_capabilities_unresolved` gate.
- Modify: `docs/reference/configuration.md`. In `[loops]`:
  - the four R13 keys with their defaults;
  - the closing paragraph "Nothing yet changes how a loop runs" is replaced by what Phase 4 applies and to which loops;
  - `[engine_environment]` gains a line saying an MCP server's `env_allow` variable reaches the session only if it is passed through there.
- Modify: `src/vibey_runners/claude/docs/reference/cli.md` (the `run` reference for `--capabilities`), `src/vibey_runners/claude/CHANGELOG.md` ([Unreleased]: `--capabilities`, the `--attach` fix), `changelog.d/sp-loops-phase4-claudeloop.feature.md`, `changelog.d/claudeloop-attach-reaches-agent.fix.md`
- Modify: `docs/architecture/decisions/0103-the-loop-capability-bundle.md`. Its status is unchanged. Add a "Phase 4" section recording R1 to R14, and close the two Consequences items it left to Phase 4: end-of-run removal and the sweep (R10); loading only from the snapshot's plugin folders (R5).
- Test: `tests/meta/test_loop_capability_evidence.py`, `tests/meta/test_cli_doc_capabilities.py`, `tests/infrastructure/engines/test_descriptors.py`, `tests/infrastructure/engines/test_argv.py`, `tests/cli/test_loops_cli.py`

- [ ] **Step 1: Write the failing tests.**
  - `test_claudeloop_claims_no_web_search_while_builtin_web_is_off_by_default`
  - `test_every_true_claim_has_a_matching_runner_fact`, the existing test, now over the new facts.
  - `test_claudeloop_and_claudeloop_local_share_every_snapshot_fact`: the facts for both loops name the same file and needle.
  - `test_launch_flags_no_longer_carry_web_search` (this replaces the `--web-search` assertions in `test_argv.py` around lines 227 to 278).
  - `test_the_cli_doc_names_builtin_web_and_the_capabilities_flag`
- [ ] **Step 2: Run** `uv run pytest tests/meta tests/infrastructure/engines tests/cli/test_loops_cli.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement.** The argv goldens have no regeneration switch (`test_argv.py::test_argv_matches_golden_file` compares `shlex.join(build_argv(...))` with each file). Rewrite each claudeloop and claudeloop-local golden to exactly that output, and say in the commit body that the only change is the two dropped flags.
- [ ] **Step 4: Run** `uv run vibey-gh corpus-index --check`, the strict docs build, `uv run pytest tests/meta -q` and the full layer floors. Expected: PASS. Every advertised count is unchanged: no new ADR.
- [ ] **Step 5: Commit** `docs(loops): descriptors, evidence and references for claudeloop's snapshot`.

## Verification (the phase is done when all of these hold)

- `uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=` passes, and the four layer floors are 100% with an empty Missing column. claudeloop's four CI rows and common's row pass at 100%. `mypy --strict`, `lint-imports` and `bandit` are clean for `src/vibey`, `src/claudeloop` and `src/vibey_runners/common`. `uv run ruff check .`, `uv run ruff format --check .` and `uv run vibey-gh corpus-index --check` are clean.
- The `noloss` property suite passes at 10,000 examples with `domain/noloss.py` unchanged (`git diff origin/develop -- src/vibey/domain/noloss.py` is empty).
- **Operator-run real-run probe (unverified until the operator runs it).**
  1. In your own `vibey.toml`, add a local MCP server with `vibey loops mcp add probe --local -- <a small stdio MCP server that exposes one tool>`, and keep the default `currency-research` plugin.
  2. `vibey inputs add <project> --paste "PROBE-PASTE-<random>"`, then start one BUILD job with `claudeloop` pinned.
  3. Confirm all of the following in one run:
     - The run's `.claudeloop/runs/<id>/events.jsonl` system-init message lists `currency-research:research-search-and-source-quality` among skills and an `mcp__probe__<tool>` tool, and does not list `WebSearch` or `WebFetch`.
     - The plan or transcript shows `PROBE-PASTE-<random>`.
     - The ledger holds one `LoopCapabilitiesSnapshotted` before the run's `SessionSeeded`, and its `digest` equals `vibey loops skills list --json`'s `digest` (with no project `[loops]`).
     - After the job settles, `<config>/loops/snapshots/` holds no folder for that run.
  4. Repeat steps 2 and 3 with `claudeloop-local` switched on (`[features] claudeloop_local = true`) and pinned. The same three things appear, and `WebFetch` is absent even with `builtin_web = true`.
  5. Record the outcome in the PR. Until then, the descriptor evidence says "unit-proven; real-run probe pending".
- Not verified while writing this plan:
  - Whether `--strict-mcp-config` also suppresses MCP servers a plugin declares in its own `.mcp.json`. The probe shows it either way. If it does not suppress them, a plugin's own servers load from the locked snapshot, which Decision 3 accepts as instruction-level config.
  - Whether Claude Code accepts an empty `--setting-sources=`. The SDK documents `[]` as isolation mode.
  - Whether `claude` resolves `plugin:skill` names for `--plugin-dir` plugins without settings sources.

## Self-review

1. **Spec coverage, by the parent's Phase 4 task list:**

   | Parent item | Where |
   |---|---|
   | Plugins as local directories | Task 4, the overlay's `plugins` |
   | MCP with an explicit transport | Task 5 |
   | Skills by name | Task 4, R6 |
   | `setting_sources=[]` | Task 4, R5 |
   | `CLAUDE.md` and `AGENTS.md` as text | Task 6 |
   | Attachments in the agent's folders | Task 1 (claudeloop's own), Task 8 (the run's input folder through the document) |
   | `WebSearch` and `WebFetch` disallowed | Task 4, R4 |
   | `--attach` fixed | Task 1 |
   | Ledger event at job start | Tasks 7 and 8 |
   | Evidence entries | Task 9 |
   | Real-run probe | Verification, operator-run |

   Decision 9 (a scrubbed environment) is Task 3. ADR-0103's two Phase 4 consequences are Task 8 (R10) and Task 9.
2. **Type consistency.**
   - The `BundleSpec` R13 fields (Task 2) feed `SnapshotDocument.of`.
   - `CapabilitySnapshot.folder` (Task 2) is where `SnapshotDocumentStore.write` puts the document and what `LoopCapabilitiesService.release` removes (Task 8).
   - `SnapshotDocument` (Task 2) is read by `CapabilitySnapshotApplier` (Task 4), which builds `AppliedCapabilities`. Task 5 fills its `mcp_servers` through `McpConfigTranslator`, using `LAUNCHER_MODULE` (Task 3). Task 6 fills its `system_prompt_append` through `InstructionFileReader`.
   - `PreparedCapabilities` (Task 8) supplies `LoopCapabilitiesRecord.payload`'s arguments (Task 7).
   - `EngineDescriptor.capabilities_flag` and `RunSpec.capabilities_file` (Task 8) meet in `build_argv`.
3. **Points where the repository disagrees with the parent plan or the brief, and what this plan does:**
   - The parent lists no end-of-run removal or live marker. `snapshot_pruner.py`'s docstring and ADR-0103's Consequences both assign them to Phase 4, so Task 8 carries them (R10).
   - `CLAUDELOOP.launch_flags` passes `--web-search` and `--deep-research` (`descriptors.py` line 149), and its evidence says vibey always passes them. That contradicts Decision 2 as Phase 4 applies it. Task 9 removes them.
   - The resolver makes a run folder only when a plugin is enabled (`resolver.py` `_run_folder`, called inside the marketplace loop), so there was nowhere to put a document for a bundle with no plugins. Task 2 changes that.
   - `BoundedProcessRunner` lives in `src/vibey/infrastructure/loops/bounded_process_runner.py`, not in the common capabilities package. This plan does not need it.
4. **Left to the builder:** private helper names, the exact JSON key order inside the document (it is canonical, sorted), the wording of notices other than those pinned above, and where in `run.py` the R12 checks sit.
