## Title
feat(sovereignloop): runs live in .sovereignloop/, the model cache under sovereignloop, and the done marker is SOVEREIGNLOOP_TASK_FULLY_COMPLETE, with every qwenloop location still read in place

ADR-0046 lane L18d (slug `loops-tenant-legacy-paths`).

## Why
Draft ADR-0046's *Migration* table (`specs/ADR-two-loops.md`) renames the runner's on-disk
names, each with a legacy read through 3.x:
- model cache `<cache>/qwenloop` becomes `<cache>/sovereignloop`, the old one "read while it
  exists; **never moved automatically** (ADR-0015 #5)": 13–16 GB is not re-downloaded silently;
- `.qwenloop/runs/<id>` becomes `.sovereignloop/runs/<id>`, the old one "read for resume, inbox
  and sessions";
- `QWENLOOP_TASK_FULLY_COMPLETE` becomes `SOVEREIGNLOOP_TASK_FULLY_COMPLETE`, and "the runner
  accepts either from the model".

At integration `d3b4a388` (tenant paths before lane L18a's move to
`src/vibey_runners/sovereign/src/sovereignloop`):
- `infrastructure/model_cache.py:25` `user_cache_path("qwenloop")`, `infrastructure/inference.py:68`
  the same, `cli/app.py:516` the same (`model remove`);
- `infrastructure/run_store.py:11` `cwd / ".qwenloop" / "runs"`; `cli/app.py:566` (`usage`),
  `:575` (`_control`: stop, wind-down) and `:593` (`prompt`) build `.qwenloop/runs/<id>/...`;
- `domain/model.py:10` `DONE_MARKER = "QWENLOOP_TASK_FULLY_COMPLETE"`; `application/runner.py:358`
  and `:369` test `DONE_MARKER in answer`, and `:51` spells the marker inside
  `_INVALID_COMPLETION_PROMPT`;
- vibey's descriptor (`src/vibey/infrastructure/engines/descriptors.py:290-316`) runs
  `binary="qwenloop"` and tails `state_dir=".qwenloop"` with
  `done_marker="QWENLOOP_TASK_FULLY_COMPLETE"`.

vibey tails `<cwd>/<descriptor.state_dir>/runs/<run_id>/events.jsonl`, so the runner's run
directory and vibey's `state_dir` must change in **one commit**; that is why this lane spans the
tenant and the descriptor. The descriptor's argv goldens
(`tests/infrastructure/engines/test_argv.py:31-38`, files
`tests/infrastructure/engines/golden/<engine_id.value>_<effort>.txt`) are named
`sovereignloop_*.txt` by lane L06 and still start with `qwenloop run`; they change here.
One class holds the fallback rule (9.b; 10.e: one rule, not five copies).

## Required behaviour
1. **`StatePaths`** (new, `sovereignloop/infrastructure/state_paths.py`, interface
   `StatePathsInterface` in `infrastructure/interfaces/state_paths_interface.py`):
   - constants `NAME = "sovereignloop"`, `LEGACY_NAME = "qwenloop"`,
     `STATE_DIR = ".sovereignloop"`, `LEGACY_STATE_DIR = ".qwenloop"`;
   - `StatePaths(*, cache_base: Callable[[str], Path] = user_cache_path)`;
   - `cache_root(self) -> Path`: `cache_base("sovereignloop")`, except when that does not
     exist and `cache_base("qwenloop")` does, then the legacy one;
   - `runs_roots(self, cwd: Path) -> tuple[Path, Path]`: `(cwd/.sovereignloop/runs, cwd/.qwenloop/runs)`;
   - `run_dir(self, cwd: Path, run_id: str) -> Path`: `cwd/.sovereignloop/runs/<id>`, except
     when that does not exist and `cwd/.qwenloop/runs/<id>` does, then the legacy one.
   - It never creates, copies, moves or deletes anything.
2. **Cache.** `ModelCache()` and `OpenAIServer()` (so `LlamaCppServer`, `VllmServer`) default
   their root to `StatePaths().cache_root()`; `model remove` builds its target with
   `StatePaths(cache_base=user_cache_path).cache_root()` (passing the CLI module's own
   `user_cache_path` keeps that name used in `cli/app.py`).
3. **Runs.** `FileRunStore(cwd, *, paths: StatePathsInterface | None = None)` resolves every
   run through `paths.run_dir(cwd, run_id)`: a new run is written under `.sovereignloop/`; a run
   id that exists only under `.qwenloop/` keeps being read and appended there (resume, inbox,
   status). `stop`, `wind-down` and `prompt` write into `StatePaths().run_dir(cwd, run_id)`'s
   `control/inbox`; `usage` counts the entries of both runs roots that exist.
4. **Marker.** `domain/model.py`:
   ```python
   DONE_MARKER = "SOVEREIGNLOOP_TASK_FULLY_COMPLETE"
   #: The former qwenloop's marker. A model prompted before the rename, or a plan that names the
   #: old marker, still completes a run with it through 3.x (ADR-0046 Migration table).
   LEGACY_DONE_MARKER = "QWENLOOP_TASK_FULLY_COMPLETE"
   #: Every marker that completes a run; the prompts only ever ask for DONE_MARKER.
   DONE_MARKERS = (DONE_MARKER, LEGACY_DONE_MARKER)
   ```
   The runner computes `claimed = any(marker in answer for marker in DONE_MARKERS)` once per
   turn and uses it at both checks; the system prompt (already `f"... {DONE_MARKER}."`) and
   `_INVALID_COMPLETION_PROMPT` name `SOVEREIGNLOOP_TASK_FULLY_COMPLETE`. Capacity handling and
   the completion conditions (verdict, tool use, storm evidence) are unchanged.
5. **vibey's descriptor** (`QWENLOOP` constant; lane L09 renames the constant):
   `binary="sovereignloop"`, `state_dir=".sovereignloop"`,
   `done_marker="SOVEREIGNLOOP_TASK_FULLY_COMPLETE"`. The five argv goldens start with
   `sovereignloop run` instead of `qwenloop run` (nothing else in them changes).
6. **Ignore files.** Root `.gitignore` and the tenant's `.gitignore` each gain
   `.sovereignloop/` on the line after `.qwenloop/` (both stay ignored).

## Where to change
Run everything from the repository root.
1. Write the two new tenant files with `write_file`, each exactly as given under *The new files*
   below, with line 1 the provenance line copied byte for byte from line 1 of
   `src/vibey_runners/sovereign/src/sovereignloop/infrastructure/run_store.py`. Then export the
   interface: in `.../infrastructure/interfaces/__init__.py` add
   `from sovereignloop.infrastructure.interfaces.state_paths_interface import StatePathsInterface`
   after the `settings_interface` import, and `"StatePathsInterface",` to `__all__` after
   `"SettingsLoaderInterface",`.
2. Save the script in *The edit script* below as `loops_legacy_paths.py` at the repository
   root, run `python3 loops_legacy_paths.py`, then `rm loops_legacy_paths.py` (never commit
   it). A failed assert means the tree differs from this spec: stop and report its message.
3. Write the new test file (below), then run the checks.

### The new files
`src/vibey_runners/sovereign/src/sovereignloop/infrastructure/state_paths.py` (after line 1):

```python
"""Where sovereignloop keeps its state, and where it still reads the former qwenloop's.

The rename never moves anything (ADR-0015 #5): a model cache is 13-16 GB and a run directory
is evidence. Each location has two spellings, and the current one wins whenever it exists
(ADR-0046 Migration table, through 3.x):

- the model cache, `<user cache dir>/sovereignloop`, else `<user cache dir>/qwenloop` while
  only that one exists;
- a run, `<cwd>/.sovereignloop/runs/<id>`, else `<cwd>/.qwenloop/runs/<id>` while only that
  one exists, so resume, inbox and status keep working on a run the old name started.
"""

from collections.abc import Callable
from pathlib import Path

from platformdirs import user_cache_path

NAME = "sovereignloop"
LEGACY_NAME = "qwenloop"
STATE_DIR = ".sovereignloop"
LEGACY_STATE_DIR = ".qwenloop"


class StatePaths:
    """Each state location: the current spelling, or the legacy one while only it exists."""

    def __init__(self, *, cache_base: Callable[[str], Path] = user_cache_path) -> None:
        self._cache_base = cache_base

    def cache_root(self) -> Path:
        current = self._cache_base(NAME)
        legacy = self._cache_base(LEGACY_NAME)
        return legacy if not current.exists() and legacy.exists() else current

    def runs_roots(self, cwd: Path) -> tuple[Path, Path]:
        return cwd / STATE_DIR / "runs", cwd / LEGACY_STATE_DIR / "runs"

    def run_dir(self, cwd: Path, run_id: str) -> Path:
        current_root, legacy_root = self.runs_roots(cwd)
        current, legacy = current_root / run_id, legacy_root / run_id
        return legacy if not current.exists() and legacy.exists() else current
```

`src/vibey_runners/sovereign/src/sovereignloop/infrastructure/interfaces/state_paths_interface.py` (after line 1):

```python
"""The contract for where sovereignloop's state lives, current spelling or legacy."""

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class StatePathsInterface(Protocol):
    """Resolves a state location; never creates, copies, moves or deletes anything."""

    def cache_root(self) -> Path:
        """The model cache root: the current one, or the legacy one while only it exists."""
        ...

    def runs_roots(self, cwd: Path) -> tuple[Path, Path]:
        """The current and the legacy runs roots under `cwd`, in that order."""
        ...

    def run_dir(self, cwd: Path, run_id: str) -> Path:
        """One run's directory: the current one, or the legacy one while only it exists."""
        ...
```

### The edit script
Copy it exactly as it stands (it starts at column 0).

```python
"""ADR-0046 lane L18d: the renamed on-disk names, every edit asserted (Arch Linux and macOS)."""

from pathlib import Path

ROOT = Path.cwd()
PKG = ROOT / "src/vibey_runners/sovereign/src/sovereignloop"
TESTS = ROOT / "src/vibey_runners/sovereign/tests"
assert (PKG / "infrastructure/state_paths.py").is_file(), "write state_paths.py first"


def edit(path: Path, old: str, new: str, count: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    found = text.count(old)
    assert found == count, f"{path}: expected {count} of {old!r}, found {found}"
    path.write_text(text.replace(old, new), encoding="utf-8")


IMPORT_STATE_PATHS = "from sovereignloop.infrastructure.state_paths import StatePaths\n"

# 1. The model cache root (ModelCache, the managed servers, `model remove`).
cache = PKG / "infrastructure/model_cache.py"
edit(
    cache,
    "from platformdirs import user_cache_path\n\nfrom sovereignloop.domain.model import ModelProfile\n",
    "from sovereignloop.domain.model import ModelProfile\n" + IMPORT_STATE_PATHS,
)
edit(
    cache,
    '        self.root = (root or user_cache_path("qwenloop")).resolve()\n',
    "        self.root = (root or StatePaths().cache_root()).resolve()\n",
)
inference = PKG / "infrastructure/inference.py"
edit(inference, "from platformdirs import user_cache_path\n\n", "")
edit(inference, "    ToolCallParseError,\n)\n", "    ToolCallParseError,\n)\n" + IMPORT_STATE_PATHS)
edit(
    inference,
    '        self.cache_dir = cache_dir or user_cache_path("qwenloop")\n',
    "        self.cache_dir = cache_dir or StatePaths().cache_root()\n",
)

# 2. Runs: the store, and the CLI's usage, stop, wind-down and prompt.
store = PKG / "infrastructure/run_store.py"
edit(
    store,
    "from typing import Any\n\n\nclass FileRunStore:\n"
    "    def __init__(self, cwd: Path) -> None:\n"
    '        self._root = cwd / ".qwenloop" / "runs"\n\n'
    "    def _run_dir(self, run_id: str) -> Path:\n"
    "        return self._root / run_id\n",
    "from typing import Any\n\n"
    "from sovereignloop.infrastructure.interfaces import StatePathsInterface\n"
    + IMPORT_STATE_PATHS
    + "\n\nclass FileRunStore:\n"
    "    def __init__(self, cwd: Path, *, paths: StatePathsInterface | None = None) -> None:\n"
    "        self._cwd = cwd\n"
    "        self._paths = paths or StatePaths()\n\n"
    "    def _run_dir(self, run_id: str) -> Path:\n"
    '        """`.sovereignloop/runs/<id>`, or the legacy `.qwenloop/runs/<id>` if only it exists."""\n'
    "        return self._paths.run_dir(self._cwd, run_id)\n",
)
app = PKG / "cli/app.py"
edit(
    app,
    "from sovereignloop.infrastructure.settings import SettingsLoader\n",
    "from sovereignloop.infrastructure.settings import SettingsLoader\n" + IMPORT_STATE_PATHS,
)
edit(
    app,
    '    target = user_cache_path("qwenloop") / "models" / profile\n',
    '    target = StatePaths(cache_base=user_cache_path).cache_root() / "models" / profile\n',
)
edit(
    app,
    '    runs = cwd / ".qwenloop" / "runs"\n'
    "    typer.echo(\n"
    "        json.dumps(\n"
    '            {"runs": len(list(runs.glob("*"))) if runs.exists() else 0, "provider_dollars": 0}\n'
    "        )\n"
    "    )\n",
    "    roots = StatePaths().runs_roots(cwd)\n"
    '    runs = sum(len(list(root.glob("*"))) for root in roots if root.exists())\n'
    '    typer.echo(json.dumps({"runs": runs, "provider_dollars": 0}))\n',
)
edit(
    app,
    '    inbox = cwd / ".qwenloop" / "runs" / run_id / "control" / "inbox"\n',
    '    inbox = StatePaths().run_dir(cwd, run_id) / "control" / "inbox"\n',
    count=2,
)

# 3. The done marker: write the new one, accept either.
model = PKG / "domain/model.py"
edit(
    model,
    'DONE_MARKER = "QWENLOOP_TASK_FULLY_COMPLETE"\n',
    'DONE_MARKER = "SOVEREIGNLOOP_TASK_FULLY_COMPLETE"\n'
    "#: The former qwenloop's marker. A model prompted before the rename, or a plan that names the\n"
    "#: old marker, still completes a run with it through 3.x (ADR-0046 Migration table).\n"
    'LEGACY_DONE_MARKER = "QWENLOOP_TASK_FULLY_COMPLETE"\n'
    "#: Every marker that completes a run; the prompts only ever ask for DONE_MARKER.\n"
    "DONE_MARKERS = (DONE_MARKER, LEGACY_DONE_MARKER)\n",
)
runner = PKG / "application/runner.py"
edit(
    runner,
    "from sovereignloop.domain.model import (\n    DONE_MARKER,\n",
    "from sovereignloop.domain.model import (\n    DONE_MARKER,\n    DONE_MARKERS,\n",
)
edit(
    runner,
    '    "QWENLOOP_TASK_FULLY_COMPLETE. For a storm run, read-only inspection is not progress: "\n',
    '    "SOVEREIGNLOOP_TASK_FULLY_COMPLETE. For a storm run, read-only inspection is not progress: "\n',
)
edit(
    runner,
    '            answer = "".join(text_parts)\n',
    '            answer = "".join(text_parts)\n'
    "            claimed = any(marker in answer for marker in DONE_MARKERS)\n",
)
edit(runner, "                DONE_MARKER in answer\n                and saw_verdict\n", "                claimed\n                and saw_verdict\n")
edit(
    runner,
    "            if DONE_MARKER in answer:\n                invalid_completion_claims += 1\n",
    "            if claimed:\n                invalid_completion_claims += 1\n",
)

# 4. The tenant tests that read a run directory the store now writes under .sovereignloop.
for name in ("test_cli.py", "test_runner.py"):
    path = TESTS / name
    text = path.read_text(encoding="utf-8")
    found = text.count('/ ".qwenloop" /')
    assert found >= 1, f"{path}: no .qwenloop run path found"
    path.write_text(text.replace('/ ".qwenloop" /', '/ ".sovereignloop" /'), encoding="utf-8")
    print(f"{name}: {found} run path(s) now under .sovereignloop")

# 5. vibey's descriptor and its argv goldens (named by lane L06).
descriptors = ROOT / "src/vibey/infrastructure/engines/descriptors.py"
edit(descriptors, '    binary="qwenloop",\n', '    binary="sovereignloop",\n')
edit(descriptors, '    state_dir=".qwenloop",\n', '    state_dir=".sovereignloop",\n')
edit(
    descriptors,
    '    done_marker="QWENLOOP_TASK_FULLY_COMPLETE",\n',
    '    done_marker="SOVEREIGNLOOP_TASK_FULLY_COMPLETE",\n',
)
golden = ROOT / "tests/infrastructure/engines/golden"
for effort in ("trivial", "low", "standard", "high", "max"):
    path = golden / f"sovereignloop_{effort}.txt"
    text = path.read_text(encoding="utf-8")
    assert text.startswith("qwenloop run ") and text.count("qwenloop") == 1, path
    path.write_text("sovereignloop" + text[len("qwenloop") :], encoding="utf-8")

# 6. Both ignore files keep the old directory ignored and add the new one.
for ignore in (ROOT / ".gitignore", ROOT / "src/vibey_runners/sovereign/.gitignore"):
    edit(ignore, ".qwenloop/\n", ".qwenloop/\n.sovereignloop/\n")
print("L18d edits applied")
```

If `ruff check` reports I001 on a file the script touched, run
`uv run ruff check --fix --select I <that file>`; if `ruff format --check` fails on one, run
`uv run ruff format <that file>`.

**Stop rule.** Any failing test, tenant or vibey, that is not fixed by this script: stop and
report it (for example a vibey test asserting `binary == "qwenloop"` or a `.qwenloop` path that
this spec did not find at `d3b4a388`).

## Acceptance criteria
- [ ] A new run writes `.sovereignloop/runs/<id>/{meta.json,events.jsonl,snapshots,control/inbox}` and no `.qwenloop/`.
- [ ] A run id present only under `.qwenloop/runs/` is appended to in place; `prompt`/`stop`/`wind-down` for it write into its legacy inbox.
- [ ] With only `<cache>/qwenloop` present, `StatePaths(cache_base=...).cache_root()` is it, and nothing is created, copied or moved.
- [ ] A model answer ending with either marker completes a run (when the other conditions hold); the prompts name only `SOVEREIGNLOOP_TASK_FULLY_COMPLETE`.
- [ ] vibey's `QWENLOOP` descriptor has `binary == "sovereignloop"`, `state_dir == ".sovereignloop"`, `done_marker == "SOVEREIGNLOOP_TASK_FULLY_COMPLETE"`; `tests/infrastructure/engines/test_argv.py` passes.
- [ ] `git grep -n '".qwenloop"\|QWENLOOP_TASK_FULLY_COMPLETE' -- src/vibey src/vibey_runners/sovereign/src` prints only `state_paths.py`'s `LEGACY_STATE_DIR` and `domain/model.py`'s `LEGACY_DONE_MARKER`.
- [ ] Tenant and vibey suites pass at their floors.

## Tests to write first (TDD)
`src/vibey_runners/sovereign/tests/test_legacy_paths.py` (line 1 from `tests/test_runner.py`;
every path under `tmp_path`, `cache_base` injected, no `monkeypatch.setattr`):
- `test_state_paths_satisfies_its_interface`.
- `test_the_cache_root_is_sovereignloop_when_neither_exists` (`cache_base=lambda name: tmp_path / name`).
- `test_the_legacy_cache_is_used_in_place_while_only_it_exists`: returns `tmp_path/"qwenloop"`; `tmp_path/"sovereignloop"` is still absent.
- `test_the_new_cache_wins_once_it_exists` (both exist).
- `test_a_new_run_is_written_under_sovereignloop`: `FileRunStore(tmp_path).create("r1", {})` returns `tmp_path/".sovereignloop"/"runs"/"r1"`; `.qwenloop` does not exist.
- `test_a_legacy_run_is_read_and_appended_in_place`: pre-create `tmp_path/".qwenloop"/"runs"/"old"/"control"/"inbox"/"1.json"` = `{"type": "stop"}`; `FileRunStore(tmp_path).read_control("old") == [{"type": "stop"}]`; `append_event("old", {...})` lands in the legacy `events.jsonl`.
- `test_the_store_takes_injected_paths` (a `StatePaths(cache_base=...)` instance passed as `paths=`).
- `test_cli_controls_reach_a_legacy_run` (`CliRunner`): with only the legacy run dir, `prompt old hi --cwd <tmp>` writes into its legacy inbox.
- `test_usage_counts_both_runs_roots`: one run under each root gives `"runs": 2`.
- `test_the_markers`: `DONE_MARKER == "SOVEREIGNLOOP_TASK_FULLY_COMPLETE"`, `DONE_MARKERS == (DONE_MARKER, "QWENLOOP_TASK_FULLY_COMPLETE")`.
- `test_the_new_marker_completes_a_run` (async): `from test_runner import FakeClock, FakeServer` (the tests directory is on `sys.path`, as `from fakes import ...` already relies on); `server = FakeServer()`; `server.chunks = [ChatChunk(tool_call={"name": "write_file", "arguments": {"path": "done.txt", "content": "ok"}}), ChatChunk(text="```qwenloop-verdict\npass\n```\nSOVEREIGNLOOP_TASK_FULLY_COMPLETE")]`; run `AutonomousRunner(server, FileRunStore(tmp_path), SandboxTools(tmp_path), clock=FakeClock()).run(run_id="new", plan="do it", cwd=tmp_path, profile=PORTABLE, server_info=ServerInfo(Backend.LLAMA_CPP, PORTABLE.name, "http://127.0.0.1", False, True), max_turns=2)`; `status is RunStatus.COMPLETED`.
- `test_the_prompts_name_only_the_new_marker`: `_system_prompt(tmp_path)` and `sovereignloop.application.runner._INVALID_COMPLETION_PROMPT` each contain `SOVEREIGNLOOP_TASK_FULLY_COMPLETE` and not `QWENLOOP_TASK_FULLY_COMPLETE`.

The existing runner tests whose model text ends with `QWENLOOP_TASK_FULLY_COMPLETE` stay
unedited: they are the legacy-marker proof.

## Checks the lane must run (all must pass)
    uv sync --extra dev
    (cd src/vibey_runners/sovereign && uv run --extra dev python -m pytest -q -p no:cacheprovider)
    (cd src/vibey_runners/sovereign && uv run --extra dev python -m mypy --strict src/sovereignloop && uv run --extra dev lint-imports && uv run --extra dev bandit -q -r src/sovereignloop)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/engines tests/application/test_conformance.py tests/live
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    git status --short

`git status --short` must not list `loops_legacy_paths.py`. The full `--cov` run needs
PostgreSQL until lane `fakes-harness-decouple` lands.

## Out of scope
- Environment names and the config file (lane L18c, done); vibey's endpoint overlay and feature
  switch names (lane `loops-vibey-local-engine-names`, L18e); `agent_surface.py` (L18e).
- Renaming the descriptor constant `QWENLOOP` (lane `loops-drop-qwenloop-alias`, L09).
- The `qwenloop-verdict` fence name the model is told to write (unchanged; not in the
  Migration table).
- Moving, copying or deleting any cache or run directory, ever.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees (the docs wave).
- Do not push or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-tenant-legacy-env`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
