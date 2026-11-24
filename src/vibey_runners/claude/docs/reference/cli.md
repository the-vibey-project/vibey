# CLI reference

`src/claudeloop/cli/app.py` is the real Typer root; every command below
works today. Top-level `claudeloop --help` / `--man` renders a Unix-style
manual page from `cli/man_page.py`. Subcommands use Typer's usual
`--help` for flag details.

## Command tree

```
claudeloop --version                 Show version and exit
claudeloop --help | --man            Manual-page overview (NAME, SYNOPSIS, …)

claudeloop run <plan-file>           New session from a markdown plan → drive to completion
                                       --cwd --attach --add-folder --from-github --import-issue
                                       --skill --plugin --connector --web-search --deep-research
                                       --capabilities
                                       --permission-mode --slash
                                       --max-turns --max-dollars --max-wait
                                       --model --effort --preset --auto-model/--no-auto-model
                                       --continue-prompt --done-marker
                                       --max-buffer-size --log-level --log-file --log-chatter
                                       --stream-ui

claudeloop resume [--session-id]     Resume a session (or auto-select most recent for cwd)
                                       (same budget / model / effort / preset / log flags as run)

claudeloop stop [--run-id]           Soft-stop → stop-summary.md, exit 130

claudeloop prompt (--now|--at-break) TEXT [--run-id]
                                     Inject a prompt (immediate next turn, or at Continue)

claudeloop model MODEL [--run-id]    Queue mid-run model (alias or raw id)
claudeloop effort LEVEL [--run-id]   Queue mid-run effort
claudeloop preset NAME [--run-id]    Queue mid-run preset low|medium|high
claudeloop permission-mode MODE      Mid-run permission mode (bypass|manual|…)
claudeloop cwd DIR                   Mid-run working directory
claudeloop slash /CMD …              Validated slash-command inject
claudeloop tool approve|deny ID      Manual-mode tool decisions
claudeloop attach|unattach …         Run attachments
claudeloop folder|skill|plugin|connector|github|research|web-search …
claudeloop memory|artifact …        Native memories / artifacts CRUD
claudeloop chat …                   Session metadata (pin/share/…)
claudeloop response copy|good|bad|retry
claudeloop voice|speak …            Optional TTS/STT extras

claudeloop logs [--run-id] [-f|--follow] [--chatter]
                                     Tail redacted events.jsonl (optionally chatter only)

claudeloop status [--run-id]         Print status.json snapshot fields
claudeloop snapshot [--run-id] [--out PATH] [--bundle|--no-bundle]
                                     Write handoff snapshot under runs/<id>/snapshots/
                                     (publishes path+digest on the state bus)
claudeloop runs                      List .claudeloop/runs/*
claudeloop savepoints [--run-id]     List git save points for a run
claudeloop unwind --to N [--backup|--no-backup] [--run-id]
                                     Reset worktree to save point (refuse if run still active)
claudeloop reset --yes               Delete project `.claudeloop/` (refuse if a run is live)
claudeloop watch [--run-id] [--follow] [--stream] [--replay] [--speed N]
                                     Follow bus.jsonl, or Textual token stream live/replay

claudeloop sessions [--cwd]          List known Claude Code sessions (read-only)
claudeloop doctor                    Pre-flight checks
claudeloop api ...                   Generated 1:1 Anthropic SDK REST commands
```

See also [`../guides/run-resources-and-chat-ops.md`](../guides/run-resources-and-chat-ops.md).


## `run --capabilities PATH`

The run's locked capability snapshot, a JSON document vibey's conductor writes into the run's
own snapshot folder before a BUILD run starts (SP-LOOPS Phase 4). It is read strictly, before
any run folder exists, and the session then holds it for its whole life:

| What | How it is applied |
|---|---|
| Claude settings | None: `setting_sources=[]` and `strict_mcp_config=True`, so no user, project or local setting, and no MCP server it declares, loads. |
| Plugins | The snapshot's plugin folders, each a local plugin (`--plugin-dir`). `--plugin` adds to them. |
| Skills | Exactly the catalog's skills, by qualified name (`plugin:skill`). `--skill` adds to them. |
| MCP servers | A local server is `"type": "stdio"`, started through a launcher that keeps only the variables its `env_allow` names (a name the session does not have is skipped, and that name is logged, never a value); a remote server is `"type": "http"`, never `sse`. `--connector` adds to them. |
| Folders | The run's input folders, then `--add-folder`. |
| Web tools | `WebSearch` and `WebFetch` are disallowed unless the snapshot's `builtin_web` is true. On a local backend they are always disallowed, and a notice says so. |
| Instruction files | The snapshot's `instruction_files` (by default `CLAUDE.md` and `AGENTS.md`), read from `--cwd` only and appended to the system prompt, never to the plan. A file over `instruction_max_bytes` is named with its size, never cut; a symlink is refused. |

