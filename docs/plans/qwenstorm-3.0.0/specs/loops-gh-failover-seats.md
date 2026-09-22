## Title
feat(gh): the operator-seat failover defaults to sovereignloop, then vscodeloop

ADR-0046 lane L39b (slug `loops-gh-failover-seats`).

## Why
vibey-gh's failover engine (#208) hands the operator seat to "the first healthy local agent
(qwenloop, then opencode, by default)" (`src/vibey_tools/gh/vibey_gh/failover.py:4-5`, defaults at
`:81-86`, integration `d3b4a388`). After ADR-0046 both names are gone as tools: `qwenloop` is
renamed `sovereignloop` (lane `loops-tenant-rename`; the old script is only a deprecated alias
through 3.x), and `opencodeloop` is retired to a stub that exits 64 (lane
`loops-remove-opencode-tenant`), while OpenCode itself is repealed by sub-doctrine 8.b (#392).
The sovereign seat ladder of 10.a (hosted agent → open-source local agent → raw local model) now
reads sovereignloop's native agent, then Code - OSS on the local model (`vscodeloop`). Sub-doctrine
10.e: the family's own runners, not a third-party default.

The defaults are only defaults: the machine-level `failover.toml` still names any seat an operator
wants (`load`, `:73-95`).

## Required behaviour
1. `FailoverConfig.seats`' default factory (`failover.py:81-86`) returns
   `(Seat(name="sovereignloop", launch="sovereignloop run"), Seat(name="vscodeloop", launch="vscodeloop run"))`.
2. The module docstring's "(qwenloop, then opencode, by default)" (`:4-5`) reads
   "(sovereignloop, then vscodeloop, by default)".
3. The two existing assertions of the old defaults in `src/vibey_tools/gh/test/test_failover.py`
   (`:40-42`, and `:69`) expect `["sovereignloop", "vscodeloop"]`; the first test is renamed
   `test_the_default_seat_order_is_sovereignloop_then_vscodeloop`. No other edit to that file.
4. A config file that still names `qwenloop` or `opencode` seats keeps working exactly as written
   (the engine runs operator commands; it never validates names).

## Where to change
- `src/vibey_tools/gh/vibey_gh/failover.py` (docstring and the default factory).
- `src/vibey_tools/gh/test/test_failover.py` (the two assertions and one rename, plus the new test below appended).

## Acceptance criteria
- [ ] `[s.name for s in FailoverConfig().seats] == ["sovereignloop", "vscodeloop"]`.
- [ ] A `failover.toml` naming `qwenloop` loads that seat unchanged.
- [ ] vibey-gh's suite and linters pass (below).

## Tests to write first (TDD)
Append to `src/vibey_tools/gh/test/test_failover.py`:
- `test_an_operator_config_naming_legacy_seats_is_honoured` (writes a `failover.toml` with a
  `qwenloop` seat and asserts `load(where).seats == (Seat(name="qwenloop", launch="qwenloop run"),)`).

## Checks the lane must run (all must pass)
    (cd src/vibey_tools/gh && pip install -e ".[dev]" && python -m pytest -q test/test_failover.py)
    (cd src/vibey_tools/gh && python -m pytest -q)
    (cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh)
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- vibey-gh's documentation (`docs/cli.md:36`, `docs/configuration.md`): the docs wave.
- Routing the review lanes through sovereignloop (gap A5).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.
- Do not push or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-remove-opencode-tenant`, `loops-tenant-rename`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
