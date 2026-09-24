## Title
feat(loop-service): a loop stores each route once, and its round-robin cursors, in its state directory
ADR-0046 lane L27 (slug `loops-state-stores`).

## Why
Draft ADR-0046 §3's idempotency table (`STORM/specs/ADR-two-loops.md:183-191`) keys the outer layer by `route_id`: "`RouteStore` creates the record once. A redelivered route re-sends the stored `RunRouted` and never advances SWRR twice", and "the router forwards a run only to the seat of its stored route, so a redelivered intake message lands in the same seat queue". §2 (lines 129–136) moves the inner round robin's cursors out of PostgreSQL in service mode: "The loop's cursors persist, per project, in its own state directory (§10). In service mode, `rotation_cursor` no longer holds the inner state", which keeps the loop database-free ("The loop needs only the broker and the shared volume"). Decision D14 of the design sheet puts `LoopCursorStore` inside `route_store.py`.

Both stores live on the loop's state directory and must survive a crash at any instant: a route is created with its content already in it (a temporary file linked into place, as the worktree fence does), and the cursor file is replaced atomically (temporary file plus `os.replace`, as `RunResultStore` does).

## Required behaviour
All in `src/vibey/infrastructure/loop_service/route_store.py`.
1. **`class RouteStore`**, built as `RouteStore(root: Path, codec: RunProtocolCodec | None = None, *, logger: Logger | None = None)`. `root` is the loop's state directory; `codec` defaults to `RunProtocolCodec()`, `logger` to `structlog.get_logger(__name__)`. A route lives at `root / "routes" / f"{route_id}.json"`.
   - `create_once(self, routed: RunRouted) -> RunRouted`:
     ```python
     path = self._route_path(routed.route_id)
     path.parent.mkdir(parents=True, exist_ok=True)
     temp = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
     temp.write_bytes(self._codec.to_bytes(routed))
     try:
         os.link(temp, path)
         return routed
     except FileExistsError:
         stored = self.get(routed.route_id)
         if stored is not None:
             return stored
         # An unreadable record is replaced, never trusted.
         os.replace(temp, path)
         self._log.warning("route_record_replaced", route_id=str(routed.route_id))
         return routed
     finally:
         temp.unlink(missing_ok=True)
     ```
     The first route stored for an id always wins: a second `create_once` with the same `route_id` returns the stored route unchanged.
   - `get(self, route_id: UUID) -> RunRouted | None`: missing → `None` (no log); `MalformedRunMessage`, or a decoded message that is not a `RunRouted` or has another `route_id` → log `warning("route_record_unreadable", route_id=str(route_id))` and return `None`.
   - `prune(self, older_than: datetime) -> int`: for every `root / "routes" / "*.json"`, read it with `get` (by the file's stem as a UUID; skip a stem that is not a UUID); delete the files whose `routed_at < older_than`; skip unreadable ones; return how many were deleted.
   - A private `_route_path(self, route_id: UUID) -> Path`.
2. **`class LoopCursorStore`**, built as `LoopCursorStore(root: Path, *, logger: Logger | None = None)`. A project's cursors live at `root / "cursors" / f"{project_id}.json"`, and a pinned or project-less route's at `root / "cursors" / "_.json"`.
   - `load(self, project_id: UUID | None) -> tuple[SeatCursor, ...]`: missing → `()`; otherwise `json.loads` the file, which must be a list of objects with `engine_id` (str), `current` (int) and `order` (int), returned in the stored order as `SeatCursor(engine_id=..., current=..., order=...)`. Any `OSError`, `ValueError`, `KeyError` or `TypeError` while reading or building, or a top-level value that is not a list → log `warning("loop_cursors_unreadable", path=str(path))` and return `()` (the round robin restarts; it never crashes the router).
   - `save(self, project_id: UUID | None, cursors: Sequence[SeatCursor]) -> None`: write `json.dumps([{"engine_id": c.engine_id, "current": c.current, "order": c.order} for c in cursors], sort_keys=True)` to a temporary file in the same directory (`path.with_name(f"{path.name}.{uuid4().hex}.tmp")`), then `os.replace` it onto the path. Parents are created.
3. **Interfaces** in `src/vibey/infrastructure/loop_service/interfaces/route_store_interface.py`, both `@runtime_checkable`, one-line docstring per member:
   - `RouteStoreInterface`: `create_once(self, routed: RunRouted) -> RunRouted`, `get(self, route_id: UUID) -> RunRouted | None`, `prune(self, older_than: datetime) -> int`.
   - `LoopCursorStoreInterface`: `load(self, project_id: UUID | None) -> tuple[SeatCursor, ...]`, `save(self, project_id: UUID | None, cursors: Sequence[SeatCursor]) -> None`.
   They import `RunRouted` (`vibey.domain.run_protocol`) and `SeatCursor` (`vibey.domain.seat_choice`) at runtime; the domain is pure.
4. **In-memory fakes**, appended to `tests/fakes/loops.py`:
   ```python
   class InMemoryRouteStore:
       """RouteStoreInterface in memory: the first route stored for an id wins."""

       def __init__(self) -> None:
           self.routes: dict[UUID, RunRouted] = {}
           self.created: list[UUID] = []

       def create_once(self, routed: RunRouted) -> RunRouted:
           if routed.route_id in self.routes:
               return self.routes[routed.route_id]
           self.routes[routed.route_id] = routed
           self.created.append(routed.route_id)
           return routed

       def get(self, route_id: UUID) -> RunRouted | None:
           return self.routes.get(route_id)

       def prune(self, older_than: datetime) -> int:
           old = [key for key, routed in self.routes.items() if routed.routed_at < older_than]
           for key in old:
               del self.routes[key]
           return len(old)


   class InMemoryLoopCursorStore:
       """LoopCursorStoreInterface in memory; `saves` records every save, in order."""

       def __init__(self) -> None:
           self.cursors: dict[UUID | None, tuple[SeatCursor, ...]] = {}
           self.saves: list[tuple[UUID | None, tuple[SeatCursor, ...]]] = []

       def load(self, project_id: UUID | None) -> tuple[SeatCursor, ...]:
           return self.cursors.get(project_id, ())

       def save(self, project_id: UUID | None, cursors: Sequence[SeatCursor]) -> None:
           self.cursors[project_id] = tuple(cursors)
           self.saves.append((project_id, tuple(cursors)))
   ```
5. **Registry**: `RouteStoreInterface` and `LoopCursorStoreInterface` are appended to `DRIVER_SEAMS`; `REGISTRY` gains `FakeRegistration(port=RouteStoreInterface, build=InMemoryRouteStore)` and `FakeRegistration(port=LoopCursorStoreInterface, build=InMemoryLoopCursorStore)`.

## Where to change
Line 1 of every new file is the provenance comment, copied byte for byte from line 1 of `src/vibey/infrastructure/process/reaper.py`.
- **New** `src/vibey/infrastructure/loop_service/route_store.py` (D14: one module, two classes). Imports: `json`, `os`, `from collections.abc import Sequence`, `from datetime import datetime`, `from pathlib import Path`, `from uuid import UUID, uuid4`, `structlog`, `from vibey.application.interfaces import Logger`, `from vibey.domain.errors import MalformedRunMessage`, `from vibey.domain.run_codec import RunProtocolCodec`, `from vibey.domain.run_protocol import RunRouted`, `from vibey.domain.seat_choice import SeatCursor`. `__all__ = ["LoopCursorStore", "RouteStore"]`. Module docstring: ADR-0046 §3's route idempotency and §2's cursor file; database-free.
- **New** `src/vibey/infrastructure/loop_service/interfaces/route_store_interface.py` (behaviour 3), in the style of `src/vibey/infrastructure/process/interfaces/reaper_interface.py`.
- **`tests/fakes/loops.py`**: add `from collections.abc import Sequence`, `from datetime import datetime`, `from vibey.domain.run_protocol import RunRouted` and `from vibey.domain.seat_choice import SeatCursor` to its import block with `edit_file` (skip any already there); append the classes of behaviour 4 at the end with `edit_file`.
- **`tests/fakes/registry.py`**: run the registration script of lane `loops-result-store` (the `register_fakes.py` block) with only these lists, then delete the script:
  ```python
  IMPORTS = [
      "from tests.fakes.loops import InMemoryLoopCursorStore, InMemoryRouteStore",
      "from vibey.infrastructure.loop_service.interfaces.route_store_interface import LoopCursorStoreInterface, RouteStoreInterface",
  ]
  SEAMS = ["RouteStoreInterface", "LoopCursorStoreInterface"]
  ENTRIES = [
      "FakeRegistration(port=RouteStoreInterface, build=InMemoryRouteStore)",
      "FakeRegistration(port=LoopCursorStoreInterface, build=InMemoryLoopCursorStore)",
  ]
  ```
- Then `uv run ruff check --fix` and `uv run ruff format` on `tests/fakes/loops.py tests/fakes/registry.py src/vibey/infrastructure/loop_service tests/infrastructure/loop_service`.
- **New** `tests/infrastructure/loop_service/test_route_store.py`.

## Acceptance criteria
- [ ] A route id is stored once; a repeated `create_once` returns the first route, byte for byte.
- [ ] No `*.tmp` file is left in `routes/` or `cursors/` after any test.
- [ ] Unreadable records are logged and never crash a caller.
- [ ] No `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`; `tests/meta/patching_baseline.json` does not change; `tests/fakes/test_port_parity.py` passes.
- [ ] 100% branch coverage of `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
`tests/infrastructure/loop_service/test_route_store.py`. Use `NOW = datetime(2026, 9, 22, 12, 0, tzinfo=UTC)` and a helper
```python
def _routed(route_id: UUID | None = None, *, seat: str = "gpt-oss-20b", at: datetime = NOW) -> RunRouted:
    return RunRouted(route_id=route_id or uuid4(), loop_id=LoopId.SOVEREIGNLOOP, status=RouteStatus.ROUTED,
                     engine_id="sovereignloop", seat=seat, model="gpt-oss:20b", switched=False,
                     reason="resident", routed_at=at, route_ms=1.5, seat_depth=0,
                     seat_oldest_wait_seconds=None)
```
Logs are read with `structlog.testing.capture_logs()`.
- `test_create_once_stores_and_returns_the_route`: `RouteStore(tmp_path).create_once(r) == r`; `get(r.route_id) == r`; the file is `tmp_path / "routes" / f"{r.route_id}.json"`.
- `test_a_second_create_returns_the_stored_route_unchanged`: `create_once(_routed(rid, seat="gpt-oss-20b"))`, then `create_once(_routed(rid, seat="qwen3-coder-30b"))` returns the first (seat `gpt-oss-20b`), and the file still decodes to the first.
- `test_get_is_none_for_a_missing_or_unreadable_record`: a missing id → `None`, no log; a file holding `b"not json"` → `None` and one `route_record_unreadable`; a file holding a route with another id → `None`.
- `test_create_once_replaces_an_unreadable_record`: the path already holds `b"garbage"`; `create_once(r) == r`, `get(r.route_id) == r`, and one `route_record_replaced` warning.
- `test_prune_removes_only_older_routes`: routes at `NOW - timedelta(hours=2)`, `NOW - timedelta(minutes=5)`, plus a `garbage.json` file and a `<uuid>.json` holding garbage; `prune(NOW - timedelta(hours=1)) == 1`; the recent route and both unreadable files remain.
- `test_cursors_round_trip_per_project_and_for_none`: `save(pid, (SeatCursor("claudeloop", -1, 0), SeatCursor("codexloop", 1, 1)))` then `load(pid)` returns them in order; `save(None, ...)` writes `cursors/_.json` and `load(None)` returns it; `load(uuid4())` is `()`.
- `test_saving_cursors_replaces_the_file_whole`: two saves, `load` returns the second; `cursors/` holds exactly one file.
- `test_unreadable_cursors_load_empty`: files holding `not json`, `{"a": 1}`, `[{"engine_id": "x"}]` and `[{"engine_id": "x", "current": "no", "order": 0}]` each load `()` with one `loop_cursors_unreadable` warning.
- `test_no_temp_file_is_left_behind`: after the scenarios above on one root, `list(tmp_path.rglob("*.tmp")) == []`.
- `test_the_stores_and_their_fakes_satisfy_their_interfaces`: `isinstance` of `RouteStore(tmp_path)` and `InMemoryRouteStore()` against `RouteStoreInterface`, of `LoopCursorStore(tmp_path)` and `InMemoryLoopCursorStore()` against `LoopCursorStoreInterface`; the in-memory route store keeps the first route, `prune` removes the old one; the in-memory cursor store round-trips and records `saves`.

## Checks the lane must run (all must pass)
```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src/vibey
uv run lint-imports
uv run bandit -q -r src/vibey
uv run pytest -q -p no:cacheprovider tests/infrastructure/loop_service tests/fakes tests/meta/test_patching_ratchet.py tests/application/test_interfaces_convention.py
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
git status --short
```
`os.link` and `os.replace` are POSIX and behave the same on Arch Linux and macOS (8.h).

## Out of scope
- Routing, forwarding and when to prune (lanes `loops-router-routing`, `loops-router-forwarding`, and the process lane).
- `rotation_cursor` in PostgreSQL (subprocess mode keeps it, ADR-0046 §2; lane `orm-rotation-cursor`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees. Protected tests are never edited.
- Do not push, open a PR or change remotes. Commit locally with the Title as the subject. Follow `STORM/EDITING-RULES.md`.

**Depends on:** `loops-result-store`, `loops-seat-chooser`
- `loops-result-store`: the `loop_service` package, the loop fakes module and the registration script; with it, `RunProtocolCodec` and `RunRouted`.
- `loops-seat-chooser`: `SeatCursor` (`domain/seat_choice.py`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
