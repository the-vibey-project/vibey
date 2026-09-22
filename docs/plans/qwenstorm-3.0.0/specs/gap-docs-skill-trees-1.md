## Title
docs(skills): the vibey-testing skill teaches the fakes-first tiers and the harness queue, in all four trees

## Why
The `vibey-testing` skill predates 8.e and the fakes standard (`issue-audit/gaps.md` M3,
lines 639-642). `.claude/skills/vibey-testing/SKILL.md:30` says "**Every session needs
Postgres**"; `:86-96` says db tests run against real Postgres "never mocked" without the
opt-in tier; nothing mentions `vibey test`, the harness queue or the fake registry. After
`fakes-ci-no-services`, the default tier needs no service (`pyproject.toml` `addopts` excludes
`integration`), and after `harness-T28-route-flip` a root pytest run is a harness request
(8.e, `src/vibey_tools/gh/docs/doctrines.md:271-292`; ADR-0045 and its amendment).

The skill lives in four trees that must say the same thing (CLAUDE.md, "Agent-surface
maintenance"): `.claude/skills/vibey-testing/SKILL.md`, `.agents/skills/vibey-testing/SKILL.md`,
`.cursor/rules/vibey-testing.mdc`, `.agent/rules/vibey-testing.md`. Their bodies are identical
below each tree's own header; `gap-agent-tree-parity`'s meta-test holds that, and
`gap-sd01-carriage` added SD-01 to three of them. This lane applies the same replacements to
all four, so headers and the SD-01 text are untouched.

## Required behaviour
1. Confirm the facts first; if either differs, use what the tree says and report it:
   - `grep -n "^addopts" pyproject.toml` shows `-m 'not paid and not integration'`;
   - `uv run vibey test --help` lists `run`, `status`, `dead-letters` and `requeue`.
2. Write this script to `.qwenstorm/skill_edit.py` and run `python3 .qwenstorm/skill_edit.py`.
   It applies the same replacements to all four files and asserts each `old` occurs exactly
   once in each (EDITING-RULES rule 2). `A_OLD_START`/`A_OLD_END` bound the "Running locally"
   body (`.claude/skills/vibey-testing/SKILL.md:27-55`).
   ~~~python
   from pathlib import Path

   FILES = [".claude/skills/vibey-testing/SKILL.md", ".agents/skills/vibey-testing/SKILL.md",
            ".cursor/rules/vibey-testing.mdc", ".agent/rules/vibey-testing.md"]
   A_OLD_START = "The default `addopts` are"
   A_OLD_END = "PostgreSQL 14, 15, 16, 17, and 18.\n"
   A_NEW = """The default `addopts` select `-m 'not paid and not integration'` under pytest-xdist. The
   default tier needs **nothing outside the process**: no PostgreSQL, no broker, no engine
   binary, no network. Every seam has a registered in-memory fake (`tests/fakes/registry.py`),
   and a test substitutes only at a declared seam: a constructor argument, the typer
   context's `obj`, or a factory. Never `monkeypatch.setattr` an import, never `mock.patch`,
   never a MagicMock standing in for a port (ADR-0045's amendment; sub-doctrine 9.b).

   The `integration` tier is opt-in: `-m integration` selects the tests that need a real
   service, each named by a `VIBEY_TEST_*` variable (for example `VIBEY_TEST_DATABASE_URL`,
   `VIBEY_TEST_AMQP_URL`); a test whose variable is unset skips. The PostgreSQL role must be
   able to run `CREATE DATABASE`: the session migrates a `vibey_test_template` once and
   clones one database per xdist worker. Two checkouts whose `migrations/` differ each set
   `VIBEY_TEST_TEMPLATE_DB` to a name of their own. On Arch Linux or macOS, `vibey install`
   installs and starts PostgreSQL and RabbitMQ.

   ```bash
   uv run pytest tests/domain -p no:cacheprovider                          # default tier
   VIBEY_TEST_DATABASE_URL="postgresql://$(whoami)@localhost:5432/vibey_test" \\
     uv run pytest -m integration tests/infrastructure/db -p no:cacheprovider
   uv run pytest tests/domain -o addopts="" -m "not paid and not integration"   # serial, for a debugger
   ```

   Overriding `addopts` also drops the tier selection; keep the `-m`. CI's `gates` job starts
   no service; `postgres-compatibility` runs `-m "integration and not paid"` on PostgreSQL 14,
   15, 16, 17 and 18, and the RabbitMQ tier has its own broker job. The same sweep runs as
   `gates (Arch Linux)` and `gates (macOS)` (8.h).

   ## The test harness runs once per machine (8.e)

   A root `pytest` run is a **test-harness request** (ADR-0045). A run is keyed by what it
   tests (the working tree, the selection and the environment), so the same run asked twice
   is answered once: while the recorded result is valid it is returned (`reused`), otherwise
   the one harness instance runs it (`executed`). A run that crashes the harness, exceeds its
   bound or cannot run is parked on a dead-letter queue with its evidence.

   ```bash
   uv run vibey test run -- -q tests/domain     # one request; prints its answer
   uv run vibey test status                     # the machine lock's holder, and what runs
   uv run vibey test dead-letters               # parked runs; `vibey test requeue RUN_ID` grants one
   VIBEY_HARNESS_ROUTE=off uv run pytest ...    # bypass the harness
   VIBEY_HARNESS_ROUTE=locked uv run pytest ... # serialize only, no queue
   ```

   `[test_harness]` in `vibey.toml` and its `VIBEY_HARNESS_*` variables set the backend
   (`auto` falls back, loudly, to the local lock when no broker answers), the reuse window and
   the bounds (see `docs/reference/configuration.md`). The pre-push hook sends one request
   carrying the four coverage gates. A test of the harness points `VIBEY_HARNESS_STATE_DIR`
   at `tmp_path` and never touches the machine's real lock.
   """
   PAIRS = [
       ("| `tests/fakes/` | Shared fakes and `test_port_parity.py`, which fails when a fake misses a Protocol method |",
        "| `tests/fakes/` | Every in-memory fake, and `registry.py`, which names the fake for each seam; `test_port_parity.py` fails when a fake misses a Protocol method |"),
       ("| `tests/contracts/` | The same contract run against a fake and the Postgres implementation |",
        "| `tests/contracts/` | One contract suite run against the fake and the real implementation (the queue: both backends, ADR-0044 §16) |"),
       ("## Postgres integration tests — never mocked", "## The integration tier — real services, never mocked"),
       ("All `tests/infrastructure/db/` tests run against a **real ephemeral Postgres**",
        "The `integration` tests under `tests/infrastructure/db/` run against a **real ephemeral Postgres**"),
       ("matters: **zero double-commit, zero lost jobs** across 500 jobs.",
        "matters: **zero double-commit, zero lost jobs** across 500 jobs. Its twin,\n"
        "`tests/infrastructure/queue/test_rabbitmq_chaos.py`, proves the same tally against a\n"
        "real broker (ADR-0044; `integration` tier)."),
       ("- `@pytest.mark.integration` — requires Postgres (auto-applied to everything\n"
        "  under `tests/infrastructure/db/` by conftest).",
        "- `@pytest.mark.integration` — needs a real service (PostgreSQL, RabbitMQ); excluded\n"
        "  by default, opt in with `-m integration`."),
   ]
   for name in FILES:
       path = Path(name)
       text = path.read_text(encoding="utf-8")
       start = text.index(A_OLD_START)
       end = text.index(A_OLD_END, start) + len(A_OLD_END)
       assert text.count(A_OLD_START) == 1, (name, "A")
       text = text[:start] + A_NEW + text[end:]
       for old, new in PAIRS:
           assert text.count(old) == 1, (name, old[:40])
           text = text.replace(old, new)
       path.write_text(text, encoding="utf-8")
       print("edited", name)
   ~~~
   The `A_NEW` text is written flush-left in the file: remove the three-space indentation this
   spec gives every line of the script when you write it.
3. If `tests/infrastructure/queue/test_rabbitmq_chaos.py` does not exist, drop the pair whose
   `old` begins `matters: **zero double-commit`, and say so in the verdict.

## Where to change
- The four files above, by the script only. Nothing else.

## Acceptance criteria
- [ ] The script asserts `count == 1` for every pair in every file, and succeeds.
- [ ] `grep -c "Every session needs Postgres" .claude/skills/vibey-testing/SKILL.md .agents/skills/vibey-testing/SKILL.md .cursor/rules/vibey-testing.mdc .agent/rules/vibey-testing.md` prints 0 four times.
- [ ] `grep -c "## The test harness runs once per machine (8.e)"` prints 1 in each of the four files.
- [ ] `git diff` changes no line above each file's `# vibey testing` title and no SD-01 line.
- [ ] `uv run pytest -q -p no:cacheprovider -n 0 tests/meta` passes (tree parity, SD-01 carriage).

## Tests to write first (TDD)
None new: `gap-agent-tree-parity`'s and `gap-sd01-carriage`'s meta-tests hold the four trees.

## Checks the lane must run (all must pass)
    grep -n "^addopts" pyproject.toml
    uv run vibey test --help
    python3 .qwenstorm/skill_edit.py
    uv run pytest -q -p no:cacheprovider -n 0 tests/meta
    git diff --stat

## Out of scope
- Every other skill (`gap-docs-skill-trees-2` to `-4`; `vibey-engine-adapters` is ADR-0046's
  docs lane). CONTRIBUTING.md (`gap-docs-contributing`). The tree headers and SD-01.

Commit as `docs(skills): the vibey-testing skill teaches the fakes-first tiers and the harness queue`. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
