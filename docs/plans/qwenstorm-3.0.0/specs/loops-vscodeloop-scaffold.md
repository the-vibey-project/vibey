## Title
feat(vscodeloop): the vscodeloop runner tenant and its pure run rules

ADR-0046 lane L20d (slug `loops-vscodeloop-scaffold`).

## Why
ADR-0046 §8 (`specs/ADR-two-loops.md:263-272`) adds a new runner tenant, `vscodeloop`
(`src/vibey_runners/vscode`, own gates per ADR-0022), that follows the family contract: the
verbs `run`, `resume`, `doctor`, `prompt`, `stop`; run directories at
`.vscodeloop/runs/<run_id>/`; the done marker `VSCODELOOP_TASK_FULLY_COMPLETE`; exit codes 0,
1, 75 (wind-down) and 78 (misconfigured). "Its bounds (turns, seconds, stall) and its one pure
terminal-status rule are the ones the dropped `specs/opencodeloop-parity-p1.md` specified. The
first check of that rule is 'a capacity rejection gives FAILED', ahead of any completion claim"
(non-negotiable 3: a capacity rejection always outranks a completion claim).

Sub-doctrine 10.e: the run-id validator is not copied a sixth time; lane `loops-runid-common`
put `RunId` in `vibey_runners.common.domain`. This lane creates the tenant with its pure domain
and its packaging; the run store, runner, CLI, driver and doctor follow in their own lanes.

## Required behaviour
0. **Gate (ADR-0046 §8, CDD bounded divergence).** Before any edit run
   `grep -n "V-VS VERDICT: FEASIBLE" STORM/specs/ADR-two-loops.md docs/architecture/decisions/0046-*.md`.
   If nothing matches, change nothing and report `gated: V-VS verdict is not FEASIBLE`.
1. **Tenant layout** (new files; line 1 of every `.py` is the provenance comment copied
   byte-for-byte from line 1 of `src/vibey_runners/opencode/src/opencodeloop/domain/model.py`):
   ```
   src/vibey_runners/vscode/pyproject.toml
   src/vibey_runners/vscode/README.md
   src/vibey_runners/vscode/LICENSE            (byte-for-byte copy of src/vibey_runners/sovereign/LICENSE, the MIT text)
   src/vibey_runners/vscode/src/vscodeloop/__init__.py        (__version__ = "0.1.0")
   src/vibey_runners/vscode/src/vscodeloop/py.typed           (empty)
   src/vibey_runners/vscode/src/vscodeloop/domain/__init__.py
   src/vibey_runners/vscode/src/vscodeloop/domain/model.py
   src/vibey_runners/vscode/src/vscodeloop/domain/interfaces/__init__.py
   src/vibey_runners/vscode/src/vscodeloop/domain/interfaces/model_interface.py
   src/vibey_runners/vscode/tests/test_domain.py
   ```
2. **`pyproject.toml`**: copy `src/vibey_runners/opencode/pyproject.toml` (80 lines at
   integration `d3b4a388`) and change: `name = "vscodeloop"`; `description = "A contract-preserving Vibey runner that drives Code - OSS (VSCodium) agent sessions."`;
   keywords `["ai-agent", "coding-agent", "vscode", "vscodium", "vibey"]`; `dependencies =
   ["typer>=0.12"]` (NO `vibey-runners-common`: it is not on an index, ADR-0037 — see the
   comment at `src/vibey_runners/claude/pyproject.toml:53-56`, copy it); dev extras add
   `"pytest-asyncio>=0.24"`; **no `[project.scripts]` yet** (lane `loops-vscodeloop-cli` adds
   it with the CLI); `packages = ["src/vscodeloop"]`; mypy `packages = ["vscodeloop"]`;
   `addopts = "--cov=vscodeloop --cov-branch --cov-report=term-missing --cov-fail-under=100"`;
   coverage `source = ["src/vscodeloop"]`; `[tool.importlinter] root_package = "vscodeloop"`
   with the same "Onion layering" contract over `vscodeloop.cli`, `.infrastructure`,
   `.application`, `.domain` (importing `vibey_runners.common` is allowed from any layer: it
   declares `dependencies = []`).
