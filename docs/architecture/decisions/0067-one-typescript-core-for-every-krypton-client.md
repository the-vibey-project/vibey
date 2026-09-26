# 0067 — One TypeScript core for every krypton client

**Status:** proposed · **Date:** 2026-09-25 · **Cites:** sub-doctrines 9.b, 9.e, 10.e, 12.c · **Related:** ADR-0016, ADR-0017, ADR-0023, ADR-0059, ADR-0065, ADR-0066 · **Evidence:** `develop` at `30356862`, read 2026-09-25

**Owes:** the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md`
and `docs/index.md`, and a nav entry in `properdocs.yml`. All are done in the change that
carries it.

## Context

The client suite (ADR-0062, ADR-0066) will run on four surfaces: the VS Code extension, a
React Native app for Android, iOS and the web, a GTK desktop app in C, and the vibey hub that
serves the web build. Three of the four are TypeScript. Until now the only TypeScript was
the extension (`clients/vscode`, ADR-0059). About half of its `src/core` was plain logic that
never touched Node or the editor: the engine catalogue, run-event parsing, the one command
table, the gate-answer planner, the budget rules, the doctor, and the interfaces they are
written against.

Copying that logic into each app would give three copies that drift. The rule that fixes
the slash commands, the budget arithmetic and the gate answers would live in three places,
and nothing would make the three agree.

## Decision

1. **One package, `@vibey/core`, in `packages/vibey-core/`.** It holds the pure part of the
   extension's core:
   - every interface;
   - the modules `catalogue`, `local-runner`, `run-events`, `commands` (the one command table),
     `cli-support`, `ollama`, `ollama-lifecycle`, `doctor`, `vibey-cli` (with the
     gate-answer planner) and `jsonl-parse`;
   - the rules of `budgets`: `BudgetRules`, the spend ledger and the guard;
   - `VolatileStorageError`.

   It also re-exports the generated design tokens, `design/dist/ts/tokens.ts` (ADR-0066).
   They are re-exported, never copied, so the generator stays the only writer. The package
   builds against **no platform types at all** (`"types": []`, `lib` ES2022). A test also
   fails if its source imports `node:*`, `vscode` or a DOM global. The three platform types
   it names (`AbortSignalLike`, `SignalName`) are written out in
   `interfaces/platform-interface.ts`, and Node's, a browser's and React Native's own types
   all fit them.
2. **What needs a platform stays in the extension.** The Node pieces that use `fs`,
   `child_process` or `http` stay in `clients/vscode/src/core` and implement the package's
   interfaces: the process runner, the HTTP client, the JSON-lines files, storage, settings,
   git, the model lock, runs and the budget file (`BudgetStore`). To keep the extension's
   own imports unchanged, the extension re-exports the moved names it used to define
   (`BudgetError`, `SpendLedger`, `BudgetGuard`, `JsonlParse` and `VolatileStorageError`).
3. **One transport interface, two transports.** `VibeyTransportInterface` is every call a
   client makes to vibey.
   - `LocalProcessTransport` runs the `vibey … --json` command line through an injected
     process runner. The extension injects its Node one, so the package stays free of Node.
   - `HubTransport` is the network transport for mobile and web. Its client is to be
     generated from the hub's OpenAPI document, `docs/reference/hub-api.json`. That document
     is not on `develop` yet (the hub lane is building it), so today every call is refused
     with a `HubTransportError` that names the document. The generated client is a
     follow-up that lands after the document does.
4. **An npm workspace at the repository root.** The root `package.json` (private, named
   `vibey-clients`) lists `packages/vibey-core` and `clients/vscode`. There is one lockfile,
   the root `package-lock.json`, and it replaces `clients/vscode/package-lock.json`. The
   Python tree does not read any of it. Each new TypeScript client joins the list when it
   lands, and `tests/meta/test_clients_have_ci.py` fails until CI runs it.
5. **The package ships inside the extension, not beside it.** The `.vsix` is still
   packaged with `--no-dependencies`, and the extension still installs nothing at runtime
   (ADR-0059). At compile, `scripts/vendor-core.js` copies the built package into
   `out/node_modules/@vibey/core`, where Node finds it from `out/extension/extension.js` and
   `out/cli.js`. CI checks that the `.vsix` carries it.
6. **Its own checks, at the same floor.** The package's vitest suite holds it to 100% of
   lines, branches, functions and statements (ADR-0023), and the generated tokens it
   re-exports count too. The new `@vibey/core` CI job runs it, and the extension's job still
   runs its own suite at 100% over what stayed.
7. **The naming.** The package is `@vibey/core` because it is the engine's client core:
   vibey names the project and the engine, and every app and interface is krypton, always
   lowercase (sub-doctrine 9.e, ADR-0065). A package that every krypton client imports is
   the engine's contract, not one of the apps. So it keeps the engine's namespace, the way
   `vibey-gh` and `vibey-skills` do. The apps built on it carry the krypton name.

## Consequences

- The mobile, web and desktop lanes import the command table, the gate answers, the budget
  rules and the catalogue from one place. A change to any of them reaches every client at
  once, and the package's suite proves it once.
- The extension behaves exactly as before. Its tests were split between the two suites,
  and the 306 tests, 191 in the extension and 115 moved into the package, still pass at 100%
  in each. More package tests were added for the pieces the extension's tests used to cover
  indirectly.
- The package's build output sits under `dist/packages/vibey-core/src/`, not `dist/`,
  because its root must hold the generated tokens it re-exports. `package.json`'s
  `exports` hides the path from importers.
- A repository-root `package.json` and `package-lock.json` now exist beside the Python
  project files. `.dockerignore` keeps `node_modules` and the package's build out of the
  image, which still carries no Node.
- `HubTransport` is a declared stub until `docs/reference/hub-api.json` lands. Anything
  that selects it is refused plainly and never fails silently.
