## Title
feat(domain): SurfaceQueueNames, every exchange, queue and routing key of the surface lanes

## Why
Draft ADR-0047 §4 (`specs/ADR-surface-lanes.md`) names every broker object a surface lane
uses, under the configurable `[bus] prefix` (lane `rmq-r01-queue-config`; sub-doctrine 12.c:
declared and configurable). §16 reserves the `<prefix>.surface.*` segment for this record, so
it never collides with ADR-0044's `<prefix>.jobs.*`, ADR-0045's `<prefix>.tests.*` or ADR-0046's
run topology. The names are pure, so the domain owns them and the 100% domain floor covers
them, as R06 did for the job names (`issue-audit/updates/353.md` behaviour 4). Part of ADR-0047
lane S02.

## Required behaviour
In the new `src/vibey/domain/surface_names.py`, `class SurfaceQueueNames`:

1. `__init__(self, prefix: str = "vibey")`. A prefix that does not match
   `^[a-z][a-z0-9_-]{0,31}$` (R01's `bus.prefix` rule) raises
   `ValueError(f"bus prefix {prefix!r} must match ^[a-z][a-z0-9_-]{{0,31}}$")`.
2. Methods, each taking `surface: SurfaceName` where shown (`s` is `surface.value`, `p` the prefix):

   | method | returns |
   |---|---|
   | `prefix()` | `p` |
   | `request_exchange()` | `"<p>.surface"` (topic) |
   | `dead_exchange()` | `"<p>.surface.dlx"` (direct) |
   | `write_queue(surface)` | `"<p>.surface.<s>"` |
   | `read_queue(surface)` | `"<p>.surface.<s>.read"` |
   | `dead_queue(surface)` | `"<p>.surface.<s>.dead"` |
   | `lock_queue(surface)` | `"<p>.surface.<s>.lock"` |
   | `write_key(surface)` | `"<s>"` |
   | `read_key(surface)` | `"<s>.read"` |

   There are no other public methods.
3. `src/vibey/domain/interfaces/surface_names_interface.py`:
   `@runtime_checkable class SurfaceQueueNamesInterface(Protocol)` with the nine methods;
   exported from `src/vibey/domain/interfaces/__init__.py`.
4. Pure: no clock, I/O or async.

## Where to change
- New `src/vibey/domain/surface_names.py`, `src/vibey/domain/interfaces/surface_names_interface.py`.
  Copy the style of R06's `QueueNames` if `src/vibey/domain/job_dispatch.py` exists; otherwise
  of `src/vibey/domain/correlation.py`.
- `src/vibey/domain/interfaces/__init__.py` (export).
- New `tests/domain/test_surface_names.py`.

## Acceptance criteria
- [ ] Every row of the table holds for the default prefix and for `"acme"`, for all eleven surfaces.
- [ ] The public method names are exactly the nine above.
- [ ] `SurfaceQueueNames("Vibey")` and `SurfaceQueueNames("a" * 33)` raise `ValueError`.
- [ ] No name starts with `<p>.jobs`, `<p>.tests` or `<p>.runs`.
- [ ] `test_domain_purity.py` passes; 100% `domain/` branch coverage.

## Tests to write first (TDD)
`tests/domain/test_surface_names.py` (no service):
- `test_names_table` (parametrized over the table, both prefixes, every surface)
- `test_public_methods_are_exactly_the_table`
- `test_prefix_is_validated`
- `test_names_stay_inside_the_surface_segment`
- `test_names_satisfy_their_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/domain/test_surface_names.py tests/domain/test_domain_purity.py
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- Declaring anything on a broker (`surfaces-topology`). CHANGELOG.md, docs/, ADRs, CLAUDE.md,
  AGENTS.md, GEMINI.md and the skill trees (`surfaces-docs-wave`). Do not push, open PRs or
  change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `surfaces-catalogue` (`SurfaceName`).
- **Shares a file with:** `src/vibey/domain/interfaces/__init__.py` (exports only).
- **Must keep passing unchanged:** `tests/domain/*`, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `/private/tmp/claude-501/storm/qwenstorm-3.0.0/EDITING-RULES.md` before changing a file.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from a sibling file.
  - The default run needs no service; never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