3. **`domain/model.py`** — pure; no I/O, clock or subprocess:
   ```python
   DONE_MARKER = "VSCODELOOP_TASK_FULLY_COMPLETE"
   EXIT_CODE_FINISHED = 0
   EXIT_CODE_FAILED = 1
   EXIT_CODE_USAGE = 2
   EXIT_CODE_WIND_DOWN = 75  # EX_TEMPFAIL, the family's hand-over code (vibey domain/engine.py:16)
   EXIT_CODE_MISCONFIGURED = 78  # EX_CONFIG (vibey domain/engine.py:23)

   class RunStatus(StrEnum): ACTIVE = "active"; FINISHED = "finished"; FAILED = "failed"; STOPPED = "stopped"
   class StopReason(StrEnum): WIND_DOWN = "wind_down"; MAX_TURNS = "max_turns"; MAX_SECONDS = "max_seconds"; STALL_TIMEOUT = "stall_timeout"

   @dataclass(frozen=True, slots=True)
   class RunBounds:
       max_turns: int = 40
       max_seconds: float = 3600.0
       stall_timeout_seconds: float = 900.0
       # __post_init__: ValueError naming the field when max_turns < 1 or either float <= 0

   class CompletionMarker:
       def __init__(self, marker: str = DONE_MARKER) -> None: ...
       def claimed_by(self, text: str) -> bool:  # any(line.strip() == marker for line in text.splitlines())

   class TerminalRule:
       def decide(self, *, capacity_rejected: bool, stop_reason: StopReason | None,
                  misconfigured: bool, driver_failed: bool, completion_claimed: bool) -> RunStatus:
           # In this order; the first that holds decides:
           # capacity_rejected -> FAILED (a capacity rejection outranks a completion claim)
           # stop_reason is WIND_DOWN -> STOPPED
           # stop_reason is any other bound -> FAILED
           # misconfigured -> FAILED
           # driver_failed -> FAILED
           # not completion_claimed -> FAILED
           # else FINISHED

   @dataclass(frozen=True, slots=True)
   class RunResult:
       status: RunStatus
       session_id: str | None = None
       detail: str = ""
       stop_reason: StopReason | None = None
       misconfigured: bool = False

       @property
       def exit_code(self) -> int:
           # FINISHED -> 0; STOPPED -> 75; misconfigured -> 78; anything else -> 1
   ```
   The completion claim is read from the session's **last** assistant text only (the runner
   lane passes it); a `CompletionMarker` never looks at tool output.
4. **`domain/interfaces/model_interface.py`**: `@runtime_checkable` Protocols
   `RunBoundsInterface`, `CompletionMarkerInterface` (`claimed_by`), `TerminalRuleInterface`
   (`decide`), `RunResultInterface` (the five fields and `exit_code`). Copy the layout of
   `src/vibey_runners/opencode/src/opencodeloop/domain/interfaces/model_interface.py`.
   Export all names from both `__init__.py` files.
