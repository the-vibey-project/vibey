## Title
feat(rotation): the LoopRoutingPort and RoutedAdapterBinderInterface seams, with registered in-memory fakes

ADR-0046 lane L14 (slug `loops-routing-ports`).

## Why
Draft ADR-0046 §3, "Flow for a BUILD job" (`specs/ADR-two-loops.md:169-179`): `select_for`
makes the outer decision, "publishes a route request to `<loop>` and awaits `RunRouted`,
bounded by `route_wait_seconds`", then "returns an adapter bound to that engine", so that
"`EngineAdapter.descriptor` is known before `start`, exactly as `build_implement_handler.py:185`
needs today". §10 (`:303`) places `LoopRoutingPort` and `RoutedAdapterBinderInterface` in
`application/interfaces/loop_routing.py`. Sub-doctrine 9.b
(`src/vibey_tools/gh/docs/doctrines.md:349`) wants the seam declared and its test double from the
first day; the operator's standard (`STORM-CONTEXT.md`, "Comprehensive in-memory fakes for every
interface") wants every new port's fake registered.

At integration `d3b4a388` neither seam exists; `application/interfaces/loop_routing.py` is
created by lane `loops-loop-selector` with `LoopSelectorInterface` only. This lane appends the
two ports, exports them, creates `tests/fakes/loops.py` with their fakes (later loop lanes
append their fakes to the same file, design sheet "Standing rules"), and registers them. The
application code that uses them is lane `loops-selecting-loop-provider`; the infrastructure
implementations are lanes `loops-client` (`LoopClient` satisfies `LoopRoutingPort`) and
`loops-service-adapter-run` (`RoutedAdapterBinder`).

## Required behaviour
1. `src/vibey/application/interfaces/loop_routing.py` gains, after `LoopSelectorInterface`:
   ```python
   @runtime_checkable
   class LoopRoutingPort(Protocol):
       """The outer layer's route call over the bus (ADR-0046 §3): publish one `RouteRequest`
       to its loop's intake queue and await that loop's `RunRouted`, for at most `wait`.
       `None` means no router answered in time -- the caller defers (busy, never a paid
       fallback, ADR-0046 §5)."""

       async def route(self, request: RouteRequest, *, wait: timedelta) -> RunRouted | None: ...


   @runtime_checkable
   class RoutedAdapterBinderInterface(Protocol):
       """Builds the `EngineAdapter` bound to the engine, seat and model a loop routed a job
       to, before the handler calls `start` (ADR-0046 §3, step 4)."""

       def bind(self, routed: RunRouted, *, job: JobRecord) -> EngineAdapter: ...
   ```
   with the imports `from datetime import timedelta`, `JobRecord` added to the existing
   `from vibey.application.dto import ...`, `from vibey.application.interfaces.engines import EngineAdapter`,
   and `from vibey.domain.run_protocol import RouteRequest, RunRouted` (lane
   `loops-run-protocol-messages`). Keep `from __future__ import annotations` and import every
   annotated name at runtime (not under `TYPE_CHECKING`):
   `tests/application/test_interfaces_convention.py:112-122` resolves every annotation.
2. Both are exported from `vibey.application.interfaces` (`__init__.py` import and `__all__`).
3. New `tests/fakes/loops.py` holds two fakes with real in-memory behaviour:
   ```python
   class FakeLoopRouting:
       """An in-memory `LoopRoutingPort`: each loop answers the reply it was scripted, rebound
       to the request's `route_id` (as a router's reply correlates to its request); a loop
       with no scripted reply, or scripted `None`, answers `None` -- no router answered."""

       def __init__(self, replies: Mapping[LoopId, RunRouted | None]) -> None:
           self._replies = dict(replies)
           self.requests: list[RouteRequest] = []
           self.waits: list[timedelta] = []

       async def route(self, request: RouteRequest, *, wait: timedelta) -> RunRouted | None:
           self.requests.append(request)
           self.waits.append(wait)
           reply = self._replies.get(request.loop_id)
           if reply is None:
               return None
           return replace(reply, route_id=request.route_id)


   class FakeRoutedAdapterBinder:
       """An in-memory `RoutedAdapterBinderInterface`: the adapter scripted for the routed
       engine id, recording every bind. An engine with no scripted adapter raises `KeyError`,
       as a binder without that engine's descriptor would fail."""

       def __init__(self, adapters: Mapping[str, EngineAdapter]) -> None:
           self._adapters = dict(adapters)
           self.binds: list[tuple[RunRouted, JobRecord]] = []

       def bind(self, routed: RunRouted, *, job: JobRecord) -> EngineAdapter:
           self.binds.append((routed, job))
           return self._adapters[routed.engine_id or ""]
   ```
   (imports: `dataclasses.replace`, `datetime.timedelta`, `collections.abc.Mapping`,
   `JobRecord`, `EngineAdapter`, `LoopId`, `RouteRequest`, `RunRouted`).
4. **Registry.** `tests/fakes/registry.py` (lane `fakes-registry`) gains in `REGISTRY`:
   `FakeRegistration(port=LoopRoutingPort, build=lambda: FakeLoopRouting({}), note="scripted RunRouted per loop")`
   and
   `FakeRegistration(port=RoutedAdapterBinderInterface, build=lambda: FakeRoutedAdapterBinder({}), note="scripted adapter per routed engine")`.
   Its parity tests (`test_fake_satisfies_its_port`, `test_fake_signatures_match_the_port`,
   `test_fakes_are_not_stubs`, `test_every_application_port_is_accounted_for`) pass.

