## Title
docs(adr): draft ADR — lane storms become a family command that submits every attempt to sovereignloop

## Why
The QwenStorm machinery that is building 3.0.0 lives outside the family, in scripts beside a
scratch checkout. Sub-doctrine 8.c (`src/vibey_tools/gh/docs/doctrines.md:204`) says storms put
work on the loop's queue and nothing spawns a loop directly; 10.e (`doctrines.md:417`) calls "a
project that ships delivery tooling it does not itself run" a claim it has not tested; 12.c
(`doctrines.md:455`) requires the state to be declared and every value a key. Today:
- `STORM/qwenlane.py:19-26` puts the integration clone's source on `sys.path` and imports
  qwenloop's private internals (`_load_config`, `_run_plan`, `_server_for`,
  `_tracked_repository_context` from `qwenloop.cli.app`), then runs the model in-process.
- `STORM/storm-queue.sh:15-16` hard-codes the storm root and a venv; `:52-54` hard-codes
  `gh issue view ... -R the-vibey-project/vibey`; `STORM/lane-setup.sh:7-9` hard-codes the main
  checkout; `STORM/file-issue.py:5-17` and `file-suite.py:25-29` hard-code the repository, the
  label and the pace.
- The state is three plain files (`queue.txt`, `integrated.txt`, `abandoned.txt`) and an
  `UNATTENDED` marker (`storm-queue.sh:11-13`, `:41-42`).
- The in-tree storm is `qwenloop run --storm` (`src/vibey_runners/qwen/src/qwenloop/cli/app.py:123-150`,
  `_run_storm` at `:373-474`, plans from `application/storm.py:97-197`). It sweeps one shared
  checkout, has no dependency queue, no isolation, no gutted-file guard, no editing rules, and
  its owner default is a person (`app.py:49`, `_DEFAULT_STORM_OWNER`).

This is EPIC-sized and its home is a real decision, so this lane writes a draft ADR, not code.

**Implementer: a large model or the operator (design, not code); the storm runner skips gap-spike-*.**

## Deliverable
`/private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-gap-storm-command.md`, a draft ADR in
the shape of `specs/ADR-two-loops.md`: a header line with **Status** (proposed), **Date**,
**Amends/Cites** and **Evidence** (the integration commit and every `file:line` read), then
**Context**, **Decision**, **How each non-negotiable still holds**, **Consequences** (Good/Bad),
**Alternatives rejected**, **Verification owed at implementation**, and **Lanes** (one row per
child: slug, files, deps, whether it can start before the ADR is ratified).

## Questions the ADR must decide
1. **Home.** One of: (a) the sovereign runner's own `storm` verb (today `qwenloop run --storm`;
   `sovereignloop` after `loops-rename`); (b) `vibey-gh storm` (it owns the forge adapters,
   `ForgeAdapterInterface`, the merge train and the git runner; it is dependency-free and
   cannot import vibey); (c) `vibey storm` (it owns the loop client and `vibey loop submit`).
   Weigh: who may talk to the broker (tenants never import vibey; 8.c's single instance), who
   files issues on a forge-neutral protocol (8.b: Forgejo by default, GitHub declared), who
   integrates branches, and the Python floors (qwenloop 3.12+, vibey-gh 3.11+).
2. **How an attempt reaches the loop.** Through `vibey loop submit` (lane `loops-submit-cli`)
   as a pinned run, so one model instance serves storms, workers and the command line alike
   (8.c). What the storm owns vs. the loop owns: plan text, repair prompt, attempt count,
   deadline, and the result's evidence.
3. **Declared state.** The format and home of the lane queue (`slug issue deps`), the settled
   sets (integrated, abandoned, blocked-on) and the unattended switch: a file under the
   repository (which path), a ledger, or the forge. 12.c: a stranger with a clone can restore it.
4. **Lane isolation.** Keep `lane-setup.sh`'s guarantees (`:17-29`: a clone with no remote, no
   credential helper, `core.hooksPath=.githooks`) and close its gap: it never installs the
   framework hooks the shims chain to (see `tests/meta/test_githooks_reach_the_framework.py`),
   which is why lane commits ran without their local gates.
5. **Completion evidence (9.c, 10.f).** Carry `qwenlane.py:120-149`'s rule -- a run that claims
   completion with no surviving change, or whose only change was restored, has not done the
   item -- and decide what else counts (focused tests named in the spec, the diff check).
