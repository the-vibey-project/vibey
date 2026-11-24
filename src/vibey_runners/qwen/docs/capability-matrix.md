# Capability matrix

The runner — `gptossloop` and `qwenloop` alike, one Typer application under two
names (vibey ADR-0064) — exposes the literal top-level command union of claudeloop, codexloop,
and the two paid runners vibey ADR-0078 later retired. Core lifecycle, control, model, server, doctor,
identity, and usage commands have native local behavior. Vendor account,
cloud, resource, speech, and generated API families are local equivalents and
never call the original vendors. Each command is registered through the same
Typer application and is covered by the CLI command-presence contract test.

## What a run can use

vibey reports the runner's plugin system as `vibey-bundle` (vibey ADR-0092, amended
2026-11-25; ADR-0103, Phase 5). A BUILD run is started with `run --capabilities PATH`, the
capability document of the person's locked snapshot.

| Capability | With `--capabilities` | Without |
|---|---|---|
| Skills and plugin commands | Listed by name and description in the system prompt within `[loops] capability_prompt_tokens` (falling back to names, then to a count, and saying so); bodies read through `skills_list` and `skill_read`, a page at a time within `[loops] capability_answer_tokens` | None |
| Instruction files | `[loops] instruction_files` (`CLAUDE.md`, `AGENTS.md`) from the run's folder, in the system prompt within the same budget; a file that does not fit is named with its size, never cut | None |
| MCP servers | Exactly the snapshot's, through `mcp_list` and `mcp_call`: a `local` server over stdio through the scrubbed launcher, a `remote` server over streamable HTTP; one persistent session per server for the run, started on first use and closed when the run ends | The stdio servers in `~/.claude.json` and `QWENLOOP_MCP_CONFIG`, through the same two tools and the same persistent sessions |
| MCP limits | The config file's `[mcp]` table: `request_timeout_seconds`, `restarts`, `close_grace_seconds`, `remote_calls_per_session`, `max_tools` | The same table |
| Plugin hooks and agents | None: no runtime exists for them outside Claude Code | None |

The worktree's `.mcp.json` is never read. Every MCP failure is a tool error the model reads,
never the end of the run, and MCP output is always untrusted data. A document the runner
refuses or cannot read exits `78` before any model is started or called.

