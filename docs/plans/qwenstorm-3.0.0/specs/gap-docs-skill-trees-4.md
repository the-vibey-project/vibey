## Title
docs(skills): the vibey-architecture skill teaches the ORM seam, the queue port, the harness and surface lanes, and measurement

## Why
The `vibey-architecture` skill (`.claude/skills/vibey-architecture/SKILL.md`) predates the
3.0.0 mechanisms (`issue-audit/gaps.md` M3, lines 639-642; R35 item 6 in
`STORM/specs/rabbitmq-lanes.md:3985-3988`):
- `:9-11` names "four contracts"; `.importlinter` now declares more (six at HEAD `4317cff6`:
  `:8`, `:36`, `:56`, `:77`, `:109`, `:138`), and the ORM lanes add
  `application-persistence-free` (`orm-import-contracts`, `orm-raw-sql-guard`).
- `:17` says infrastructure is the "ONLY layer that may import asyncpg"; after
  `orm-raw-sql-guard`, asyncpg is imported only by the notifier, persistence goes through the
  ORM seam (ADR-0049) and `tests/meta/test_raw_sql_budget.py` fails on a new raw-SQL site.
- `:25-30` lists the `application/interfaces/` areas as of 2026-09-15; the directory now also
  holds `blob`, `bus`, `cache`, `config_store`, `docs`, `email`, `files`, `messaging`,
  `secrets`, `siem`, `sms`, `tracker` and more.
- Nothing says where a queue, a harness request, a surface operation or a measurement goes
  (ADR-0044, ADR-0045, ADR-0047, and the 8.g record).
The same text is in `.agents/skills/vibey-architecture/SKILL.md`,
`.cursor/rules/vibey-architecture.mdc` and `.agent/rules/vibey-architecture.md`.

## Required behaviour
1. Gather, for the script:
   - `CONTRACTS`: `grep "^name = " .importlinter | sed 's/^name = //'`, joined with `; `.
   - `AREAS`: `ls src/vibey/application/interfaces/*.py | xargs -n1 basename | sed 's/\.py$//' | grep -v '^__init__$'`,
     joined with `, ` and each wrapped in backticks.
   - `A8G`: the four digits of `ls docs/architecture/decisions/*-always-measured.md`;
     `AORM`: of `*-persistence-goes-through-the-orm.md`. If either is missing, STOP.
2. Write `.qwenstorm/skill_edit.py` and run it. For each of the four files, apply each pair
   with `assert text.count(old) == 1` and write the file back.
   - C. `old`: `` `import-linter` enforces this in CI via four `` (end of `:9`) through
     `` interfaces-declare-only. `` (`:11`), as the three lines stand. `new`:
     `` `import-linter` enforces this in CI through the contracts in `.importlinter`: `` +
     CONTRACTS + `.` (wrap at about 80 columns).
   - I. `old`: `├── infrastructure/    # Adapters. ONLY layer that may import asyncpg, httpx, etc.`
     `new`: `├── infrastructure/    # Adapters. The ONLY layer that may import SQLAlchemy, httpx, aio-pika, etc.`
   - A. `old`: the text from `` behind a `Protocol` in `application/interfaces/<area>.py` (`azure`, `build`, ``
     through `` `review`, `system`, `visual`). `` (`:25-30`'s list). `new`:
     `` behind a `Protocol` in `application/interfaces/<area>.py` ( `` + AREAS + `` ). ``
   - P. `old`: `` re-export shim of seven names — never add to it. Never `import asyncpg` or ``
     `new`: `` re-export shim of seven names — never add to it. Persistence goes through the ORM seam, SQLAlchemy 2 async on asyncpg behind `PostgresOrmInterface` (ADR-AORM); `tests/meta/test_raw_sql_budget.py` fails on any new raw-SQL site outside `LISTEN` (the notifier) and the migrator's scripts. Never `import asyncpg` or ``
     (with AORM filled in).
   - Q. Insert a new section before the line `## Shape: classes, behind interfaces`
     (`old` = that line; `new` = the section below, a blank line, then that line):
     ```
     ## Queues, lanes and measurements

     - **Jobs** go on the job queue port (`application/interfaces/queue.py`, ADR-0044):
       RabbitMQ dispatches by default, PostgreSQL stays selectable and is always the
       record. A handler never assumes which backend it runs on.
     - **Engine runs** go to a loop's queue (8.c): two loops, one instance per model.
       See the `vibey-engine-adapters` skill and ADR-0046.
     - **Test runs** are requests to the one test harness per machine (8.e, ADR-0045);
       never start a second pytest beside a running one.
     - **Surface operations** (tracker, docs, secrets, files, email, SMS, messaging,
       configuration, cache, blob storage, security events) go through the surface's
       port; each surface is driven by one lane on the bus (8.f, ADR-0047).
     - **Every new loop, lane, queue, surface or test run records its measurements**
       through `MeasurementPort` in the same change (8.g, ADR-A8G). Unmeasured is
       incomplete.
     - **Every new seam has a registered in-memory fake** in `tests/fakes/registry.py`
       (ADR-0045's amendment).
     ```
     (with A8G filled in).

## Where to change
- `.claude/skills/vibey-architecture/SKILL.md`, `.agents/skills/vibey-architecture/SKILL.md`,
  `.cursor/rules/vibey-architecture.mdc`, `.agent/rules/vibey-architecture.md`, by the script only.

## Acceptance criteria
- [ ] The script edits all four files; every assertion holds.
- [ ] `grep -c "## Queues, lanes and measurements"` prints 1 in each file, and
      `grep -c "via four"` prints 0 in each file.
- [ ] Each file names every `.importlinter` contract name and every interface module.
- [ ] `grep -n "ADR-A8G\|ADR-AORM"` prints nothing in the four files.
- [ ] `git diff` changes no header line and no SD-01 line; `uv run pytest -q -p no:cacheprovider -n 0 tests/meta` passes.

## Tests to write first (TDD)
None new: the tree-parity and SD-01 carriage meta-tests hold the four trees.

## Checks the lane must run (all must pass)
    grep "^name = " .importlinter
    ls src/vibey/application/interfaces/
    python3 .qwenstorm/skill_edit.py
    uv run pytest -q -p no:cacheprovider -n 0 tests/meta
    git diff --stat

## Out of scope
- The tenants table (`:110-146`) and anything about the loops' adapters, rotation or the
  rename (ADR-0046's docs lane owns `vibey-engine-adapters` and those rows).
- `vibey-domain-model`; other skills; code.

Commit as `docs(skills): the vibey-architecture skill teaches the ORM seam, the queue port, the harness, surface lanes and measurement`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
