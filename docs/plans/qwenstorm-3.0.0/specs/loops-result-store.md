## Title
feat(loop-service): a run's result is persisted atomically, and a loop records its measurements
ADR-0046 lane L22 (slug `loops-result-store`).

## Why
Draft ADR-0046 (`STORM/specs/ADR-two-loops.md`) runs each run request in a loop's **seat host**, and its idempotency table (§3, "a run") says a redelivered request whose result was already persisted is answered from that result, never run again. The superseded R21 (`specs/rmq-r21-local-run-executor.md`, behaviour 1; its closing note `issue-audit/updates/368.md`) specified that store: `<cwd>/.vibey/diagnostics/<run_id>.result.json`, written atomically before the request is acknowledged, beside the diagnostics `LoopProcessAdapter` already writes (`src/vibey/infrastructure/engines/loop_process_adapter.py:365-368` at integration `d3b4a388`). This lane carries it into the new package `infrastructure/loop_service/` (ADR-0046 §10).

Sub-doctrine 8.g (`src/vibey_tools/gh/docs/doctrines.md:316-324`) says every loop and queue records latency, depth, waiting time and outcome. The design sheet's decision D9 gives everything the caller never sees (switches, probes, rejections, dead letters, forwards) one sink: the loop's own append-only `measurements.jsonl` in its state directory, plus a structlog event `loop_measured`. This lane builds that sink, `LoopMeasurementLog`, so every later loop-service lane records into it. The loop is database-free by design (ADR-0046 §2; `issue-audit/updates/374.md`), and this lane adds the test that keeps the whole package so.

This is the first loop-service lane: it creates the package, its `interfaces/` package, the `.importlinter` entry ADR-0046 §10 asks for ("Each new `interfaces/` package joins `.importlinter`'s `infrastructure-interfaces-declare-only` contract"), and the test package.

## Required behaviour
1. **`src/vibey/infrastructure/loop_service/__init__.py`** holds the provenance line and this module docstring, and nothing else (no imports, so later lanes never edit it):
   ```python
   """ADR-0046's loop service: a router per loop and a seat host per model.

   Database-free by design (ADR-0046 §2): a loop needs only the broker and the shared
   worktrees volume. test_result_store.py::test_the_loop_service_needs_no_database holds
   every module in this package to that.
   """
   ```
2. **`src/vibey/infrastructure/loop_service/interfaces/__init__.py`** holds the provenance line and the docstring `"""Seams the loop service declares (ADR-0016). Interfaces declare; they never consume. Import each Protocol from its own module."""`, and nothing else.
3. **`class RunResultStore`** in `src/vibey/infrastructure/loop_service/result_store.py`, built as `RunResultStore(codec: RunProtocolCodec | None = None, *, logger: Logger | None = None)`. `codec` defaults to `RunProtocolCodec()`; `logger` defaults to `structlog.get_logger(__name__)`.
   - `path(self, cwd: str, run_id: UUID) -> Path` returns `Path(cwd) / ".vibey" / "diagnostics" / f"{run_id}.result.json"`.
   - `write(self, cwd: str, result: RunResult) -> None` writes `codec.to_bytes(result)` atomically:
     ```python
     target = self.path(cwd, result.run_id)
     body = self._codec.to_bytes(result)
     target.parent.mkdir(parents=True, exist_ok=True)
     descriptor, temp = tempfile.mkstemp(prefix=f".{result.run_id}.", suffix=".tmp", dir=target.parent)
     try:
         with os.fdopen(descriptor, "wb") as handle:
             handle.write(body)
             handle.flush()
             os.fsync(handle.fileno())
         os.replace(temp, target)
     except BaseException:
         # The temp file never outlives a failed write, even a cancelled one.
         Path(temp).unlink(missing_ok=True)
         raise
     ```
   - `read(self, cwd: str, run_id: UUID) -> RunResult | None`:
     - the file is missing (`FileNotFoundError`) → `None`, with no log;
     - `codec.from_bytes` raises `MalformedRunMessage` → log `warning("run_result_unreadable", path=str(target), error=str(exc))` and return `None`;
     - the decoded message is not a `RunResult`, or its `run_id != run_id` → log `warning("run_result_unreadable", path=str(target), error=f"not the result of run {run_id}")` and return `None`;
     - otherwise return the decoded `RunResult`.
