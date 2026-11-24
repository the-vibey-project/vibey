---
description: "Reference for vibey-runners-common, the stdlib-only code shared by vibey, its runners and vibey-gh: the loop capability bundle, JSON-RPC, the MCP client and the run ports."
---

# vibey-runners-common: the code every loop shares

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** This package holds the code that more than one member of the
> family needs, with no third-party dependency: the loop capability bundle (ADR-0103), a JSON-RPC
> 2.0 peer, an MCP client, the shared run ports, and the memory probe. vibey, claudeloop,
> codexloop, the local runner (`gptossloop`/`qwenloop`) and vibey-gh all import it. It ships inside
> `vibey-engine`; there is nothing to install or run on its own. Read it when you change how a
> loop is given plugins, skills or MCP servers.

## How to read this page

Daniel found the package while tracing where a skill reached a running model.

**Daniel:** Professor, nobody runs this. Why does it have a page?

**Professor Feynman:** Think of a shared workshop in a row of houses. Nobody lives there, but
every house borrows its tools, so the tools must be kept in one place and labelled. Each section
below is one shelf: what is on it, who borrows it, and the file that proves it.

## Who uses it

| Importer | Files that import it | For |
|---|---|---|
| vibey (`src/vibey`) | 20 | The capability bundle and the marketplace lock, mostly through their interfaces; the JSON-RPC codec and error vocabulary behind `vibey mcp` and `vibey acp`; the MCP protocol versions. |
| claudeloop | 8 | The shared run ports; reading a run's capability document; instruction files; the scrubbed MCP launch. |
| local runner (`qwenloop`, `gptossloop`) | 6 | The capability document, the skill shelf, and the MCP client. |
| codexloop | 3 | The shared run ports. |
| vibey-gh | 1 (`fit.py`) | The memory probe, for `vibey-gh fit`. |

The counts are `grep -rl vibey_runners.common` over each tree's Python files. Only the protocols
and use cases that genuinely converge across the family live here. Each runner still owns its own
domain layer, its own vendor-specific concrete implementations (in `infrastructure/`), and any
interface or use case whose actual shape diverges enough between runners that forcing a shared
version would misrepresent one of them — those stay local to the runner that needs them.

The package imports nothing outside the standard library (`dependencies = []`). That is why
vibey's pure `domain/` and `application/` layers may import parts of it (ADR-0017), and why
`import-linter` holds two contracts here: shared code depends on no concrete runner, and
interfaces declare seams but never consume them.

## `capabilities/`: the loop capability bundle

The largest subpackage (52 modules). It is the code of ADR-0103: what every loop is given
(marketplaces, plugins, MCP servers, skills) is declared by the person, locked by content, and
fetched only on the person's word. `vibey loops marketplace|plugin|mcp|skills|snapshots` is the
command line over it.

| Module | What it does |
|---|---|
| `bundle.py` | Reads the `[loops]` table strictly into a bundle. |
| `defaults.py` | What a bundle holds when the person has said nothing: the `vibey` marketplace that ships in the wheel (a reserved name a person-added marketplace may not take) and the `currency-research` plugin. |
| `manifest.py` | Reads a marketplace's `.claude-plugin/marketplace.json` without leaving the marketplace. |
| `marketplace_catalog.py` | What one marketplace offers, and every plugin it lists that cannot be used here, with the reason. |
| `lock.py`, `sidecar_lock.py` | The marketplace lock (what each tree hashed to when the person locked it), and the exclusive file lock held while it is changed. |
| `resolver.py` | Turns a bundle into a locked, run-scoped snapshot. |
| `snapshot.py`, `snapshot_copier.py` | What one run is given, and the copy of locked marketplace content into the run's own folder. |
| `snapshot_document.py`, `snapshot_document_store.py` | The `capabilities.json` the conductor writes into the run's folder and a runner reads back with `--capabilities PATH`. |
| `skill_index.py`, `plugin_command_index.py` | Index a set of plugins' `skills/*/SKILL.md` and `commands/*.md`. |
| `skill_shelf.py` | A run's skill shelf: what a loop may read on demand (`skills_list`, `skill_read` in the local runner). |
| `instruction_files.py` | The repository's `CLAUDE.md` and `AGENTS.md` as instruction text, read the same way by every loop given a snapshot. |
| `token_estimate.py` | The one token estimate that `[loops] capability_prompt_tokens` and `capability_answer_tokens` are measured in. |
| `scrubbed_launch.py`, `scrubbed_exec.py` | The argv that starts a `local` MCP server, and the launcher that starts it with only the environment variables the person allowed. claudeloop's MCP config uses it too. |
| `git_folder_guard.py` | Decides which entry is a marketplace's own `.git`, by file identity. |

