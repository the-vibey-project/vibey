## Title
feat(domain): what a test run is, how it is keyed, and how its outcome is classified

## Why
Sub-doctrine 8.e is ratified on the integration branch
(`src/vibey_tools/gh/docs/doctrines.md:271-292`): the test harness runs one test run at a time
per machine, fed by a queue, and "a run is identified by what it tests — the tree, the
selection of tests and the environment — so the same run asked for twice is answered once".
Draft ADR-0045 (`specs/ADR-test-harness-queue.md`) §5 defines that key exactly, and §6 defines
how a pytest exit code becomes an outcome, using pytest's documented exit codes 0–5.

Both are pure rules, so they belong in `src/vibey/domain/` (CLAUDE.md: no I/O, no async, no
clock). `tests/domain/test_domain_purity.py:12-36` walks every file there and refuses
`asyncio`, `subprocess`, `socket`, any `pathlib` import (`:52-61`), `open()`, `os.environ`,
`os.getenv`, `datetime.now()` and `time.time()`. `hashlib`, `json`, `re`, `enum`,
`dataclasses` and `typing` are stdlib and allowed. This lane is the first harness lane; every
later one imports these types.

## Required behaviour
Create `src/vibey/domain/test_harness.py`. Every dataclass is `@dataclass(frozen=True, slots=True)`.
Every validation failure raises `ValueError` with a message naming the field.

1. **`CoverageGate`**: `include: str` (non-empty, contains neither `"\x00"` nor `"="`) and
   `fail_under: int` (0–100 inclusive; a `bool` is refused). The classmethod
   `parse(cls, text: str) -> CoverageGate` splits on the **last** `=`:
   `CoverageGate.parse("src/vibey/domain/*=100") == CoverageGate("src/vibey/domain/*", 100)`.
   Text with no `=`, an empty include, or a minimum that is not a decimal integer raises
   `ValueError(f"a gate is INCLUDE=MIN, got {text!r}")`.
2. **`TestSelection`**: `command: tuple[str, ...]` (non-empty), `argv: tuple[str, ...]`,
   `gates: tuple[CoverageGate, ...] = ()`. Any command or argv item containing `"\x00"` raises.
   - `CACHE_DEPENDENT_FLAGS: ClassVar[frozenset[str]]` is exactly `{"--lf", "--last-failed",
     "--ff", "--failed-first", "--nf", "--new-first", "--sw", "--stepwise", "--sw-skip",
     "--stepwise-skip"}`.
   - property `reusable -> bool`: `False` when any argv item is in that set, else `True`.
   - property `collects_coverage -> bool`: `True` when any argv item is `"--cov"` or starts
     with `"--cov="`.
3. **`EnvNamePatterns`**: `patterns: tuple[str, ...]`; each pattern must match
   `^[A-Za-z_][A-Za-z0-9_]*\*?$`.
   - `matches(self, name: str) -> bool`: a pattern ending in `*` is a prefix match on the text
     before the `*`; any other pattern is an exact match.
   - `select(self, environ: Mapping[str, str]) -> tuple[tuple[str, str], ...]`: the
     `(name, value)` pairs whose name matches any pattern, sorted by name.
4. **`ValueDigest`**, a stateless class with the static method
   `of(value: str) -> str` returning `hashlib.sha256(value.encode("utf-8")).hexdigest()`.
5. **`TestEnvironment`**: `python: str`, `distributions: str`, `database: str`,
   `env: tuple[tuple[str, str], ...]` (pairs of `(name, digest)`; names must be strictly
   increasing, so sorted and unique). The classmethod
   `from_values(cls, *, python: str, distributions: str, database: str, values: Sequence[tuple[str, str]]) -> TestEnvironment`
   digests each value with `ValueDigest.of` and sorts by name.
6. **`TestRunKey`**, a stateless class:
   - `SCHEMA: ClassVar[str] = "vibey.test.key/1"`.
   - `canonical(tree: str, selection: TestSelection, environment: TestEnvironment) -> str`
     (static) returns `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)` of
     ```python
     {"schema": "vibey.test.key/1", "tree": tree,
      "selection": {"command": list(selection.command), "argv": list(selection.argv),
                    "gates": [[g.include, g.fail_under] for g in selection.gates]},
      "environment": {"python": environment.python, "distributions": environment.distributions,
                      "database": environment.database,
                      "env": {name: digest for name, digest in environment.env}}}
     ```
   - `derive(tree, selection, environment) -> str` (static) returns
     `hashlib.sha256(canonical(...).encode("ascii")).hexdigest()`.
7. **`MachineLoad`**: `load1: float`, `load5: float`, `load15: float` (each ≥ 0) and
   `cpu_count: int | None`.
8. **`TestOutcome(StrEnum)`**: `PASSED = "passed"`, `FAILED = "failed"`, `CRASHED = "crashed"`,
   `TIMED_OUT = "timed_out"`, `UNEXECUTABLE = "unexecutable"`, `ABANDONED = "abandoned"`.
   - `is_reusable(self) -> bool` is true for `PASSED` and `FAILED` only;
   - `is_dead_letter(self) -> bool` is true for `CRASHED`, `TIMED_OUT` and `UNEXECUTABLE` only.
