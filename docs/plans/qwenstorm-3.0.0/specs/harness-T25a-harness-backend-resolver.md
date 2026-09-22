## Title
feat(test-harness): choose the harness backend — auto degrades, announced; rabbitmq never does

## Why
Draft ADR-0045 §3 defines the three backends:
- **`auto`** (the default) uses the machine's queue when `[bus] amqp_url` resolves, the broker
  answers, and a service consumes the queue. Otherwise it uses the machine lock, and **says so, and
  why**. It is not the silent fallback ADR-0002 and ADR-0044 §1 forbid: the answer's second line
  names the reason (10.f), and both paths take the same machine lock and write the same store, so
  choosing either can neither run two tests at once nor split the record.
- **`rabbitmq`** never degrades: without a URL it fails, naming the remedies, as ADR-0044 §1 does
  for `QueueBackendNotConfigured` (rmq-r17).
- **`local`** never touches the broker.

The decision is small and pure given its probe, so it is its own class, tested by a table, before
the composition (harness-T25b) wires it.

## Required behaviour
Create `src/vibey/infrastructure/test_harness/backend.py`:
1. **`TestHarnessBackendResolver`**, stateless, with the class constant
   `NOT_CONFIGURED: ClassVar[str] = "the rabbitmq test-harness backend needs a broker URL: export VIBEY_BUS_AMQP_URL=amqp://USER:PASS@HOST:5672/ or export VIBEY_HARNESS_BACKEND=local"`
   (harness-T25b raises the same text when a service is asked for without a URL).
   `async def resolve(self, *, backend: str, amqp_url: str | None, probe: Callable[[], Awaitable[str | None]]) -> tuple[str, str | None]`:
   - `local` → `("local", None)`, never calling `probe`;
   - `rabbitmq` with no URL (`None` or blank) → raise `TestHarnessNotConfigured(self.NOT_CONFIGURED)`
     (`vibey.infrastructure.test_harness.settings`, harness-T05); the message holds both remedies
     verbatim: `export VIBEY_BUS_AMQP_URL=amqp://USER:PASS@HOST:5672/` and
     `export VIBEY_HARNESS_BACKEND=local`;
   - `rabbitmq` with a URL → `("rabbitmq", None)`, without probing;
   - `auto` with no URL → `("local", "backend=local (auto: no [bus] amqp_url is configured)")`;
   - `auto` with a URL → `reason = await probe()`; `None` → `("rabbitmq", None)`, otherwise
     `("local", f"backend=local (auto: {reason})")`;
   - any other backend → `ValueError` naming it.
2. **The interface** `src/vibey/infrastructure/test_harness/interfaces/backend_interface.py`:
   `@runtime_checkable` `TestHarnessBackendResolverInterface` (`resolve`).

## Where to change
- New `src/vibey/infrastructure/test_harness/backend.py` and its interface module.
- New `tests/infrastructure/test_harness/test_backend.py`.

## Acceptance criteria
- [ ] The resolver table holds for every row, including that `local` and `rabbitmq` never call the probe (a recording probe).
- [ ] The not-configured message contains both remedies verbatim.
- [ ] 100% coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/test_harness/test_backend.py` (`from vibey.infrastructure.test_harness import backend as hb`):
- `test_resolver_table` (parametrized over every row)
- `test_rabbitmq_without_a_url_names_both_remedies`
- `test_local_and_rabbitmq_never_probe`
- `test_an_unknown_backend_is_refused`
- `test_resolver_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_harness
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Wiring it into the composition (harness-T25b) and the `serve` command (harness-T25).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** harness-T05-test-harness-config.
- **Files touched:** the two new source files and the new test file.
- **Shares a file with:** none.
- **Must keep passing unchanged:** harness-T05's tests, and the protected tests.
- **Registry (amendment A4):** nothing. The resolver is a pure policy over an injected probe (`PURE_POLICY`), not a seam.
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - In test files import modules, not `Test*` names.
  - Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`; default-tier tests need nothing outside the process (ADR-0045 amendment A1; lane fakes-isolation-guard's audit hook fails a default-tier test that reaches out).
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
