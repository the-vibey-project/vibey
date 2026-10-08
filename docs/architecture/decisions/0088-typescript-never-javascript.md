# 0088 — TypeScript, never JavaScript: the only authored form is typed, and the JavaScript that must exist is generated

**Status:** proposed · **Date:** 2026-10-08 · **Extends:** ADR-0066 (one design system; it copied `channel.js` to every target), ADR-0062 and ADR-0067 (the TypeScript workspace and core) · **Cites:** sub-doctrines 9.b, 10.e, 12.b and 12.e · **Related:** ADR-0016, ADR-0051

**Owes:** the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md`
and `docs/index.md`; a `properdocs.yml` nav entry; `docs/llms.txt` regenerated from that
nav; the canon's entry in `src/vibey_tools/gh/docs/doctrines.md` and its regenerated
`corpus-index.json`. All are in the change that carries this record.

## Context

The project's application code is TypeScript and Python, and both are typed. JavaScript
was the gap. Measured on `develop` at `ae15cc72b`, before this change, `git ls-files` listed
20 JavaScript files:

- `design/web/channel.js`, hand-written, copied by the design generator to eight places;
- `math.js`, hand-written in one place and committed in three;
- the VS Code task panel's webview page, `clients/vscode/media/panel.js`, held to a type
  checker only by `// @ts-check` comments;
- two build scripts and two smoke-test files in `clients/vscode/`, plain Node;
- `babel.config.js` and `metro.config.js` for the krypton app.

None of it was checked by the compiler that checks everything beside it. The panel's own
comments say as much: a JSDoc type is a request to be checked, and a build that does not run
the check does not grant it.

## Decision

1. **TypeScript is the only authored form** (sub-doctrine 9.f). No exemption for scripts,
   configuration, tests or small helpers.
2. **A `.js` that must exist is an artifact.** A browser cannot execute a `.ts` file, and
   Expo's Metro and Babel `require` their configuration as `.js`. Each such file is compiled
   by the repository's own `tsc` (the one `npm ci` installs; ADR-0062) from a `.ts` source
   under `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes` and the rest of
   the flags `@vibey/core` already uses. It is committed at the path the consumer expects,
   behind a banner that names its source.
3. **The list is declared, and the rule is a test.** `scripts/typescript_artifacts.toml`
   lists every artifact and every place it is committed (ADR-0051).
   `tests/meta/test_typescript_artifacts.py` fails when a tracked `.js` is not on that list,
   when a listed file does not name its source, and when a committed file differs from what
   its source compiles to. CI installs Node and runs the check as Gate 0a; with no compiler
   it fails rather than skips, because a gate that quietly does not run reports a success it
   did not observe.
4. **Tools that run from a developer's machine are compiled, not committed.** The VS Code
   build scripts and smoke tests compile with `tsc -p tsconfig.tools.json` into untracked,
   ignored `.js` beside their sources.
5. **The design generator no longer owns scripts.** It keeps tokens, stylesheets and icons;
   the compiled scripts are this mechanism's, so no file has two writers.

## Consequences

- Twenty hand-written JavaScript files became seven TypeScript sources, one declared list and
  fifteen generated artifacts. The compiled `channel.js`, `math.js`, `panel.js` and the two
  app configs are the same programs; the types are new. `explorer.ts` (the ledger explorer) is
  born typed.
- The panel's message protocol, the ledger site format and the release `surfaces` object are
  now interfaces, so a field renamed on one side is a compile error on the other.
- Editing a source and forgetting to regenerate fails the build and names the command.
- Contributors need Node to change a script, as they already do to change a client.
- **Not converted, and named so it is not forgotten.** The release-surfaces workflow builds
  the consent banner and the analytics snippet as JavaScript inside Python string literals,
  in three managed copies (`.github/workflows/`, the vibey-gh tenant's copy and its
  template). That is authored JavaScript in a file this change's test cannot see. Converting
  it means moving the logic into TypeScript, serving it as an artifact and changing the
  markup the workflow emits into every published page; it cannot be exercised without a
  release run, so it is its own change. Until then 9.f is not yet true of the tree.

## Alternatives rejected

- **Keep JavaScript for configuration, typed by `// @ts-check`.** The status quo for the
  panel. It checks only where an editor or a build happens to run the checker, and the
  exemption is exactly the shape a rule erodes through.
- **Run `.ts` directly (Node's type stripping).** Node 24 can, but the VS Code extension
  declares `node >=20`, Metro and Babel load `.js` regardless, and a browser cannot.
- **Do not commit the compiled files; build them at deploy.** Every tenant builds its
  documentation from a clean checkout with `properdocs`, a Python wheel and a Docker image
  force-includes `docs/javascripts/*.js`; none of them has Node. A committed artifact with a
  drift test is the pattern the design tokens already use.
- **Add a bundler.** Nothing here imports anything at run time; `tsc` alone is enough, and a
  second toolchain would be a second thing to keep (10.e).

## Rule status

Conduct that binds future decisions, survives a rewrite and is not mechanism, so under 12.b
it is a sub-doctrine and then ratified: filed as **9.f** under doctrine 9, beside the
declared seam (9.b). The record argues it; only
`src/vibey_tools/gh/docs/doctrines.md` states it. Until the operator's merge ratifies it, it
is a proposal.
