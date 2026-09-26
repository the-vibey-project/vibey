# @vibey/core

The TypeScript every krypton client shares: the VS Code extension today, and the mobile, web and
desktop apps as they land. It is plain TypeScript with no Node, no editor and no DOM, and it builds
against no platform types at all ([ADR-0067](../../docs/architecture/decisions/0067-one-typescript-core-for-every-krypton-client.md)).

| Module | What it is |
|---|---|
| `catalogue` | `vibey loops --json` parsed into loops, engines and efforts, and the loop selector |
| `run-events` | a run's event stream as a transcript, and its verdict |
| `commands` | the one command table: every client's palette and slash commands |
| `vibey-cli` | the `vibey … --json` calls, and the gate-answer planner |
| `transport` | `VibeyTransportInterface`, with `LocalProcessTransport` and `HubTransport` (the hub's routes, `docs/reference/hub-api.json`), and `HubDiscovery`, which finds a hub and checks a key |
| `budgets` | the budget rules, the spend ledger and the guard (the file itself stays in each client) |
| `doctor`, `ollama`, `ollama-lifecycle` | the setup checks and the local model's lifecycle |
| `cli-support`, `jsonl-parse`, `local-runner`, `volatile-storage-error` | smaller shared pieces |
| `tokens` | the design tokens, re-exported from `design/dist/ts/tokens.ts` (never copied) |
| `interfaces/` | every interface, including those the clients implement with their platform |

```bash
npm ci                                  # at the repository root: one workspace, one lockfile
npm run build --prefix packages/vibey-core
npm run coverage --prefix packages/vibey-core   # 100% of lines, branches, functions, statements
```