5. **Root packaging** (edit_file each):
   - `pyproject.toml` `[tool.hatch.build.targets.wheel] packages` (`:200-212` at `d3b4a388`,
     after the qwen/sovereign entry): `"src/vibey_runners/vscode/src/vscodeloop",`; and
     `[tool.hatch.build.targets.wheel.sources]` (`:225-236`):
     `"src/vibey_runners/vscode/src/vscodeloop" = "vscodeloop"`. Update the comment's count of
     package roots if it states one ("eleven" becomes "twelve").
   - `deploy/docker/Dockerfile`: `COPY src/vibey_runners/vscode/pyproject.toml ./src/vibey_runners/vscode/`
     after the qwen/sovereign pyproject COPY (`:132`), and
     `COPY src/vibey_runners/vscode/src/vscodeloop/ ./src/vibey_runners/vscode/src/vscodeloop/`
     after the qwen/sovereign source COPY (`:142`).
   - `.github/workflows/ci.yml` tools matrix: three rows after the sovereign (qwen) rows
     (`:531-546`), for Python 3.12, 3.13 and 3.14:
     ```yaml
     - package: vscodeloop
       dir: src/vibey_runners/vscode
       python: "3.12"
       install: 'pip install -e ../common && pip install -e ".[dev]"'
       static: 'mypy --strict src/vscodeloop && lint-imports && bandit -q -r src/vscodeloop'
       test: 'python -m pytest -q'
     ```
     (the 3.13 and 3.14 rows have no `static`, like qwen's).
   - `src/vibey_runners/common/pyproject.toml` "Shared code depends on no concrete runner"
     `forbidden_modules`: add `"vscodeloop"`.
   - Run `uv lock` (the workspace glob `src/vibey_runners/*` registers the member,
     `pyproject.toml:251`), and commit `uv.lock`.

## Where to change
The new tenant files in behaviour 1; `pyproject.toml`; `deploy/docker/Dockerfile`;
`.github/workflows/ci.yml`; `src/vibey_runners/common/pyproject.toml`; `uv.lock`.

## Acceptance criteria
- [ ] `cd src/vibey_runners/vscode && pip install -e ../common && pip install -e ".[dev]" && python -m pytest -q` passes at 100% branch coverage (the addopts floor).
- [ ] `mypy --strict src/vscodeloop && lint-imports && bandit -q -r src/vscodeloop` pass in the tenant.
- [ ] `TerminalRule().decide(capacity_rejected=True, stop_reason=None, misconfigured=False, driver_failed=False, completion_claimed=True) is RunStatus.FAILED`.
- [ ] `RunResult(RunStatus.STOPPED, stop_reason=StopReason.WIND_DOWN).exit_code == 75`; a misconfigured failure is 78.
- [ ] `uv lock --check` passes; `uv run pytest -q -p no:cacheprovider tests/meta` passes (tools matrix membership and floor, shipped trees reachable).

## Tests to write first (TDD)
`src/vibey_runners/vscode/tests/test_domain.py`:
- `test_run_bounds_defaults` (40 / 3600.0 / 900.0).
- `test_run_bounds_rejects_invalid_values` (parametrized: `max_turns=0`, `max_seconds=0`, `stall_timeout_seconds=-1`; each `ValueError` names its field).
- `test_completion_marker_requires_its_own_line` (`"done\nVSCODELOOP_TASK_FULLY_COMPLETE\n"` True; padded marker line True; marker inside a sentence False; `""` False).
- `test_terminal_rule_capacity_outranks_a_completion_claim`.
- `test_terminal_rule_wind_down_is_stopped`.
- `test_terminal_rule_fails_on_a_bound_misconfiguration_driver_failure_or_missing_claim` (parametrized).
- `test_terminal_rule_finishes_only_with_a_claim_and_nothing_else`.
- `test_exit_codes_follow_the_family` (0, 75, 78, 1).
- `test_domain_classes_satisfy_their_interfaces`.
- `test_run_id_comes_from_the_family` (`from vibey_runners.common.domain import RunId`; `RunId.parse("../x")` raises `ValueError`) — proves the tenant uses the shared validator.

## Checks the lane must run (all must pass)
    cd src/vibey_runners/vscode && pip install -e ../common && pip install -e ".[dev]" && python -m pytest -q
    cd src/vibey_runners/vscode && mypy --strict src/vscodeloop && lint-imports && bandit -q -r src/vscodeloop
    uv lock --check
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/meta
    uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"

## Out of scope
- The run store, runner, CLI, driver and doctor (lanes `loops-vscodeloop-run-store` …
  `loops-vscodeloop-doctor`); the console script (`loops-vscodeloop-cli`).
- Any vibey-side wiring (`loops-vscode-engine-ids`, `loops-vscode-vibey-wiring`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.
- Do not push or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-vscode-spike`, `loops-runid-common`, `loops-tenant-rename`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