9. **`TestOutcomePolicy`**, stateless:
   `classify(self, exit_code: int | None, *, timed_out: bool, gate_failures: int) -> TestOutcome`,
   checked in this order:
   1. `timed_out` → `TIMED_OUT`;
   2. `exit_code is None`, or `exit_code < 0` (killed by a signal), or `exit_code == 3`
      (pytest internal error) → `CRASHED`;
   3. `exit_code == 0` and `gate_failures == 0` → `PASSED`;
   4. anything else → `FAILED` (0 with a failed gate, 1, 2, 4, 5 and every other positive code).
10. **`TestRouteMode(StrEnum)`**: `OFF = "off"`, `LOCKED = "locked"`, `QUEUE = "queue"`. The
    classmethod `parse(cls, text: str) -> TestRouteMode` strips and lower-cases its input;
    anything else raises
    `ValueError(f"vibey_harness_route must be one of off, locked, queue; got {text!r}")`.
11. **Interfaces.** Create `src/vibey/domain/interfaces/test_harness_interface.py` with
    `@runtime_checkable` Protocols. It must not import `vibey.domain.test_harness` at run time
    (use `from __future__ import annotations` and name other Protocols of this module, or
    import concrete types only under `if TYPE_CHECKING:`):
    - `CoverageGateInterface` (properties `include`, `fail_under`) — later lanes type gates with it;
    - `TestSelectionInterface` (properties `command`, `argv`, `gates`, `reusable`, `collects_coverage`);
    - `TestEnvironmentInterface` (properties `python`, `distributions`, `database`, `env`);
    - `EnvNamePatternsInterface` (`patterns` property, `matches`, `select`);
    - `ValueDigestInterface` (`of`);
    - `TestRunKeyInterface` (`canonical`, `derive`);
    - `TestOutcomePolicyInterface` (`classify`).
    `test_harness.py` imports this module (as `domain/circuit.py:13` imports its interface).

## Where to change
- New `src/vibey/domain/test_harness.py`. Copy the frozen, slotted dataclass and `StrEnum`
  style of `src/vibey/domain/circuit.py:1-30`.
- New `src/vibey/domain/interfaces/test_harness_interface.py`. Copy the docstring and Protocol
  layout of `src/vibey/domain/interfaces/circuit_interface.py`.
- New `tests/domain/test_test_harness.py`. Do not edit `src/vibey/domain/interfaces/__init__.py`;
  import from the module path.

## Acceptance criteria
- [ ] The canonical string for a fixed small example equals a literal written in the test.
- [ ] The key changes when any one component changes: the tree, a command item, an argv item, a gate, `python`, `distributions`, `database`, or one env value.
- [ ] The key does not change when the env values are given in a different order.
- [ ] The outcome table holds for every row.
- [ ] `uv run pytest -q -p no:cacheprovider tests/domain/test_domain_purity.py` passes; 100% coverage of `src/vibey/domain/`.

## Tests to write first (TDD)
`tests/domain/test_test_harness.py` imports `from vibey.domain import test_harness as th`
(never `from vibey.domain.test_harness import TestSelection`) and has:
- `test_gate_parse_splits_on_the_last_equals_sign`
- `test_gate_bounds_and_malformed_text` (parametrized: `"x=101"`, `"x=-1"`, `"=5"`, `"x"`, `"x=a"`, an include with `"\x00"`)
- `test_selection_rejects_nul_and_an_empty_command`
- `test_selection_is_not_reusable_with_a_cache_flag` (parametrized over the ten flags)
- `test_selection_collects_coverage` (`--cov`, `--cov=vibey` yes; `--cov-report=` no)
- `test_env_patterns_prefix_and_exact_matches`
- `test_env_patterns_reject_a_bad_pattern`
- `test_environment_from_values_digests_and_sorts`
- `test_environment_rejects_unsorted_or_duplicate_names`
- `test_canonical_json_is_exact`
- `test_key_changes_with_each_component` (parametrized)
- `test_key_ignores_env_order`
- `test_machine_load_rejects_negative_load`
- `test_outcome_table` (parametrized: `(None, False, 0)` crashed, `(-9, False, 0)` crashed, `(3, False, 0)` crashed, `(0, False, 0)` passed, `(0, False, 1)` failed, `1`, `2`, `4`, `5` and `7` failed, `(0, True, 0)` timed_out)
- `test_outcome_reusable_and_dead_letter_sets`
- `test_route_mode_parse` (`" Locked "` parses; `"sometimes"` raises with the exact message)
- `test_classes_satisfy_their_interfaces` (`isinstance` against each Protocol)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- Any I/O: the tree digest (harness-T08), the environment probe (harness-T09), files (harness-T10).
- The reuse policy (harness-T02) and the messages (harness-T03).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees; the docs wave owns them.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** none.
- **Files touched:** the three files above.
- **Shares a file with:** none.
- **Must keep passing unchanged:** `tests/domain/test_domain_purity.py`, every test under `tests/domain/`, and the protected tests.
- **Registry (amendment A4):** nothing. Every class here is a pure policy or a value (`PURE_POLICY` / `VALUE_CONTRACT`), not a substitution seam.
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file (`vibey-gh check` compares it exactly):
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - In test files import modules, not `Test*` names: pytest tries to collect every class whose name starts with `Test` in a test module's namespace.
  - Substitute only at a declared seam (a constructor or keyword argument). Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`/`AsyncMock`/`Mock`; `monkeypatch.setenv`, `delenv` and `chdir` are allowed.
  - Default-tier tests need nothing outside the process (ADR-0045 amendment A1; lane fakes-isolation-guard's audit hook fails a default-tier test that reaches out).
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
