# Issue spec template (QwenStorm 3.0.0)

Audience: a local gpt-oss:20b (Ollama, 131k context, ~40 turns, tools read_file/write_file/
edit_file/shell) that will implement this ONE issue in a clone of the storm integration branch,
then a human-grade reviewer who verifies it. Shared context: STORM-CONTEXT.md. Be concrete: name files, functions, line numbers, exact behaviours. No placeholders.

## Title
<conventional-commit style, e.g. "feat(engines)!: the worker's pool follows [engines].enabled">

## Why
2-5 sentences. Cite the ratified rule (sub-doctrine 8.b in src/vibey_tools/gh/docs/doctrines.md,
ADR numbers) and the verified gap with file:line evidence.

## Required behaviour
Numbered, testable statements of what must be true after the change.

## Where to change
The exact files/functions to edit or create, and the existing pattern to copy (file:line).
Every new class gets an interface beside it (ADR-0016: `pkg/x.py` -> `pkg/interfaces/x_interface.py`).

## Acceptance criteria
Checklist; each item verifiable by a command or a test name.

## Tests to write first (TDD)
Test file paths and test names, with what each asserts.

## Checks the lane must run (all must pass)
Exact commands. For src/vibey:
  uv run ruff check . && uv run ruff format --check .
  uv run mypy --strict src/vibey
  uv run lint-imports
  uv run pytest -q -p no:cacheprovider <focused tests>
  (100% branch coverage per layer: domain/, application/, infrastructure/, cli/)
For tenants: the tenant's own suite and static gates (see CLAUDE.md "Commands worth memorizing").
Each command runs as one line on its own: no heredoc (`<<'PY'`), no backslash continuation, no
multi-line inline script. A check needing more than one statement becomes a single
`python3 -c '...'` line (semicolons and generator expressions in place of loops); single-quote
the whole argument and double-quote every string literal inside it, since these commands run
through a real shell and a bare backtick or `$` inside a double-quoted outer string is not
literal there.

## Out of scope
What NOT to touch (other lanes own it). Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md,
AGENTS.md, GEMINI.md or skill trees -- the docs wave owns those. Do not push, open PRs, or
change git remotes. Commit locally with a Conventional Commit message when done.

## Hard repository rules (always)
- domain/ stays pure (no I/O, async, clock, network); enforced by tests/domain/test_domain_purity.py.
- Dependencies point inward: domain -> application -> infrastructure -> cli (import-linter).
- CreditsExhausted never has resets_at. A capacity rejection outranks a completion claim.
- Code lives in classes with an interface beside each (ADR-0016); module functions need a written reason.
- Every job idempotent under replay; the ledger is append-only.
