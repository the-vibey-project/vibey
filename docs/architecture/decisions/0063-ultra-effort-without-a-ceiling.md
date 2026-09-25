# 0063 — ULTRA: effort without a ceiling

**Status:** proposed · **Date:** 2026-09-25 · **Cites:** sub-doctrine 8.b as amended by the change that carries this record (*the cap, and the one path to no cap*), awaiting the operator's ratifying merge (Constitution Article II.3); sub-doctrines 8.g, 12.c, 12.d, 12.f and 10.g; Constitution Article III.2 · **Related:** ADR-0005, ADR-0059, ADR-0062 · **Evidence:** `develop` at `0a2f856e`, read 2026-09-25

**Owes:** this record states a design; no code in the change that carries it implements
ULTRA. The implementation is the ULTRA lane's, and every item under *Decision* is owed
there with its tests. The no-cap conduct is canon, in the 8.b amendment drafted in the same
pull request (ADR-0020). This record also owes the ADR count in `CLAUDE.md`, `AGENTS.md`,
`GEMINI.md`, `README.md` and `docs/index.md`, and a nav entry in `properdocs.yml`, both done
in the change that carries it.

## Context

The operator asked for infinite runs and loops. A run should stop only when the operator
stops it or a declared budget cap is reached, "finished" should become a checkpoint followed
by another improvement pass, and an unlimited budget should be available behind several
warnings.

What `develop` has at `0a2f856e`:

- `domain/effort.py` defines five levels, `TRIVIAL` to `MAX`. `BUILD_LADDER` escalates an
  item over six attempts, and the seventh attempt parks it at a human gate.
- The budget brake is `application/budget_source.py`'s `LedgerBudgetSource`, which tallies
  spend from the ledger against a declared cap. Cap changes are `BudgetCapChanged` events.
- The extension's `vibey-vscode declare-paid --no-cap --confirm-no-cap` already records a
  no-cap declaration, with one confirmation flag and no warning a person has to read.
- The canon says budgets bound every loop (Constitution, Article III.2) and that paid use is
  declared-only (8.b). Nothing said whether a no-cap declaration is lawful, or how.

## Decision

1. **ULTRA is the sixth effort level, after MAX.** `Effort.ULTRA = 5`. It is chosen, never
   escalated into: no ladder climbs to ULTRA on its own.
2. **Its projections are unbounded.** Where a runner takes a limit, ULTRA passes none:
   qwenloop, gptossloop and claudeloop run with no `--max-turns`. Where a runner insists on
   a limit, its adapter re-invokes it in passes, as a loop, each pass continuing from the
   last one's state.
3. **The ladder never parks at ULTRA.** An item at ULTRA does not exhaust the attempt ladder
   and is not parked at a human gate for running long. It still parks for the reasons that
   are not about length: a human gate the phase asks for, a no-loss handoff failure, or a
   capacity rejection.
4. **"Done" is a checkpoint.** On a done verdict an ULTRA run commits, then enqueues the next
   pass: review, the checks, then the next improvement. Each pass is a ledger event with its
   own job key, so a replayed pass is answered once and never runs twice.
5. **What still stops it.**
   - **The operator's Stop,** from any paired client, binding at once.
   - **The budget brake,** at the declared cap.
   - Nothing else ends an ULTRA run by itself. `CreditsExhausted` stays a handoff to the
     next engine, with no `resets_at`, exactly as today.
6. **The no-cap path.** A declaration with no cap is lawful only through the path 8.b now
   states, and every surface implements it the same way:
   1. a full-screen warning with the chosen engine's measured cost per hour, and "unknown"
      when it has not been measured (8.g);
   2. a typed phrase: `I accept unlimited spending`;
   3. a second warning whose default is "Keep a cap";
   4. the declaration `[budget] ultra_no_cap = true` in `vibey.toml`, an entry in the budget
      journal, and a ledger event on the `BudgetCapChanged` pattern naming who, when and
      which device;
   5. never switched on from a phone or the web app: only from the host;
   6. switched off by one action (one click in a client, one command at the CLI), binding
      at once.

   While it stands, every client shows an "UNLIMITED SPEND" banner and a spend ticker, and
   sends reminder notifications at declared thresholds. The CLI form runs steps 1 to 3
   interactively, in the terminal. The extension's existing `--no-cap --confirm-no-cap`
   flags on their own can show no warning and take no typed phrase, so they are refused,
   and a no-cap declaration made any other way is ignored and reported.
7. **Every picker shows ULTRA distinctly.** It has its own colour and motion from the design
   tokens (ADR-0062), on every client and in `vibey loops --json`.

## Consequences

- **A run can cost without limit.** That is the feature, and why the path to it has six
  steps and the path out has one. The asymmetry is 12.f's, applied to money.
- **Constitution Article III.2 is read, not amended.** "Budgets bound every loop" is read
  as: every loop has a budget the operator declared, and "no cap" is such a declaration,
  made on purpose through the warned path, with Stop always in reach. The 8.b amendment
  states this reading in the canon itself, so the canon does not carry the rule and its
  apparent opposite unreconciled. Whether that reading holds, or whether the Constitution
  needs its own amendment, is the operator's call at the merge.
- **Goldens and pickers change.** `vibey loops --json` gains ULTRA, and so do the
  extension's `CatalogueParser` and `LoopSelector` and every client's picker.
- **Tests owed by the ULTRA lane:**
  - domain property tests: ULTRA never parks for length, and always stops at a cap or on
    Stop;
  - golden updates;
  - runner adapter tests for the re-invocation loop;
  - an end-to-end drive of the three warnings;
  - a sovereign ULTRA run that completes two improvement passes and stops on Stop;
  - a paid ULTRA run that stops at a small cap.

## Alternatives considered

- **Make MAX unbounded instead of adding a level.** Rejected: MAX is reached by escalation,
  and an unbounded run must be chosen on purpose, never climbed into.
- **Allow no cap with one confirmation, as the extension does today.** Rejected: one flag is
  a click, and a click is how an unlimited spend happens by accident.
- **Forbid no cap entirely.** Rejected: the operator asked for it, and the canon's job is to
  make it safe to have, not to overrule them.