## Where to change
Read `STORM/EDITING-RULES.md` first.
- `src/vibey/application/interfaces/loop_routing.py` (from lane `loops-loop-selector`): append the
  two Protocols (behaviour 1) and extend its imports. It is under 100 lines, but still use
  `edit_file` (append after the last line of `LoopSelectorInterface`).
- `src/vibey/application/interfaces/__init__.py` (over 100 lines: `edit_file`): change
  `from vibey.application.interfaces.loop_routing import LoopSelectorInterface` into
  ```python
  from vibey.application.interfaces.loop_routing import (
      LoopRoutingPort,
      LoopSelectorInterface,
      RoutedAdapterBinderInterface,
  )
  ```
  and add `"LoopRoutingPort",` and `"RoutedAdapterBinderInterface",` to `__all__` directly after
  `"LoopSelectorInterface",`.
- New `tests/fakes/loops.py`; line 1 is the provenance comment copied byte for byte from
  `tests/fakes/engines.py`. No `unittest.mock`; no method body that is only `...`, `pass`,
  `return None` or `raise NotImplementedError`.
- `tests/fakes/registry.py`: the two `FakeRegistration` entries inside the `REGISTRY` tuple
  literal (before its closing parenthesis) and their imports
  (`from tests.fakes.loops import FakeLoopRouting, FakeRoutedAdapterBinder`; the two ports from
  `vibey.application.interfaces`).
- New test file `tests/fakes/test_fake_loops.py`.

## Acceptance criteria
- [ ] Every test below passes, and so do `tests/fakes/test_port_parity.py` and
      `tests/application/test_interfaces_convention.py`.
- [ ] `from vibey.application.interfaces import LoopRoutingPort, LoopSelectorInterface, RoutedAdapterBinderInterface` works.
- [ ] `grep -n "unittest.mock\|MagicMock\|AsyncMock" tests/fakes/loops.py tests/fakes/test_fake_loops.py` prints nothing.
- [ ] `uv run mypy --strict src/vibey` and `uv run lint-imports` pass (the interfaces package
      imports only `vibey.application.dto`, its own modules and `vibey.domain`).

## Tests to write first (TDD)
`tests/fakes/test_fake_loops.py` (line 1: the provenance comment). Build a reply with
`RunRouted(route_id=uuid4(), loop_id=LoopId.SOVEREIGNLOOP, status=RouteStatus.ROUTED, engine_id="sovereignloop", seat="gpt-oss-20b", model="gpt-oss:20b", switched=False, reason="resident", routed_at=datetime(2026, 9, 22, tzinfo=UTC), route_ms=1.5, seat_depth=0, seat_oldest_wait_seconds=None)`
and a request with
`RouteRequest(route_id=uuid4(), loop_id=LoopId.SOVEREIGNLOOP, project_id=uuid4(), candidates=(RouteCandidate("sovereignloop", 1),), pin=None, model_pin=None, min_context=None, requested_at=datetime(2026, 9, 22, tzinfo=UTC), caller="w1")`.
- `test_fake_routing_answers_the_scripted_reply_rebound_to_the_request`: the answer equals the
  scripted reply except `route_id == request.route_id`.
- `test_fake_routing_answers_none_for_a_loop_it_was_not_scripted_for`: a `PAIDLOOP` request →
  `None`; a loop scripted `None` → `None`.
- `test_fake_routing_records_every_request_and_wait`: two calls → `requests` and `waits` hold
  both, in order.
- `test_fake_binder_returns_the_routed_engines_adapter_and_records_the_bind`: with
  `{"sovereignloop": ScriptedEngine(descriptor=BY_ENGINE_ID[EngineId.SOVEREIGNLOOP], base_dir=tmp_path)}`
  → that object, and `binds == [(routed, job)]` (`job = make_job(uuid4())` from `tests.fakes.queue`).
- `test_fake_binder_refuses_an_engine_it_has_no_adapter_for`: `pytest.raises(KeyError)`.
- `test_the_fakes_satisfy_their_ports`: `isinstance(FakeLoopRouting({}), LoopRoutingPort)` and
  `isinstance(FakeRoutedAdapterBinder({}), RoutedAdapterBinderInterface)`.
- `test_the_ports_are_exported`: the three names import from `vibey.application.interfaces`.

## Checks the lane must run (all must pass)
First run `uv run ruff format src/vibey/application/interfaces tests/fakes`.

    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/fakes tests/application/test_interfaces_convention.py tests/application/test_loop_selector.py tests/meta
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/application/*' --fail-under=100
    git diff --stat

## Out of scope
- `SelectingLoopProvider` (lane `loops-selecting-loop-provider`), `LoopClient` (lane
  `loops-client`), `RoutedAdapterBinder` (lane `loops-service-adapter-run`).
- Any fake beyond these two; `tests/fakes/loops.py` grows in later lanes.
- Protected tests: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

**Depends on:** `loops-loop-selector`, `loops-run-protocol-messages`, `fakes-registry`, `fakes-engines`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
