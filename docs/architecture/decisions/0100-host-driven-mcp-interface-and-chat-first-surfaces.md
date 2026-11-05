# 0100 — Host-driven MCP interface and chat-first krypton surfaces

**Status:** proposed · **Date:** 2026-11-04 · **Cites:** SD-01 v1.0; proposed sub-doctrine 12.p; sub-doctrines 8.b, 9.b, 9.e, 9.f, 10.c, 10.f, 12.c, 12.d, 12.k · **Related:** ADR-0009, ADR-0016, ADR-0023, ADR-0065, ADR-0067, ADR-0068, ADR-0071, ADR-0073, ADR-0088, ADR-0091

**Owes:** the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md`
and `docs/index.md` (`tests/meta/test_adr_counts.py`), a nav entry in `properdocs.yml`,
and a fragment in `changelog.d/`. All are included in the change that carries this record.

## Context

Developers and operators already live inside frontier LLM chat and IDE interfaces —
Claude Code, Codex, Claude Desktop, Cursor, VS Code, and Gemini CLI — or expect a
conversational workspace when they open a dedicated desktop, mobile, or web client. Asking
an operator to leave their active chat session to memorise CLI flags or click through
status tabs works against the grain of how agentic software is operated (the REA pattern:
plugging the orchestration engine directly into the frontier LLM interface the user
already has open).

At the same time, two architectural constraints from ADR-0068 and SD-01 bind every client:

1. **One command core, many skins.** Every client — CLI, MCP server, desktop app, mobile
   and web app, and VS Code extension — talks to the same hub contract (`/api/v1`).
2. **A host LLM is not the operator.** If a frontier model connected over MCP held the
   hub's `host` token (`<state_dir>/token`), a prompt injection inside a ledger event or
   issue body could cause the model to answer a `budget_exhausted` or `deploy_*` gate and
   authorize real money or real cloud infrastructure without the human's consent.

## Decision

### 1. Scoped `agent` principal on the hub (never `spend`)

- `src/vibey/domain/hub_scope.py` defines `AGENT_DEFAULT_SCOPES = frozenset({HubScope.VIEW,
  HubScope.ANSWER, HubScope.RUN})`. It never includes `spend`, `bump`, or `workflows`.
- `LocalTokenStore.agent_token()` provisions `<state_dir>/agent.token` with the same
  `0600`, no-symlink, owner-only checks as `<state_dir>/token`.
- `AgentTokenAuthenticator` authenticates `Authorization: Bearer <agent.token>` using
  `vibey_bootstrap.security.compare_secrets` and yields `HubPrincipal(name="agent",
  scopes=settings.agent_scopes)`.
- `[hub] agent_scopes` in `vibey.toml` configures the ceiling (`["view", "answer", "run"]`
  by default; `[]` disables agent access completely). Because the hub enforces scopes per
  route and per gate kind, a host LLM cannot answer a spending gate (`budget_exhausted`,
  `deploy_*`) even if instructed to do so.

### 2. `vibey mcp`, `vibey connect`, and the `vibey-chat-driver` skill

- **`vibey mcp`** (`src/vibey/infrastructure/mcp/stdio_server.py`,
  `src/vibey/infrastructure/mcp/hub_gateway.py`, `src/vibey/domain/host_tools.py`) is a
  dependency-free JSON-RPC 2.0 stdio MCP server exposing 14 tools (`vibey_projects`,
  `vibey_status`, `vibey_gates`, `vibey_answer_gate`, `vibey_budget`, `vibey_queue`,
  `vibey_ledger`, `vibey_loops`, `vibey_lanes`, `vibey_doctor`, `vibey_start_project`,
  `vibey_start_work`, `vibey_pause_work`, and `vibey_abandon_project` with
  `dry_run=True` by default). It authenticates with `agent.token` and auto-starts the hub
  via `vibey hub start` if needed. Its `instructions` field (`HOST_INSTRUCTIONS`) binds
  the host model: tool outputs are untrusted data (SD-01 §4), spending gates belong to the
  human operator, and destructive actions require a dry run and explicit confirmation.
- **`vibey connect`** (`src/vibey/domain/host_clients.py`,
  `src/vibey/infrastructure/mcp/host_installer.py`, `src/vibey/cli/connect.py`) plans and
  applies idempotent MCP server registrations across `claude_code`, `claude_desktop`,
  `codex`, `cursor`, `vscode`, and `gemini_cli`, creating `.vibey.bak` backups before
  updating existing files and supporting `--dry-run`, `--yes`, and `--list`.
- **Plugin and skill packaging:** `src/vibey_tools/skills/plugins/vibey/` packages the
  `.mcp.json` entry and the `vibey-chat-driver` skill, mirrored across `.claude/skills/`,
  `.agents/skills/`, `.cursor/rules/`, and `.agent/rules/`.

### 3. Shared hub chat route (`POST /api/v1/chat/messages`)

- `HubChatPlanner` (`src/vibey/domain/hub_chat.py`) deterministically parses conversational
  turns and slash commands (`/help`, `/status`, `/gates`, `/answer`, `/new`, `/start`,
  `/pause`, `/resume`, `/abandon`, `/budget`, `/queue`, `/ledger`, `/loops`, `/doctor`)
  into structured `ChatPlan` values.
- `HubService.chat()` (`src/vibey/application/hub/hub_service.py`) executes those plans
  through the existing hub use-case methods, enforcing the caller's `HubPrincipal` scopes,
  and returns a `ChatResponse` containing the assistant reply, structured `tool_calls`
  cards, open `gates` cards (with `requires_spend` badged), and active project summary.
- Exposed at `POST /api/v1/chat/messages` in `src/vibey/infrastructure/hub/app.py` and
  committed in `docs/reference/hub-api.json`.

### 4. Chat-first krypton clients across desktop, mobile, web, and VS Code

- **krypton desktop (`clients/desktop`, C17 / GTK4 / libadwaita):** `kr-chat.h`/`kr-chat.c`
  in the pure-C core and `kr-chat-page.h`/`kr-chat-page.c` in the GTK view make `Chat`
  (`PAGE_CHAT`, `Ctrl+L`) the first view and default landing workspace, mirroring the
  Claude Code and Codex desktop layout: a left session sidebar of projects with phase and
  waiting-gate badges, a central scrollable transcript of user/assistant turns, collapsible
  tool-call cards, inline gate approval cards with `spend` gates badged, live ledger event
  narration, and a bottom composer with `/` slash-command completion.
- **krypton mobile & web (`clients/app`, Expo / React Native / TypeScript):**
  `clients/app/src/core/chat.ts` (+ `interfaces/chat-interface.ts` at 100% test coverage)
  and `clients/app/src/screens/chat.tsx` make `Chat` the landing tab (`/`), with project
  session chips, transcript bubbles, tool-call cards, inline gate approval cards, and `/`
  command completion, while keeping the Projects dashboard on `/projects`.
- **krypton for VS Code (`clients/vscode`, TypeScript) & `@vibey/core`:** Added
  `vibey.openChat` (`/chat`) and `vibey.connectMcp` (`/mcp`) to the shared command
  catalogue and redesigned the webview panel around a chat-first workspace with quick `/`
  command chips, inline open-gate cards with spend-gate badges, and one-click MCP setup.

## Consequences

- Operators can drive every phase of vibey from inside Claude Code, Codex, Cursor, VS Code,
  Claude Desktop, or Gemini CLI after running `vibey connect`, or from the built-in Chat
  workspace in krypton desktop, mobile, web, and VS Code.
- A host LLM over MCP is structurally prevented from authorizing spend, queue priority
  bumps, or remote workflow dispatch unless the operator explicitly widens
  `[hub] agent_scopes` in `vibey.toml`.
- All four Python layers, `@vibey/core`, `clients/vscode`, and `clients/app/src/core`
  maintain 100% branch coverage, and `clients/desktop` passes all 17 Meson C test suites.

## Proposed sub-doctrine

This decision establishes how people and host LLMs drive vibey across every interface, so
ADR-0020 requires a proposed sub-doctrine alongside the decision record. Only the
operator's merge into `src/vibey_tools/gh/docs/doctrines.md` ratifies it (Article II.3;
SD-01):

> **12.p — the conversation is the control plane** *(proposed; ratification requires the
> operator's merge)*: a person drives vibey from the conversation they already have open —
> inside their frontier coding assistant over MCP, or in krypton's own chat workspace on
> desktop, mobile, web and editor — and never has to leave the conversation to inspect
> state, start or pause work, or answer a non-spending gate. Every conversational client
> speaks the one hub contract, and every AI host connected to it acts as a scoped agent
> principal whose ceiling excludes spending money, reordering queues or dispatching
> workflows unless the operator declares otherwise in the repository. Where a gate spends
> money or mutates real infrastructure, the conversation surfaces the gate in full and
> reserves the act of consent for the human operator.