The rest are small records and their errors (`*_entry.py`, `*_spec.py`, `*_error.py`), each with
its interface under `capabilities/interfaces/`.

## `jsonrpc/`

A stdlib JSON-RPC 2.0 implementation: the line codec (`codec.py`,
`JsonRpcCodec` and its `CODEC` singleton), the error vocabulary
(`errors.py`: the standard codes, `RpcError`, `PeerClosed`,
`PeerCancelled`) and a bidirectional asyncio peer (`peer.py`,
`JsonRpcPeer`), each with its interface under `jsonrpc/interfaces/`.

It is shared because more than one speaker of the wire format lives in the
family: vibey's MCP server (`vibey mcp`) and its Agent Client Protocol agent
(`vibey acp`), and the local runner's MCP client (SP-LOOPS Phase 5). One
implementation keeps their bytes from drifting apart; vibey holds no copy of
its own (`tests/meta/test_one_jsonrpc_peer.py`). vibey's application layer may
import `errors` (ADR-0017), and the package's `__init__.py` is empty so that
doing so pulls in no `asyncio`.

## `mcp/`

A stdlib MCP client over that peer (SP-LOOPS Phase 5). `McpSession` speaks
MCP to one server through a transport; `StdioTransport` starts a `local`
server as a child that leads its own process group, and closing it closes
the server's stdin, waits a grace period, then kills the whole group.
`HttpTransport` reaches a `remote` server over MCP's streamable HTTP
transport, through `HttpOpener`: https only, no redirect followed, no
cookie, credential, environment proxy or environment value sent, and a
bounded reply. `McpTransportFactory` picks the transport for a configured
server. `McpSessionPool` holds one session per server for a run: it starts each on
first use, restarts a dead one a bounded number of times, keeps each remote
server's call budget, and closes them all when the run ends without ever
raising. `protocol.py` holds the protocol versions, which vibey's own MCP
server imports, so both ends speak from one list. A `local` server's argv
comes from `capabilities/scrubbed_launch.py` (`ScrubbedLaunch`).

## `application/` and `infrastructure/`

- `application/interfaces/` holds the run ports the runners share (`api`, `control`,
  `observability`, `storage`, `system`, `ui`); `application/usecases/completion.py` wraps a prompt
  with the done-marker instruction used to detect task completion across turns.
- `infrastructure/memory_probe.py` is the family's one reading of how much physical memory the
  machine has. vibey-gh's fit calculus uses it.

## Tests and gates

The CI `tools` job runs this package on Python 3.12, 3.13 and 3.14, from this directory:

```bash
pip install -e ".[dev]"
mypy --strict src/vibey_runners/common && lint-imports
python -m pytest -q -p no:cacheprovider --cov=vibey_runners.common.infrastructure \
  --cov=vibey_runners.common.capabilities --cov=vibey_runners.common.jsonrpc \
  --cov=vibey_runners.common.mcp --cov-branch --cov-report=term-missing --cov-fail-under=100
```

`infrastructure`, `capabilities`, `jsonrpc` and `mcp` are held to 100% line and branch coverage.

## Where next

- [ADR-0103](../../../docs/architecture/decisions/0103-the-loop-capability-bundle.md): the loop
  capability bundle this package implements.
- [The local runner's README](../qwen/README.md): how a run uses the skill shelf and the MCP
  client.
- [ADR-0017](../../../docs/architecture/decisions/0017-dogfood-the-family-first.md): why the
  family uses this code rather than writing its own.

## Say it in one line

vibey-runners-common is the stdlib-only workshop every vibey loop borrows from: the capability
bundle, JSON-RPC, the MCP client and the shared run ports.
