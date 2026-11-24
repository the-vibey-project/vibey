---
description: "Reference for @vibey/core, the shared TypeScript core of the krypton clients: what each module does, who uses it, and how to build and test it."
---

# @vibey/core: the TypeScript every krypton client shares

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** `@vibey/core` is plain TypeScript with no Node, no editor and
> no DOM: the command table, the `vibey … --json` calls, the transports to the hub and to GitHub,
> the budget rules and the run-event parser that the VS Code extension and the krypton mobile and
> web app both use (ADR-0067). The C desktop app cannot use it. It is not published; build and
> test it from the repository root with `npm ci` and the three commands below.

> [!IMPORTANT]
> **Work in progress — not a final product:** `@vibey/core` and the surrounding vibey ecosystem are under active development and are not yet a final product. APIs and types are still evolving. Folks will be notified on the [Discord server](https://discord.gg/Qvu8aYnVS) once the product is finally done.

## How to read this page

**Daniel:** Professor, is this an app?

**Professor Feynman:** It is the engine block, not the car. Two cars are built on it, the editor
extension and the phone app, so a fix made here reaches both. The table says what each part
does; look up the one you are about to change.

## Who uses it

| Client | How |
|---|---|
| VS Code extension (`clients/vscode`) | A dependency (`"@vibey/core": "0.4.0"`) in the root npm workspace. |
| krypton mobile and web (`clients/app`) | Read from source: Jest maps `@vibey/core` to `packages/vibey-core/src/index.ts`, and the app imports it (for example `VibeyCli` in `src/core/hub-client.ts`). The app keeps its own lockfile outside the workspace. |
| krypton desktop (`clients/desktop`) | Does not use it. The desktop app is C17 on GTK 4 (ADR-0073) and mirrors the same rules in C. |

It builds against no platform types at all ([ADR-0067](../../docs/architecture/decisions/0067-one-typescript-core-for-every-krypton-client.md)):
anything that needs the platform is an interface under `src/interfaces/` that the client
implements.

## Modules

| Module | What it is |
|---|---|
| `catalogue` | `vibey loops --json` parsed into loops, engines and efforts, and the loop selector |
| `run-events` | a run's event stream as a transcript, and its verdict |
| `commands` | the one command table: every client's palette and slash commands |
| `vibey-cli` | the `vibey … --json` calls, and the gate-answer planner |
| `transport` | `VibeyTransportInterface`, with `LocalProcessTransport`, `WorkflowsTransport` (every call as `vibey --workflows …`, ADR-0085) and `HubTransport` (the hub's routes, `docs/reference/hub-api.json`), and `HubDiscovery`, which finds a hub and checks a key; each transport's `runOnWorkflows` sends one command line to the repository's GitHub-hosted runners |
| `workflows` | `WorkflowsCommandLine`: a command line for the workflows read, checked, and its result read the same from `vibey -w` and from the hub, and `PortableTimer` |
| `hub-engine` | the one hub on this computer, from a UI: `vibey hub status \| start \| stop`, always the local `vibey`, never through a paired hub or the workflows; closing a UI never stops the hub |
| `project-driver` | driving a project from a conversation: starting one, being asked its questions, replying, and unwinding it; wording and parsing only, the CLI does the work |
| `project-follower` | following a project as it runs: reads `vibey status` and `vibey gates` every few seconds and hands back when a person is needed, the project finishes, time is up, or the person cancels; it starts and stops nothing |
| `budgets` | the budget rules, the spend ledger and the guard (the file itself stays in each client) |
| `doctor`, `ollama`, `ollama-lifecycle` | the setup checks and the local model's lifecycle |
| `local-runner` | the local runner's protocol (`.qwenloop`, the done marker, the verdict fence, exit 75) and the two engine identities, `gptossloop` (on by default) and `qwenloop` |
| `cli-support`, `jsonl-parse`, `volatile-storage-error` | smaller shared pieces |
| `tokens` | the design tokens, re-exported from `design/dist/ts/tokens.ts` (never copied) |
| `interfaces/` | every interface, including those the clients implement with their platform |

### A known difference from the rest of vibey

`local-runner.ts` gives `gptossloop` the default model `gpt-oss:20b`, the stock build. The runner
itself, and every other vibey surface, defaults to the Heretic v2 build
`hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE` (ADR-0099,
`src/vibey/domain/sovereign_model.py`). A client that passes this default runs a different model
from the rest of vibey. This is drift in the code, recorded here until it is fixed.

## Build and test

```bash
npm ci                                  # at the repository root: one workspace, one lockfile
npm run build --prefix packages/vibey-core
npm run coverage --prefix packages/vibey-core   # 100% of lines, branches, functions, statements
```

`npm run typecheck` checks the sources and the tests; `npm test` runs Vitest without coverage.
The 100% thresholds are in `vitest.config.mts`, which leaves out `src/interfaces/**` and
`src/index.ts`. CI runs this package as the `vibey-core` job. Every line is TypeScript
(sub-doctrine 9.f, ADR-0088).

## Where next

- [ADR-0067](../../docs/architecture/decisions/0067-one-typescript-core-for-every-krypton-client.md):
  why there is one core for every TypeScript client.
- [The krypton app README](../../clients/app/README.md): the mobile and web client that reads this
  core from source.
- [The hub API reference](../../docs/reference/hub-api.md): the routes `HubTransport` calls.

## Say it in one line

@vibey/core is the platform-free TypeScript the VS Code extension and the krypton phone and web app
share, so one fix reaches both.