6. **Spec → issue.** The spec format (`SPEC-TEMPLATE.md`, `## Title` parsed by
   `^## Title\n(.+)$`) as a declared schema; filing through the forge protocol, not `gh`;
   pacing and resumability as in `file-suite.py:1-12` (the filing log and issue map).
7. **Review and integration.** Batch review in unattended mode (`storm-queue.sh:11-13`), who
   merges into the integration branch, and how the integration branch meets the merge train.
8. **Measurement (8.g, `doctrines.md:316`).** Per attempt: queue wait, run latency, turns,
   outcome, restored files; per storm: throughput and depth. Which port records them.
9. **Configuration (12.c).** Every hard-coded value above becomes a key with its default
   stated: repository, forge, label, owner, roots, venv/interpreter, pace, attempts, model.
10. **Rename.** Command and state names across `loops-rename` (qwenloop → sovereignloop).

## Canon the ADR must honour
8.a–8.c (`doctrines.md:99-235`), 8.g (`:316`), 7.c (`:82`), 9.b (`:349`), 9.c (`:351`),
10.e (`:417`), 10.f (`:419`), 12.c (`:455`); ADR-0046 (`specs/ADR-two-loops.md` §3, §10:
`vibey loop submit`); SD-01 (every storm lane's agent carries it verbatim); CLAUDE.md
non-negotiables (never block a worker on a human; every job idempotent under replay; never
implement on `main`).

## Evidence to gather (read, cite with file:line)
- `STORM/qwenlane.py` (all 158 lines), `storm-queue.sh` (61), `lane-setup.sh` (30),
  `file-issue.py` (17), `file-suite.py` (392), `EDITING-RULES.md`, `qwen-storm.toml` (8),
  `SPEC-TEMPLATE.md`, `queue.txt`, `integrated.txt`, `abandoned.txt`, `progress.log`.
- `src/vibey_runners/qwen/src/qwenloop/cli/app.py:103-165`, `:250-315`, `:373-474`;
  `application/storm.py`; `infrastructure/tools.py:21-33`, `:104-117` (the write_file shrink
  refusal that EDITING-RULES rule 2 relies on).
- `src/vibey_tools/gh/vibey_gh/` forge adapters and merge train (`forge_*`, `merge_train.py`).
- `.githooks/` and `tests/meta/test_githooks_reach_the_framework.py`.
- `specs/ADR-two-loops.md` §3 and §10; lane `loops-submit-cli`'s spec once written.

## Child lanes the ADR must name
Written now, because they are exact without the ADR's decisions (they improve the in-tree
storm whatever its final home):
- `gap-storm-1-editing-rules` -- the generic lane editing rules ship as a prompt asset in every
  storm plan.
- `gap-storm-2-gutted-file-guard` -- gutted-file restore is a checked, tested class, with its
  thresholds as keys.
- `gap-storm-3-gutted-file-wiring` -- the in-tree storm restores after every attempt, tells the
  next attempt, and never counts a gutted attempt as converged.

Owed after the ADR is ratified (list each in **Lanes** with files and deps):
- `lane setup` -- an isolated clone with no remote and the framework hooks installed.
- the declared dependency queue and integration branch (queue, integrated, abandoned, blocked).
- spec → issue filing on the forge protocol, with the spec schema declared.
- each attempt submitted to sovereignloop's queue (after `loops-submit-cli`).
- the claimed-complete-without-surviving-changes rule as a checked rule.
- measurement of attempts and storms (after `gap-measure-port`).
- retiring `STORM/*.sh`/`*.py` in favour of the command (the operator's step).

## Acceptance criteria
- [ ] The ADR file exists with every required section, answers questions 1–10, and cites
      every evidence file with line numbers at the integration HEAD it names.
- [ ] Its **Lanes** table names each child with files, deps and a one-line scope.
- [ ] No source file, test, CHANGELOG, doc or skill tree is changed by this lane.

## Tests to write first (TDD)
None: a design lane. Its verification owed is written into the ADR.

## Checks the lane must run (all must pass)
    test -s /private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-gap-storm-command.md
    grep -c "^## " /private/tmp/claude-501/storm/qwenstorm-3.0.0/specs/ADR-gap-storm-command.md

## Out of scope
- Implementing any child. Ratifying anything (the operator's merge does, Article II.3).
- CHANGELOG.md, docs/, ADRs under `docs/architecture/decisions/`, CLAUDE.md, AGENTS.md,
  GEMINI.md and the skill trees.

The draft lives under `STORM/specs/` and nothing is committed to the repository until the
operator moves it into `docs/architecture/decisions/`.
Commit as `docs(adr): lane storms become a family command` (only at that move). Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