4. **`class LoopMeasurementLog`** in `src/vibey/infrastructure/loop_service/measurement_log.py`, built as `LoopMeasurementLog(path: Path, *, logger: Logger | None = None)`:
   - `path` is a read-only property returning the path it was built with.
   - `record(self, measurement: LoopMeasurement) -> None`:
     ```python
     record = measurement.to_record()
     self._path.parent.mkdir(parents=True, exist_ok=True)
     with self._path.open("a", encoding="utf-8") as handle:
         handle.write(json.dumps(record, sort_keys=True) + "\n")
     self._log.info("loop_measured", **record)
     ```
     It appends only (mode `"a"`): it never truncates or rewrites a line already there.
5. **Interfaces**, each `@runtime_checkable`, in the style of `src/vibey/infrastructure/process/interfaces/reaper_interface.py` (module docstring "Mirrors `vibey/infrastructure/loop_service/<module>.py` (ADR-0016). Interfaces declare; they never consume."):
   - `interfaces/result_store_interface.py`: `RunResultStoreInterface` with `path(self, cwd: str, run_id: UUID) -> Path`, `write(self, cwd: str, result: RunResult) -> None`, `read(self, cwd: str, run_id: UUID) -> RunResult | None`, each with a one-line docstring.
   - `interfaces/measurement_log_interface.py`: `LoopMeasurementLogInterface` with the property `path -> Path` and `record(self, measurement: LoopMeasurement) -> None`.
   Both import their domain types (`RunResult` from `vibey.domain.run_protocol`, `LoopMeasurement` from `vibey.domain.loop_events`) at runtime: the domain is pure.
6. **`.importlinter`**: `vibey.infrastructure.loop_service.interfaces` joins the `source_modules` of `[importlinter:contract:infrastructure-interfaces-declare-only]` (`.importlinter:108-133` at `d3b4a388`).
7. **In-memory fakes**, appended to `tests/fakes/loops.py` (created by lane `loops-routing-ports`), each with real behaviour for every method:
   ```python
   class InMemoryRunResultStore:
       """RunResultStoreInterface in memory, keyed by (cwd, run_id). `fail_with` makes every
       write raise it, to prove a result is persisted before it is published and acked."""

       def __init__(self, *, fail_with: Exception | None = None) -> None:
           self.results: dict[tuple[str, UUID], RunResult] = {}
           self.writes: list[tuple[str, RunResult]] = []
           self.fail_with = fail_with

       def path(self, cwd: str, run_id: UUID) -> Path:
           return Path(cwd) / ".vibey" / "diagnostics" / f"{run_id}.result.json"

       def write(self, cwd: str, result: RunResult) -> None:
           if self.fail_with is not None:
               raise self.fail_with
           self.writes.append((cwd, result))
           self.results[(cwd, result.run_id)] = result

       def read(self, cwd: str, run_id: UUID) -> RunResult | None:
           return self.results.get((cwd, run_id))


   class InMemoryLoopMeasurementLog:
       """LoopMeasurementLogInterface in memory: every measurement, in order."""

       def __init__(self, path: Path = Path("measurements.jsonl")) -> None:
           self._path = path
           self.records: list[LoopMeasurement] = []

       @property
       def path(self) -> Path:
           return self._path

       def record(self, measurement: LoopMeasurement) -> None:
           self.records.append(measurement)
   ```
8. **Registry** (`tests/fakes/registry.py`, lane `fakes-registry`): both interfaces are appended to `DRIVER_SEAMS`, and `REGISTRY` gains `FakeRegistration(port=RunResultStoreInterface, build=InMemoryRunResultStore)` and `FakeRegistration(port=LoopMeasurementLogInterface, build=InMemoryLoopMeasurementLog)`.

