## Title
docs(agents): CLAUDE.md, AGENTS.md and GEMINI.md state 3.0.0's law

## Why
The three agent briefs state repealed facts (`issue-audit/gaps.md` M2, lines 630-637):
`CLAUDE.md:3-6` ("six `*loop` … runners", opencode), `:140-141` (the queue is
"`FOR UPDATE SKIP LOCKED`"); `AGENTS.md:3-5`, `:90-104` (a sovereign list naming
`qwenloop`+`opencode`, Bitwarden, Forward Email and Fossify as defaults), `:154-156`;
`GEMINI.md:3-6`, `:84`. None states 8.c's two loops, RabbitMQ dispatch, 8.e's harness queue,
8.f's surface lanes, 8.d's model, 8.g, 8.h or 7.c. The canon is
`src/vibey_tools/gh/docs/doctrines.md` (7.c `:82-91`; 8.a `:99`; 8.b `:120-194`; 8.c
`:196-234`; 8.d `:236-269`; 8.e `:271-292`; 8.f `:294-314`; 8.g `:316-324`; 8.h `:326-333`).
The operator's rulings of 2026-09-22 (STORM-CONTEXT.md) are facts the briefs may state; open
rulings (`STORM/specs/gap-ops-canon-rulings.md`) are not, and 8.c's heading (its item 1) is
not quoted.

Ownership: ADR-0046's docs lane owns the "Engines" and "Rotation" bullets and the
"Workspace tenants" list; ADR-0047's (`surfaces-docs`) owns surface-lane configuration. This
lane leaves those bullets as it finds them. `gap-sd01-carriage` added SD-01 to AGENTS.md and
GEMINI.md; this lane keeps that text byte-for-byte.

## Required behaviour
1. **ADR numbers.** Resolve each with `ls` and use the four digits (`ADR-NNNN`):
   `A7C`=`*-the-thorough-ledger.md`, `A8D`=`*-the-default-model-is-chosen-by-measurement.md`,
   `A8G`=`*-always-measured.md`, `A8H`=`*-arch-linux-and-macos-are-the-default-operating-systems.md`,
   `AORM`=`*-persistence-goes-through-the-orm.md`, `AINST`=`*-vibey-install-installs-the-local-stack.md`
   (all in `docs/architecture/decisions/`). If one is missing, STOP and report which.
