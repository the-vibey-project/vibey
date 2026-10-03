# 0078 — Retire cursorloop and agyloop

**Status:** accepted · **Date:** 2026-10-03 · **Issue:** [#1376](https://github.com/the-vibey-project/vibey/issues/1376) · **Supersedes in part:** ADR-0006, ADR-0015, ADR-0021, ADR-0037 and ADR-0042, where each names these two engines as current · **Cites:** sub-doctrines 8.b, 8.c, 10.f, 12.c and 12.e · **Related:** ADR-0005, ADR-0038, ADR-0064 · **Evidence:** `develop` at `588c69b3f`, read 2026-10-03 · **Canon:** amends the paid-adapter lists of 8.b and 8.c, a ratification-ready draft under Article II.3 until the operator's merge carries it

**Owes:** the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md`
and `docs/index.md`; a `properdocs.yml` nav entry for this record; `docs/llms.txt`
regenerated from that nav; a `changelog.d/` fragment of type `breaking`. All are in the
change that carries this record.

## Context

The paid loop (8.c) drove four adapters: `claudeloop`, `codexloop`, `cursorloop` and
`agyloop`. Each of the last two was a whole runner tenant under `src/vibey_runners/` — its
own package, console script, vendor SDK dependency (`cursor-sdk`, `google-antigravity`),
`tools` matrix rows on three interpreters, descriptor, capacity classifier, event map and
golden argv files — kept green by the same gates as the engines that carry the work.

The operator decided, on #1376, to delete both outright rather than keep them dormant: the
paid loop keeps Claude through `claudeloop` (the paid default, 8.b) and OpenAI through
`codexloop`; the local engines — `gptossloop`, `qwenloop` and `claudeloop-local` — are
untouched. This record writes that decision down and says what follows from it.

## Decision

1. **Both engines are deleted, not repealed.** `src/vibey_runners/cursor/` and
   `src/vibey_runners/agy/` are removed with their console scripts, wheel packages, vendor
   SDK dependencies, `tools` matrix rows, Docker `COPY` lines and design-asset targets.
   `EngineId` loses `CURSORLOOP` and `AGYLOOP`; their descriptors, capacity classifiers,
   event maps, API-key variables and state directories leave the core with them. No
   interval of "repealed but still in the tree" is kept (`REPEALED_FROM_LOOPS` stays
   empty, as ADR-0064's handling of OpenCode left it).
2. **Naming a retired engine is refused, out loud, naming this record.** A `vibey.toml`
   whose `[engines] enabled`, `[engines.weights]` or any `[phases.*] engines` list names
   one; a project's `engine_environment.engines`; `vibey worker --engines`;
   `vibey doctor --engine`; and the cluster preflight's `--engines` — each fails with the
   ordinary unknown-engine refusal plus a clause that says the engine was retired by
   ADR-0078 and which paid engines remain. A phase's engine list is not otherwise checked
   against the known engines, so without this a retired name there would have been dropped
   without a word (12.e). The clauses live in one table, `RETIRED_ENGINES` in
   `domain/engine.py`, and `EngineId` itself raises them for a retired name, so every path
   that turns an operator's word into an engine id says the same thing.
3. **Stored history is not rewritten.** The ledger is append-only, and the `engine_id`
   columns are plain text. A ledger event, health row, rotation cursor or job that names a
   retired engine stays exactly as written and reads as an `UnrecognizedEngineId` (vibey#287):
   nothing selects it, nothing crashes on it. A job last assigned to one of them gets no
   affinity and excludes nothing on its next attempt, so it moves to an engine that exists.
   No migration was needed: no `CHECK` constraint or enum in the schema names either engine.
4. **The generic seams stay.** The capabilities only these engines exercised — a plan
   passed as a flag (`plan_flag`), a run without a wind-down or prompt verb, a model chosen
   per effort by name — are properties of `EngineDescriptor` and of the catalogue that
   `vibey loops` publishes, not of the deleted engines. They remain, tested with synthetic
   descriptors, so the next engine that needs one is a descriptor rather than a code change
   (12.c).

## Consequences

**Breaking.** This is why the release derives a major version (4.0.0):

- the `cursorloop` and `agyloop` console scripts are gone from `vibey-engine`;
- a configuration, flag, CRD (`VibeyProject.spec.engines`) or engine environment that names
  either engine is refused until the name is removed;
- `vibey loops --json` no longer lists them, so the paid loop shows two engines.

**Not breaking.** Existing ledgers, health rows and rotation cursors keep their rows and
keep loading (Decision 3). The canon's paid default, Claude through `claudeloop`, does not
change.

**Left in place, on purpose.** Old ADR bodies, `CHANGELOG.md` history, the research paper,
the plans under `docs/plans/` and `research/` describe what was true when they were written
and are not rewritten (10.f); the ADRs that stated the roster as current carry a
"superseded in part" note instead. The repository's own `.gitignore` keeps ignoring
`.cursorloop/` and `.agyloop/`, because existing checkouts still hold those state
directories and un-ignoring them would put old run transcripts one `git add -A` from a
commit.

**Canon.** Sub-doctrines 8.b and 8.c name the paid loop's adapters. Both lists drop the two
engines in the change that carries this record, marked as a ratification-ready draft; the
operator's merge ratifies them (Article II.3).