## Where to change
Line 1 of every new file is the provenance comment, copied byte for byte from line 1 of `src/vibey/infrastructure/process/reaper.py`:
`# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`

This lane creates the package, so it touches more than one source file (the sheet names them):
- **New** `src/vibey/infrastructure/loop_service/__init__.py`, `interfaces/__init__.py` (behaviours 1–2).
- **New** `src/vibey/infrastructure/loop_service/result_store.py`. Imports: `os`, `tempfile`, `from pathlib import Path`, `from uuid import UUID`, `structlog`, `from vibey.application.interfaces import Logger`, `from vibey.domain.errors import MalformedRunMessage`, `from vibey.domain.run_codec import RunProtocolCodec`, `from vibey.domain.run_protocol import RunResult`. Store the logger as `self._log: Logger = logger if logger is not None else structlog.get_logger(__name__)`. `__all__ = ["RunResultStore"]`.
- **New** `src/vibey/infrastructure/loop_service/measurement_log.py`. Imports: `json`, `from pathlib import Path`, `structlog`, `from vibey.application.interfaces import Logger`, `from vibey.domain.loop_events import LoopMeasurement`. `__all__ = ["LoopMeasurementLog"]`.
- **New** `src/vibey/infrastructure/loop_service/interfaces/result_store_interface.py` and `interfaces/measurement_log_interface.py` (behaviour 5). No Protocol is declared outside an `interfaces` package (`tests/application/test_interfaces_convention.py:130-146`).
- **`.importlinter`** (behaviour 6): use `edit_file` with this exact `old_string` (it is unique; it is the end of that contract):
  ```
  forbidden_modules =
      vibey.cli
      vibey.tui
      vibey.bootstrap

  # The same rule for the first `interfaces/` package in the absorbed vibey-gh (ADR-0016:
  ```
  and this `new_string` (one line added above `forbidden_modules =`):
  ```
      vibey.infrastructure.loop_service.interfaces
  forbidden_modules =
      vibey.cli
      vibey.tui
      vibey.bootstrap

  # The same rule for the first `interfaces/` package in the absorbed vibey-gh (ADR-0016:
  ```
  Other lanes may have added source modules above; do not remove any line.