2. **The loop name.** If `src/vibey_runners/sovereign` exists, write `` `sovereignloop` ``
   below. Otherwise write `` `sovereignloop` (named `qwenloop` in code until ADR-0046's rename lands) ``
   the first time it appears in each file, and `` `sovereignloop` `` after that.
3. **Intro.** Replace `CLAUDE.md:3-10` and `AGENTS.md:3-9` (from `` `vibey`: a queue-based `` to
   `Python 3.12+.`) with:
   ```
   `vibey`: a queue-based, six-phase conductor for autonomous software delivery.
   PostgreSQL holds the record and the ledger; RabbitMQ dispatches the work (ADR-0044).
   Engines run in two loops — `sovereignloop`, the default, and the declared-only
   `paidloop` — whose adapters live in this repository under `src/vibey_runners/`
   (sub-doctrine 8.c). It orchestrates design → build → review with an optional
   visual-design interstitial, plus an opt-in deployment stage set (self-hosted
   OpenStack by default). One distribution — `pip install vibey` delivers the whole
   family, engines and tools included (ADR-0037). Python 3.12+, on Arch Linux and
   macOS (8.h).
   ```
   Replace `GEMINI.md:3-9` (the paragraph from its first line through the line that ends
   with `.cursor/rules/`).`) with the same nine lines, followed by this line:
   ```
   Facts only — procedures live in `.agent/rules/` (mirrors of `.claude/skills/` and `.cursor/rules/`).
   ```
4. **The law.** Insert this section in all three files immediately before `## Layer map`
   (with the ADR numbers from step 1 filled in):
   ```
   ## The law 3.0.0 runs under

   The canon is `src/vibey_tools/gh/docs/doctrines.md`; these are its operational facts.

   - **Sovereign first, paid declared-only (8.a, 8.b).** Every surface defaults to a
     self-hosted, free implementation, always on: engines `sovereignloop`; cloud
     OpenStack; forge Forgejo; ticketing Plane; documentation BookStack; secrets
     OpenBao; files Nextcloud; email self-hosted SMTP; SMS Kannel; messaging Matrix;
     configuration Infisical; cache Valkey (the Redis protocol); bus RabbitMQ; blob
     storage Garage; security events Wazuh. A paid platform is a declared relay
     through the sovereign host. Where one is declared without naming which, the
     default is Claude (`paidloop` through `claudeloop`), VS Code (IDE), AWS (cloud)
     and GitHub (forge). OpenCode is repealed. ADR-0042.
   - **Two loops, one instance per model, fed by queues (8.c).** `sovereignloop`
     (always on) and `paidloop` (declared-only: `claudeloop`, `codexloop`,
     `cursorloop`, `agyloop`, VS Code on a paid provider). Nothing starts a second
     instance to go faster: work waits on the loop's RabbitMQ queue, with dead-letter
     queues and idempotency. ADR-0044, ADR-0046.
   - **This era's default model (8.d):** GPT-OSS 20B (`gpt-oss:20b`) on Ollama,
     chosen by measurement; a machine it does not fit gets its RAM tier's default.
     ADR-A8D.
   - **The test harness runs once per machine, fed by a queue (8.e).** A root pytest
     run is a harness request, answered from the record while it is valid and
     otherwise run once; `VIBEY_HARNESS_ROUTE=off` runs directly. ADR-0045.
   - **Every sovereign surface runs in one lane, driven by the bus (8.f).** ADR-0047.
   - **Always measured (8.g).** Every loop, lane, queue, surface, test run and model
     records latency, throughput, depth, waiting, resource use and outcome, and those
     measurements join the ledger. ADR-A8G.
   - **Arch Linux and macOS (8.h)** are the default operating systems; every change is
     proven on both (`gates (Arch Linux)`, `gates (macOS)`), and `vibey install`
     installs the local stack on both. ADR-A8H, ADR-AINST.
   - **The thorough ledger (7.c).** Record everything that can be recorded, append-only;
     secrets, credentials and people's private details are redacted, and each
     redaction is recorded. ADR-A7C.
   - **Tests need nothing outside the process.** Every seam has a registered in-memory
     fake (`tests/fakes/registry.py`); tests substitute only at declared seams — no
     `monkeypatch.setattr` of an import, no `mock.patch`, no MagicMock as a port.
     Real services are the opt-in `integration` tier (`-m integration`). ADR-0045
     (amendment); sub-doctrine 9.b.
   - **Persistence goes through the ORM,** SQLAlchemy 2 async on asyncpg behind
     declared interfaces; no new raw SQL (the exemptions are `LISTEN` and the
     migrator's scripts). ADR-AORM.
   ```
5. **AGENTS.md's old sovereign bullet** (`:90-104`, from `- **Sovereign self-hosted free is the only default` to `sub-doctrine 8.b, ADR-0042.`) is deleted: the new section states it.
6. **Queue backend.** Replace the bullet in each file:
   - `CLAUDE.md:140-141` and `AGENTS.md:154-156` (`- **Queue backend:** …` through `see ADR-0002.`) with:
     ```
     - **Queue backend:** a port with two backends (ADR-0044). RabbitMQ dispatches by
       default (`[queue] backend = "rabbitmq"`, broker at `VIBEY_BUS_AMQP_URL`);
       PostgreSQL stays selectable (`backend = "postgres"`, `FOR UPDATE SKIP LOCKED`,
       ADR-0002) and is the record store and the ledger under both. PostgreSQL 14+
       (CI exercises 14–18; the chart defaults to 17), never SQLite.
     ```
   - `GEMINI.md:84` with `- **Queue:** a port. RabbitMQ dispatches by default; PostgreSQL stays selectable and is always the record and the ledger (ADR-0044; never SQLite).`
   First confirm the default: `uv run python -c "from vibey.domain.config import QueueConfig; print(QueueConfig().backend)"`
   must print `rabbitmq`; if not, STOP and report.
7. **Commands block**, in each file:
   - The comment line that contains `the 7-gate sweep over src/vibey` (and, in AGENTS.md, the
     comment line after it, which mentions `postgres-compatibility`) becomes:
     ```
     # CI job `gates`: the 7-gate sweep over src/vibey. It starts no service; the
     # `integration` tier runs in `postgres-compatibility` (PostgreSQL 14–18). The same
     # sweep runs as `gates (Arch Linux)` and `gates (macOS)` (8.h).
     ```
   - Directly above the line `uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=`, add:
     `# A root pytest run is one test-harness request (8.e, ADR-0045); VIBEY_HARNESS_ROUTE=off runs it directly.`
   - Directly above the comment line that contains `(runs first)`, add:
     ```
     # A new machine: `vibey install` installs the local stack on Arch Linux or macOS (ADR-AINST).
     ```
8. **Maintenance line.** `CLAUDE.md:227-228` and `AGENTS.md:243-244` become:
   `**Agent-surface maintenance:** when a skill/procedure changes, update every agent-surface tree — Claude, Cursor, Codex, Antigravity, and any other tree the tree-parity meta-test lists — in the same PR.`
   (In AGENTS.md keep its `**Maintenance:**` label.)

## Where to change
- `CLAUDE.md`, `AGENTS.md`, `GEMINI.md` (edit_file only; each is over 100 lines). Do not touch
  anything between `<!-- vibey:begin -->` and `<!-- vibey:end -->`, the SD-01 text, the
  "Engines" and "Rotation" bullets, or the "Workspace tenants" list.

## Acceptance criteria
- [ ] `grep -c "## The law 3.0.0 runs under" CLAUDE.md AGENTS.md GEMINI.md` prints 1 for each.
- [ ] `grep -n "ADR-A[0-9A-Z]*\b" CLAUDE.md AGENTS.md GEMINI.md` prints nothing (every placeholder resolved).
- [ ] `grep -c "Subdoctrine SD-01 — Counterparties, Trust, and Verification" CLAUDE.md AGENTS.md GEMINI.md`
      prints the same numbers before and after the change.
- [ ] `grep -n "six .\*loop\|SKIP LOCKED. is$\|free Bitwarden" CLAUDE.md AGENTS.md GEMINI.md` prints nothing.
- [ ] The text between `<!-- vibey:begin -->` and `<!-- vibey:end -->` is unchanged (`git diff` shows no line there).
- [ ] `uv run pytest -q -p no:cacheprovider -n 0 tests/meta` passes (ADR counts, SD-01 carriage, tree parity).

## Tests to write first (TDD)
None new. `tests/meta` (including `gap-sd01-carriage`'s test) is the check.

## Checks the lane must run (all must pass)
    uv run python -c "from vibey.domain.config import QueueConfig; print(QueueConfig().backend)"
    ls docs/architecture/decisions/
    uv run pytest -q -p no:cacheprovider -n 0 tests/meta
    git diff --stat

## Out of scope
- The "Engines" and "Rotation" bullets and the tenant list (ADR-0046's docs lane); surface-lane
  commands and keys (`surfaces-docs`); the skill trees (`gap-docs-skill-trees-*`).
- 8.c's heading, which is an open ruling; SD-01's text (`gap-sd01-carriage`).

Commit as `docs(agents): CLAUDE.md, AGENTS.md and GEMINI.md state 3.0.0's law`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