It is applied on every connect, so a mid-run `attach`, `folder`, `skill`, `plugin` or
`connector` adds to it and never drops it. The `capabilities.applied` event carries the digest,
counts and names only. A document that is refused or cannot be read exits `78`. `--connector`
with a name the snapshot already gives, or `--web-search` beside a snapshot that switches the
web tools off, exits `2`. A mid-run `connector add` with such a name also exits `2`, before
anything is queued, and the run continues unchanged. Without `--capabilities` nothing changes: the session loads Claude
Code's own settings as before.


## Mid-run operator control

`run` / `resume` are foreground processes. A second terminal targets the same
cwd (or an explicit `--run-id`):

| Command | Effect |
|---|---|
| `stop` | Soft stop; writes `stop-summary.md` |
| `prompt --now` | Next turn uses this text |
| `prompt --at-break` | Applied after a Continue verdict |
| `permission-mode` / `cwd` / `slash` | Session options + slash inject |
| `attach` / `folder` / `skill` / … | Resource CRUD |
| `tool approve|deny` | Manual permission approvals |
| `response retry|good|bad|copy` | Last-turn actions |
| `logs -f` | Follow `events.jsonl` |
| `status` / `runs` | Poll live status |
| `snapshot` | Write handoff JSON (+ optional bundle); bus publishes digest |
| `savepoints` / `unwind` | List / restore git save points |
| `reset --yes` | Wipe `.claudeloop/` when no live run |
| `watch` | Follow `bus.jsonl` or stream UI |
| `savepoints` / `unwind` | Git refs under `refs/claudeloop/…` (commit only when the tree changed after excluding `.claudeloop/`; unchanged trees are ref-tagged only; subjects use `chore(claudeloop): turn N — …`) |

Control plane layout: `.claudeloop/runs/<run_id>/` (`meta.json`, `inbox/`,
`events.jsonl`, `audit.jsonl`, `status.json`, `bus.jsonl`,
`savepoints.jsonl`, `stop-summary.md`, `resources/`, `memories/`,
`artifacts/`).

See [`../guides/autonomous-runs.md`](../guides/autonomous-runs.md) and
[`../guides/run-resources-and-chat-ops.md`](../guides/run-resources-and-chat-ops.md).


## Exit codes

| Code | Meaning |
|---|---|
| `0` | Done verdict (run/resume), or inspection/doctor success |
| `1` | Failed run (blocked, budget, max-wait, auth, …) or doctor check failed |
| `2` | Usage error (e.g. `prompt` without exactly one timing flag), or a flag that clashes with the `--capabilities` snapshot |
| `78` | The run could not start as configured: its `--capabilities` document was refused or could not be read, or the backend cannot serve it |
| `130` | Soft-stopped by `claudeloop stop` |

Full terminal-state semantics:
[`../architecture/run-loop-state-machine.md`](../architecture/run-loop-state-machine.md#states).

## Large tool results (SDK buffer)

Default `--max-buffer-size` is **50 MiB**. The Agent SDK's 1 MiB default
raises `JSON message exceeded maximum buffer size of 1048576 bytes` on large
tool outputs. Also settable via `CLAUDELOOP_MAX_BUFFER_SIZE`.

## Logging transports

`run` / `resume` always emit **dual console** logs on stderr (human + JSON
lines with `"transport": "console_json"`), optional `--log-file`, plus
per-run `events.jsonl` / `audit.jsonl`. Full matrix:
[`../guides/logging-and-observability.md`](../guides/logging-and-observability.md).

## Configuration

Every flag has env / `claudeloop.toml` equivalents — see
[`../getting-started/configuration.md`](../getting-started/configuration.md).

Worked examples: [`../getting-started/quickstart.md`](../getting-started/quickstart.md).
Live / system harness: [`../guides/live-testing.md`](../guides/live-testing.md).