- **`tests/fakes/loops.py`** (behaviour 7): `read_file` it; add to its import block (with `edit_file`, after its last import line) `from pathlib import Path`, `from uuid import UUID`, `from vibey.domain.loop_events import LoopMeasurement`, `from vibey.domain.run_protocol import RunResult`; append the two classes at the end of the file with `edit_file` (old_string = the file's last lines, copied exactly). Never rewrite the file.
- **`tests/fakes/registry.py`** (behaviour 8): its tuples change with every lane, so use this checked script. Save it with `write_file` as `register_fakes.py` in the repository root, run `["python3", "register_fakes.py"]`, then delete it with `["rm", "register_fakes.py"]` (it must not be committed):
  ```python
  import ast
  from pathlib import Path

  REGISTRY = Path("tests/fakes/registry.py")
  IMPORTS = [
      "from tests.fakes.loops import InMemoryLoopMeasurementLog, InMemoryRunResultStore",
      "from vibey.infrastructure.loop_service.interfaces.measurement_log_interface import LoopMeasurementLogInterface",
      "from vibey.infrastructure.loop_service.interfaces.result_store_interface import RunResultStoreInterface",
  ]
  SEAMS = ["RunResultStoreInterface", "LoopMeasurementLogInterface"]
  ENTRIES = [
      "FakeRegistration(port=RunResultStoreInterface, build=InMemoryRunResultStore)",
      "FakeRegistration(port=LoopMeasurementLogInterface, build=InMemoryLoopMeasurementLog)",
  ]


  def extend(source: str, name: str, items: list[str]) -> str:
      tree = ast.parse(source)
      node = next(
          n
          for n in tree.body
          if isinstance(n, ast.AnnAssign | ast.Assign)
          and getattr(n.target if isinstance(n, ast.AnnAssign) else n.targets[0], "id", None) == name
      )
      assert isinstance(node.value, ast.Tuple), f"{name} is not a tuple literal"
      lines = source.splitlines(keepends=True)
      close = sum(map(len, lines[: node.value.end_lineno - 1])) + node.value.end_col_offset - 1
      assert source[close] == ")", f"{name} does not end with ')'"
      head = source[:close].rstrip()
      comma = "" if head.endswith(("(", ",")) else ","
      return head + comma + "\n" + "".join(f"    {item},\n" for item in items) + source[close:]


  source = REGISTRY.read_text(encoding="utf-8")
  assert IMPORTS[0] not in source, "already registered"
  tree = ast.parse(source)
  last = max(n.end_lineno for n in tree.body if isinstance(n, ast.Import | ast.ImportFrom))
  lines = source.splitlines(keepends=True)
  source = "".join(lines[:last]) + "".join(line + "\n" for line in IMPORTS) + "".join(lines[last:])
  source = extend(source, "DRIVER_SEAMS", SEAMS)
  source = extend(source, "REGISTRY", ENTRIES)
  REGISTRY.write_text(source, encoding="utf-8")
  print(f"registered {len(SEAMS)} seams and {len(ENTRIES)} fakes")
  ```
  If an `assert` fails, stop and report it; do not hand-edit around it.
- Then run `uv run ruff check --fix tests/fakes/loops.py tests/fakes/registry.py src/vibey/infrastructure/loop_service` and `uv run ruff format tests/fakes/loops.py tests/fakes/registry.py src/vibey/infrastructure/loop_service tests/infrastructure/loop_service` (it merges and sorts the imports).
- **New** `tests/infrastructure/loop_service/__init__.py` (the provenance line only) and `tests/infrastructure/loop_service/test_result_store.py`.

## Acceptance criteria
- [ ] `grep -n "vibey.infrastructure.loop_service.interfaces" .importlinter` prints exactly one line, and `uv run lint-imports` passes.
- [ ] Every test below passes; none uses `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`, and `tests/meta/patching_baseline.json` does not change.
- [ ] `tests/fakes/test_port_parity.py` passes with the two new registrations (parity, signatures, not-a-stub).
- [ ] `git status --short` lists no `register_fakes.py`.
- [ ] 100% branch coverage of `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
`tests/infrastructure/loop_service/test_result_store.py`. Use `NOW = datetime(2026, 9, 22, 12, 0, tzinfo=UTC)`, a helper `_result(run_id: UUID, detail: str = "") -> RunResult` returning `RunResult(run_id=run_id, status=RunStatus.EXITED, exit_code=0, meta_status="finished", started_at=NOW, finished_at=NOW + timedelta(seconds=5), detail=detail, stdout=None, stderr=None, cached_at=None)`, and a helper `_measurement(outcome: str = "exited:0") -> LoopMeasurement` returning `LoopMeasurement(loop_id=LoopId.SOVEREIGNLOOP, subject=MeasurementSubject.RUN, at=NOW, seat="gpt-oss-20b", engine_id="sovereignloop", model="gpt-oss:20b", latency_ms=1200.5, waited_seconds=3.0, outcome=outcome)`. Logs are read with `structlog.testing.capture_logs()`.
- `test_round_trip`: `RunResultStore().write(str(tmp_path), result)` then `read(str(tmp_path), result.run_id) == result`, and `path(str(tmp_path), run_id) == tmp_path / ".vibey" / "diagnostics" / f"{run_id}.result.json"` exists.
- `test_write_replaces_atomically_and_leaves_no_temp_file`: write `_result(run_id, "first")`, then `_result(run_id, "second")`; `read` returns the second, and `sorted(p.name for p in (tmp_path / ".vibey" / "diagnostics").iterdir()) == [f"{run_id}.result.json"]`.
- `test_a_failed_write_leaves_no_temp_file`: make the target path a directory (`store.path(...).mkdir(parents=True)`); `write` raises `OSError`; the diagnostics directory holds only that one entry.
- `test_missing_and_malformed_read_none`: a missing file reads `None` with no log line; a file holding `b"not json"` reads `None` and logs one `run_result_unreadable` warning; a file holding `RunProtocolCodec().to_bytes(<a valid RunProgress>)` reads `None`; a file holding the result of another run id reads `None`.
- `test_measurements_append_one_sorted_json_line_each`: `LoopMeasurementLog(tmp_path / "state" / "loops" / "sovereignloop" / "measurements.jsonl")` (parents do not exist yet) records two measurements; the file has two lines; `json.loads(line) == m.to_record()` for each, and each raw line equals `json.dumps(json.loads(line), sort_keys=True)`.
- `test_measurements_never_truncate_an_existing_log`: the file already holds `"previous\n"`; after one `record`, its first line is still `previous` and it has two lines.
- `test_each_measurement_is_logged_as_loop_measured`: one `record` gives one captured entry with `event == "loop_measured"`, `log_level == "info"` and every key of `to_record()` with its value.
- `test_the_loop_service_needs_no_database`: walk every `*.py` under `Path(vibey.infrastructure.loop_service.__file__).parent` with `ast`; no `Import`/`ImportFrom` names a module starting with `asyncpg`, `sqlalchemy`, `psycopg` or `vibey.infrastructure.db`. The failure message names the file and says "the loop needs only the broker and the shared volume (ADR-0046 §2)".
- `test_classes_and_fakes_satisfy_their_interfaces`: `isinstance` of `RunResultStore()` and `InMemoryRunResultStore()` against `RunResultStoreInterface`, of `LoopMeasurementLog(tmp_path / "m.jsonl")` and `InMemoryLoopMeasurementLog()` against `LoopMeasurementLogInterface`; the in-memory store round-trips one result, and `InMemoryRunResultStore(fail_with=OSError("disk full")).write(...)` raises `OSError`.

## Checks the lane must run (all must pass)
```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src/vibey
uv run lint-imports
uv run bandit -q -r src/vibey
uv run pytest -q -p no:cacheprovider tests/infrastructure/loop_service tests/fakes tests/meta/test_import_contracts_bind.py tests/meta/test_patching_ratchet.py tests/application/test_interfaces_convention.py
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
grep -n "vibey.infrastructure.loop_service.interfaces" .importlinter
git status --short
```
Tests that need PostgreSQL are marked `integration` (lane `fakes-harness-decouple`) and skip without `VIBEY_TEST_DATABASE_URL`; nothing in this lane needs a service.

## Out of scope
- The executor, the fence, the stores, the seat host and the router (lanes `loops-local-run-executor` through `loops-router-forwarding`).
- Writing measurements into the PostgreSQL ledger (D9: the caller writes `LoopRouted`/`LoopRunMeasured`; the loop is database-free).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees (the docs wave). Protected tests (`tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`) are never edited.
- Do not push, open a PR or change remotes. Commit locally with the Title as the subject.
- Editing: follow `STORM/EDITING-RULES.md` (`edit_file` for existing files; never rewrite an existing test file). Nothing here is OS-specific (8.h: Arch Linux and macOS alike).

**Depends on:** `loops-run-codec`, `loops-ledger-kinds`, `loops-routing-ports`
- `loops-run-codec`: `RunProtocolCodec`, `MalformedRunMessage` and the `RunResult` message (via `loops-run-protocol-messages`).
- `loops-ledger-kinds`: `LoopMeasurement`, `MeasurementSubject` (`domain/loop_events.py`).
- `loops-routing-ports`: creates `tests/fakes/loops.py`; with it, `fakes-registry` (`tests/fakes/registry.py`, the patching ratchet).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
