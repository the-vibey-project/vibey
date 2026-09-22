## Title
feat(config): [loop_services] declares the two loops, their seats and their capacity, and refuses replicas

ADR-0046 lane L10 (slug `loops-config-loop-services`).

## Why
Sub-doctrine 8.c (`src/vibey_tools/gh/docs/doctrines.md:196-234`) runs **exactly two loops**,
"a single instance per model", and "Throughput is raised by giving the one instance more
capacity, never by starting another". 12.c (`doctrines.md:455`) makes every tunable a key.
Draft ADR-0046 §3, §4, §6 and §11 (`specs/ADR-two-loops.md`) name those keys: capacity,
per-seat prefetch, the models, the default model, the residency bounds, unload-on-switch, the
route wait, the queue wait, the supersede grace, the stale-lock bound, and the
`[loop_services] root` a run's `cwd` must lie under (its *Security impact*). Its *Migration*
table maps R01's unreleased `[loop_services.<engine_id>]` to `[loop_services.<loop_id>]` with
`.seats.<name>`.

This is "ADR-0046's loop-configuration lane" that three filed issues defer to:
- #348 (R01, `issue-audit/updates/348.md` behaviour notes, "Do not add any `loop_services` key
  here");
- #377 (R30, `updates/377.md`: the chart sets `VIBEY_LOOP_SERVICES_ROOT=/work` on every loop
  pod and the worker, and its `loopServices.<loop>.models` / `capacity` values mirror these keys);
- #380 (R33, `updates/380.md`: the doctor's probe root is `[loop_services] root`, and it reads
  sovereignloop's declared models, defaulting to `gpt-oss:20b`).

At integration `d3b4a388`, `VibeyConfig` (`src/vibey/domain/config.py:318-342`) has no
`loop_services` field and `_SURFACE_ENV_VARS` (`src/vibey/infrastructure/config_loader.py:17-59`)
has no row for it. Every value is validated here, in the pure domain, so the loops, the chart
and the doctor never re-derive a default.

`ConfigError` is defined in `config.py` (`:38-44`). The new module must raise it, and
`config.py` must import the new module for its `VibeyConfig` field, which would be an import
cycle. So `ConfigError` moves to `src/vibey/domain/errors.py`, and `config.py` re-exports it
(`from vibey.domain.config import ConfigError` keeps working everywhere).

## Required behaviour
1. **Keys.** `[loop_services]` holds exactly `root`, `state_dir`, `sovereignloop` and
   `paidloop`.
   - `root: str = "/"`: must start with `/`, else `ConfigError("loop_services.root", "must be an absolute path")`.
   - `state_dir: str = ""`: `""` (resolved at composition by lane `loops-bootstrap-loop-service`)
     or starts with `/`, else `ConfigError("loop_services.state_dir", "must be empty or an absolute path")`.
   - A non-string `root` or `state_dir`: `ConfigError(<dotted key>, "must be a string")`.
   - A non-table `[loop_services]`: `ConfigError("loop_services", "must be a table")`.
   - Any other key (after the `replicas` check): `ConfigError("loop_services", "loop_services has exactly two loops (8.c): sovereignloop and paidloop")`.
2. **`replicas` is refused wherever it is written**: in `[loop_services]`, in either loop's
   table, and in any seat table, with
   `ConfigError(<dotted key>, "replicas is not a key: sub-doctrine 8.c runs a single instance per model; raise capacity instead")`,
   for example `loop_services.sovereignloop.replicas` or
   `loop_services.paidloop.seats.claudeloop.replicas`. It is checked before any other key of
   that table.
3. **Each loop's table** (`[loop_services.sovereignloop]`, `[loop_services.paidloop]`) becomes
   a `LoopConfig`. Defaults and constraints:

   | key | default | constraint (error path `loop_services.<loop>.<key>`) |
   |---|---|---|
   | `models` | `()` | list of non-empty strings, else "must be a list of non-empty strings"; slugs unique and not reserved (`SeatSlug().unique`, its `ValueError` text becomes the message); paidloop: each is a canonical engine id (`ENGINE_ID_PARSER.known(x)` is a member whose `.value == x`, else "`<x>` is not an engine id") and not `sovereignloop` ("sovereignloop is sovereignloop's adapter, not a paid one (sub-doctrine 8.b)") |
   | `default_model` | `"gpt-oss:20b"` (sovereignloop); `None` (paidloop) | sovereignloop only: a non-empty string ("must be a model name"), one of `models` when `models` is non-empty ("`<m>` is not one of models"), and a valid slug when `models` is empty; on paidloop → "paidloop's default adapter is claudeloop (sub-doctrine 8.b); name its seats with models" |
   | `model_context` | `{}` | sovereignloop only (on paidloop → "model_context is sovereignloop's: its seats are models"); a table ("must be a table of model = context window"); each key a declared model (path `...model_context.<m>`, "`<m>` is not a declared model"); each value an integer ≥ 1 |
   | `capacity` | `1` | integer 1–64 (a seat's prefetch; 8.c: throughput is capacity, never a copy) |
   | `router_prefetch` | `16` | integer 1–1000 |
   | `delivery_limit` | `3` | integer 1–1000 |
   | `consumer_timeout_seconds` | `21600` | integer ≥ 60 |
   | `residency_max_wait_seconds` | `900.0` | number ≥ 0 |
   | `residency_min_hold_runs` | `1` | integer ≥ 0 |
   | `unload_on_switch` | `true` | boolean |
   | `schedule_interval_seconds` | `5.0` | number > 0 |
   | `route_wait_seconds` | `30` | integer ≥ 1 |
   | `run_queue_wait_seconds` | `3600` | integer ≥ 1 |
   | `run_deadline_seconds` | `21600` | integer ≥ 1 |
   | `supersede_grace_seconds` | `30` | integer ≥ 1 |
   | `stale_lock_seconds` | `300` | integer ≥ 0 |
   | `probe_timeout_seconds` | `10` | integer ≥ 1 |
   | `doctor_probe_timeout_seconds` | `120` | integer ≥ 1 |
   | `publish_progress` | `true` | boolean |
   | `seats` | `{}` | see behaviour 4 |

   Integer keys refuse `bool` and non-`int` ("must be an integer"), then the range:
   "must be an integer from <low> to <high>" or "must be an integer of at least <low>".
   Number keys accept `int` or `float` (not `bool`; "must be a number"), stored as `float`:
   "must be a number of at least 0" / "must be a number greater than 0". Boolean keys refuse
   anything but `bool`: "must be true or false". Any key not in the table above:
   `ConfigError(f"loop_services.<loop>.<key>", f"unknown key {key!r}")`. A non-table loop
   value: `ConfigError("loop_services.<loop>", "must be a table")`.
4. **Seats.** `[loop_services.<loop>.seats."<name>"]` becomes `SeatConfig(prefetch: int | None = None)`.
   - The name must be one of the loop's `effective_models(loop_id)`, else
     `ConfigError(f"loop_services.<loop>.seats.<name>", f"<name> is not a declared seat of <loop>")`.
   - Its only key is `prefetch`, an integer 1–64; any other key is "unknown key".
   - A non-table seat, or a non-table `seats`, is refused ("must be a table", "must be a table of seat tables").
5. **Methods.**
   - `LoopServicesConfig.for_loop(loop_id: LoopId) -> LoopConfig`.
   - `LoopConfig.effective_models(loop_id: LoopId) -> tuple[str, ...]`: `models` when
     non-empty; else sovereignloop `(default_model,)`; else paidloop
     `(DEFAULT_ADAPTER[LoopId.PAIDLOOP].value,)`, i.e. `("claudeloop",)` (8.b; #377's chart
     default `models: [claudeloop]`).
   - `LoopConfig.prefetch_for(seat_name: str) -> int`: that seat's `prefetch` when set, else `capacity`.
   - `LoopConfig.context_for(model: str) -> int`: `model_context[model]`, else
     `MODEL_CONTEXT_DEFAULTS[model]` (`{"gpt-oss:20b": 131072}`), else `32768`.
   - `LoopConfig.declarations() -> tuple[ModelDeclaration, ...]`: for sovereignloop, one
     `ModelDeclaration(name, context_for(name))` per `models or (default_model,)`; `()` when
     `default_model is None` (paidloop).
6. **The parser is a class**, `LoopServicesConfigParser`, with
   `parse(self, data: Mapping[str, Any]) -> LoopServicesConfig` reading `data.get("loop_services", {})`.
   `parse_config` calls it once: `loop_services=LoopServicesConfigParser().parse(data)`, and
   `VibeyConfig` gains `loop_services: LoopServicesConfig = field(default_factory=LoopServicesConfig)`
   as a new last field. The default `LoopServicesConfig()` equals `parse({})`.
7. **Environment.** `_SURFACE_ENV_VARS` gains two rows, directly after R01's last row
   `("engines", "invocation", "VIBEY_ENGINE_INVOCATION", str),`:
   `("loop_services", "root", "VIBEY_LOOP_SERVICES_ROOT", str)` and
   `("loop_services", "state_dir", "VIBEY_LOOP_SERVICES_STATE_DIR", str)`. An empty value is
   unset, as for every row (`apply_env_overrides`, `config_loader.py:62-80`).
8. **`ConfigError` moves** verbatim (class, docstring, `__init__`) from `config.py:38-44` to the
   end of `src/vibey/domain/errors.py`, with one added docstring sentence saying why it lives
   there. `config.py` imports it with the explicit re-export form
   `from vibey.domain.errors import ConfigError as ConfigError` (mypy `--strict` has no implicit
   re-export) and no longer imports `VibeyError`.
9. `domain/` stays pure: the new module imports only the standard library and
   `vibey.domain.{engine, errors, loop, residency}` (never `vibey.domain.config`).

## Where to change
- New `src/vibey/domain/loop_services_config.py`; new
  `src/vibey/domain/interfaces/loop_services_config_interface.py`. Line 1 of each is the
  provenance line copied byte for byte from line 1 of `src/vibey/domain/config.py`.
- Reference implementation of the new module (write it whole; `write_file` is fine for a new file):
  ```python
  """`[loop_services]`: the two loops' settings (ADR-0046 §3, §4, §6, §11; sub-doctrine 8.c).

  Exactly two loops, a single instance per model: `[loop_services.sovereignloop]`, whose seats
  are models, and `[loop_services.paidloop]`, whose seats are engine ids. Throughput is
  `capacity` (a seat's prefetch), never a copy, so `replicas` is refused wherever it is
  written. Pure: this module validates an already-parsed mapping. Whether every paid seat is a
  PAID descriptor is checked at composition (lane loops-bootstrap-loop-service): descriptors
  are infrastructure.
  """

  from collections.abc import Mapping, Sequence
  from dataclasses import dataclass, field
  from types import MappingProxyType
  from typing import Any, ClassVar, Final

  from vibey.domain.engine import ENGINE_ID_PARSER
  from vibey.domain.errors import ConfigError
  from vibey.domain.loop import DEFAULT_ADAPTER, LoopId
  from vibey.domain.residency import ModelDeclaration, SeatSlug

  #: Sub-doctrine 8.d's designation; equal to the Ollama client's DEFAULT_OLLAMA_MODEL.
  DEFAULT_SOVEREIGN_MODEL: Final = "gpt-oss:20b"
  #: A model's context window when `model_context` does not name it.
  MODEL_CONTEXT_DEFAULTS: Final[Mapping[str, int]] = MappingProxyType({"gpt-oss:20b": 131_072})
  #: Neither table names the model; equal to config.DEFAULT_LOCAL_CONTEXT_WINDOW.
  DEFAULT_MODEL_CONTEXT: Final = 32_768
  REPLICAS_REFUSED: Final = (
      "replicas is not a key: sub-doctrine 8.c runs a single instance per model; "
      "raise capacity instead"
  )
  TWO_LOOPS: Final = "loop_services has exactly two loops (8.c): sovereignloop and paidloop"


  @dataclass(frozen=True, slots=True)
  class SeatConfig:
      """One seat's own prefetch; None means the loop's `capacity`."""

      prefetch: int | None = None


  @dataclass(frozen=True, slots=True)
  class LoopConfig:
      """One loop's settings. `default_model` is sovereignloop's; paidloop's is None."""

      models: tuple[str, ...] = ()
      default_model: str | None = None
      model_context: dict[str, int] = field(default_factory=dict)
      capacity: int = 1
      router_prefetch: int = 16
      delivery_limit: int = 3
      consumer_timeout_seconds: int = 21_600
      residency_max_wait_seconds: float = 900.0
      residency_min_hold_runs: int = 1
      unload_on_switch: bool = True
      schedule_interval_seconds: float = 5.0
      route_wait_seconds: int = 30
      run_queue_wait_seconds: int = 3_600
      run_deadline_seconds: int = 21_600
      supersede_grace_seconds: int = 30
      stale_lock_seconds: int = 300
      probe_timeout_seconds: int = 10
      doctor_probe_timeout_seconds: int = 120
      publish_progress: bool = True
      seats: dict[str, SeatConfig] = field(default_factory=dict)

      def effective_models(self, loop_id: LoopId) -> tuple[str, ...]:
          if self.models:
              return self.models
          if loop_id is LoopId.SOVEREIGNLOOP:
              return (self.default_model or DEFAULT_SOVEREIGN_MODEL,)
          return (DEFAULT_ADAPTER[LoopId.PAIDLOOP].value,)

      def prefetch_for(self, seat_name: str) -> int:
          seat = self.seats.get(seat_name)
          if seat is not None and seat.prefetch is not None:
              return seat.prefetch
          return self.capacity

      def context_for(self, model: str) -> int:
          default = MODEL_CONTEXT_DEFAULTS.get(model, DEFAULT_MODEL_CONTEXT)
          return self.model_context.get(model, default)

      def declarations(self) -> tuple[ModelDeclaration, ...]:
          if self.default_model is None:
              return ()
          names = self.models or (self.default_model,)
          return tuple(ModelDeclaration(name=n, context_window=self.context_for(n)) for n in names)


  @dataclass(frozen=True, slots=True)
  class LoopServicesConfig:
      root: str = "/"
      state_dir: str = ""
      sovereignloop: LoopConfig = field(
          default_factory=lambda: LoopConfig(default_model=DEFAULT_SOVEREIGN_MODEL)
      )
      paidloop: LoopConfig = field(default_factory=LoopConfig)

      def for_loop(self, loop_id: LoopId) -> LoopConfig:
          return self.sovereignloop if loop_id is LoopId.SOVEREIGNLOOP else self.paidloop


  class LoopServicesConfigParser:
      """Validates `[loop_services]`; every error names its dotted key."""

      INTEGER_KEYS: ClassVar[Mapping[str, tuple[int, int | None]]] = MappingProxyType(
          {
              "capacity": (1, 64),
              "router_prefetch": (1, 1000),
              "delivery_limit": (1, 1000),
              "consumer_timeout_seconds": (60, None),
              "residency_min_hold_runs": (0, None),
              "route_wait_seconds": (1, None),
              "run_queue_wait_seconds": (1, None),
              "run_deadline_seconds": (1, None),
              "supersede_grace_seconds": (1, None),
              "stale_lock_seconds": (0, None),
              "probe_timeout_seconds": (1, None),
              "doctor_probe_timeout_seconds": (1, None),
          }
      )
      #: key -> (lowest, whether the lowest value itself is allowed)
      NUMBER_KEYS: ClassVar[Mapping[str, tuple[float, bool]]] = MappingProxyType(
          {"residency_max_wait_seconds": (0.0, True), "schedule_interval_seconds": (0.0, False)}
      )
      BOOLEAN_KEYS: ClassVar[frozenset[str]] = frozenset({"unload_on_switch", "publish_progress"})
      LOOP_KEYS: ClassVar[frozenset[str]] = frozenset(
          {"models", "default_model", "model_context", "seats"}
          | set(INTEGER_KEYS)
          | set(NUMBER_KEYS)
          | {"unload_on_switch", "publish_progress"}
      )

      def parse(self, data: Mapping[str, Any]) -> LoopServicesConfig:
          raw = data.get("loop_services", {})
          if not isinstance(raw, Mapping):
              raise ConfigError("loop_services", "must be a table")
          self._refuse_replicas(raw, "loop_services")
          if set(raw) - {"root", "state_dir", "sovereignloop", "paidloop"}:
              raise ConfigError("loop_services", TWO_LOOPS)
          return LoopServicesConfig(
              root=self._path(raw, "root", "/", allow_empty=False),
              state_dir=self._path(raw, "state_dir", "", allow_empty=True),
              sovereignloop=self._loop(raw.get("sovereignloop", {}), LoopId.SOVEREIGNLOOP),
              paidloop=self._loop(raw.get("paidloop", {}), LoopId.PAIDLOOP),
          )

      def _refuse_replicas(self, table: Mapping[str, Any], path: str) -> None:
          if "replicas" in table:
              raise ConfigError(f"{path}.replicas", REPLICAS_REFUSED)

      def _path(self, table: Mapping[str, Any], key: str, default: str, *, allow_empty: bool) -> str:
          where = f"loop_services.{key}"
          value = table.get(key, default)
          if not isinstance(value, str):
              raise ConfigError(where, "must be a string")
          if allow_empty and value == "":
              return value
          if not value.startswith("/"):
              expected = "empty or an absolute path" if allow_empty else "an absolute path"
              raise ConfigError(where, f"must be {expected}")
          return value

      def _loop(self, raw: object, loop_id: LoopId) -> LoopConfig:
          path = f"loop_services.{loop_id}"
          if not isinstance(raw, Mapping):
              raise ConfigError(path, "must be a table")
          self._refuse_replicas(raw, path)
          for key in raw:
              if key not in self.LOOP_KEYS:
                  raise ConfigError(f"{path}.{key}", f"unknown key {key!r}")
          sovereign = loop_id is LoopId.SOVEREIGNLOOP
          if not sovereign and "default_model" in raw:
              raise ConfigError(
                  f"{path}.default_model",
                  "paidloop's default adapter is claudeloop (sub-doctrine 8.b); "
                  "name its seats with models",
              )
          if not sovereign and "model_context" in raw:
              raise ConfigError(
                  f"{path}.model_context", "model_context is sovereignloop's: its seats are models"
              )
          models = self._models(raw, path, sovereign)
          default_model = self._default_model(raw, path, models) if sovereign else None
          effective = LoopConfig(models=models, default_model=default_model).effective_models(loop_id)
          values: dict[str, Any] = {}
          for key, (low, high) in self.INTEGER_KEYS.items():
              if key in raw:
                  values[key] = self._integer(raw[key], f"{path}.{key}", low, high)
          for key, (lowest, inclusive) in self.NUMBER_KEYS.items():
              if key in raw:
                  values[key] = self._number(raw[key], f"{path}.{key}", lowest, inclusive)
          for key in sorted(self.BOOLEAN_KEYS):
              if key in raw:
                  values[key] = self._boolean(raw[key], f"{path}.{key}")
          return LoopConfig(
              models=models,
              default_model=default_model,
              model_context=self._model_context(raw, path, effective),
              seats=self._seats(raw, path, effective, loop_id),
              **values,
          )

      def _models(self, raw: Mapping[str, Any], path: str, sovereign: bool) -> tuple[str, ...]:
          where = f"{path}.models"
          value = raw.get("models", [])
          if not isinstance(value, list) or not all(isinstance(m, str) and m.strip() for m in value):
              raise ConfigError(where, "must be a list of non-empty strings")
          models = tuple(value)
          if not sovereign:
              for engine in models:
                  member = ENGINE_ID_PARSER.known(engine)
                  if member is None or member.value != engine:
                      raise ConfigError(where, f"{engine} is not an engine id")
                  if member is DEFAULT_ADAPTER[LoopId.SOVEREIGNLOOP]:
                      raise ConfigError(
                          where,
                          "sovereignloop is sovereignloop's adapter, not a paid one (sub-doctrine 8.b)",
                      )
          self._slugs(models, where)
          return models

      def _default_model(self, raw: Mapping[str, Any], path: str, models: tuple[str, ...]) -> str:
          where = f"{path}.default_model"
          value = raw.get("default_model", DEFAULT_SOVEREIGN_MODEL)
          if not isinstance(value, str) or not value.strip():
              raise ConfigError(where, "must be a model name")
          if models and value not in models:
              raise ConfigError(where, f"{value} is not one of models")
          if not models:
              self._slugs((value,), where)
          return value

      def _slugs(self, names: Sequence[str], where: str) -> None:
          try:
              SeatSlug().unique(names)
          except ValueError as exc:
              raise ConfigError(where, str(exc)) from exc

      def _model_context(
          self, raw: Mapping[str, Any], path: str, effective: tuple[str, ...]
      ) -> dict[str, int]:
          where = f"{path}.model_context"
          value = raw.get("model_context", {})
          if not isinstance(value, Mapping):
              raise ConfigError(where, "must be a table of model = context window")
          contexts: dict[str, int] = {}
          for model, window in value.items():
              if model not in effective:
                  raise ConfigError(f"{where}.{model}", f"{model} is not a declared model")
              contexts[model] = self._integer(window, f"{where}.{model}", 1, None)
          return contexts

      def _seats(
          self, raw: Mapping[str, Any], path: str, effective: tuple[str, ...], loop_id: LoopId
      ) -> dict[str, SeatConfig]:
          where = f"{path}.seats"
          value = raw.get("seats", {})
          if not isinstance(value, Mapping):
              raise ConfigError(where, "must be a table of seat tables")
          seats: dict[str, SeatConfig] = {}
          for name, table in value.items():
              seat_path = f"{where}.{name}"
              if not isinstance(table, Mapping):
                  raise ConfigError(seat_path, "must be a table")
              self._refuse_replicas(table, seat_path)
              if name not in effective:
                  raise ConfigError(seat_path, f"{name} is not a declared seat of {loop_id}")
              for key in table:
                  if key != "prefetch":
                      raise ConfigError(f"{seat_path}.{key}", f"unknown key {key!r}")
              prefetch = table.get("prefetch")
              seats[name] = SeatConfig(
                  prefetch=None
                  if prefetch is None
                  else self._integer(prefetch, f"{seat_path}.prefetch", 1, 64)
              )
          return seats

      def _integer(self, value: object, where: str, low: int, high: int | None) -> int:
          if isinstance(value, bool) or not isinstance(value, int):
              raise ConfigError(where, "must be an integer")
          if value < low or (high is not None and value > high):
              bound = f"from {low} to {high}" if high is not None else f"of at least {low}"
              raise ConfigError(where, f"must be an integer {bound}")
          return value

      def _number(self, value: object, where: str, lowest: float, inclusive: bool) -> float:
          if isinstance(value, bool) or not isinstance(value, int | float):
              raise ConfigError(where, "must be a number")
          if value < lowest or (value == lowest and not inclusive):
              bound = "of at least" if inclusive else "greater than"
              raise ConfigError(where, f"must be a number {bound} {lowest:g}")
          return float(value)

      def _boolean(self, value: object, where: str) -> bool:
          if not isinstance(value, bool):
              raise ConfigError(where, "must be true or false")
          return value
  ```
  Run `uv run ruff format src/vibey/domain/loop_services_config.py` after writing it; keep
  every name and message exactly as above. If lane `loops-residency-policy` named
  `SeatSlug.unique`'s argument differently, adapt the one call and say so in the commit body.
- The interface module declares `@runtime_checkable` Protocols `SeatConfigInterface`
  (`prefetch`), `LoopConfigInterface` (every field above as a read-only property, plus
  `effective_models(self, loop_id: LoopId) -> tuple[str, ...]`, `prefetch_for`, `context_for`,
  `declarations(self) -> tuple[ModelDeclaration, ...]`), `LoopServicesConfigInterface` (`root`,
  `state_dir`, `sovereignloop`, `paidloop`, `for_loop`) and
  `LoopServicesConfigParserInterface` (`parse`). Import `LoopId` and `ModelDeclaration` under
  `if TYPE_CHECKING:` with `from __future__ import annotations`, as
  `domain/interfaces/value_objects_interface.py` avoids runtime sibling imports. Lane
  `loops-seat-host-core` types its `config` argument as `LoopConfigInterface`.
- `src/vibey/domain/errors.py` (83 lines at `d3b4a388`): append `ConfigError` (behaviour 8)
  with `edit_file` or an append; add this docstring sentence:
  "It lives here, not in `vibey.domain.config`, so a module `config.py` imports
  (`loop_services_config.py`) can raise it without an import cycle; `config.py` re-exports it."
- `src/vibey/domain/config.py` (`edit_file` only):
  - replace `from vibey.domain.errors import VibeyError` with
    `from vibey.domain.errors import ConfigError as ConfigError` and add
    `from vibey.domain.loop_services_config import LoopServicesConfig, LoopServicesConfigParser`
    (isort order; run `uv run ruff check --fix --select I src/vibey/domain/config.py`);
  - delete the `class ConfigError(VibeyError):` block (`:38-44`) and its two trailing blank lines;
  - append the `loop_services` field as the last `VibeyConfig` field;
  - add `loop_services=LoopServicesConfigParser().parse(data),` as the last keyword of the
    `VibeyConfig(...)` call in `parse_config`.
- `src/vibey/infrastructure/config_loader.py` (123 lines): insert the two rows (behaviour 7)
  with `edit_file`, anchored on R01's `    ("engines", "invocation", "VIBEY_ENGINE_INVOCATION", str),`.
  If R01 has not landed that row, stop and report (this lane depends on it).

## Acceptance criteria
- [ ] `parse_config({"project": {"name": "x"}}).loop_services == LoopServicesConfig()`; its `sovereignloop.effective_models(LoopId.SOVEREIGNLOOP) == ("gpt-oss:20b",)`, `paidloop.effective_models(LoopId.PAIDLOOP) == ("claudeloop",)`, `root == "/"`, `state_dir == ""`.
- [ ] Every row of behaviour 3's table has a default test and one invalid-value test naming its dotted key.
- [ ] `replicas` is refused at all three levels with the exact 8.c message.
- [ ] `[loop_services.opencode]` (or any third key) raises the exact "exactly two loops" message.
- [ ] `VIBEY_LOOP_SERVICES_ROOT=/work` reaches `loop_services.root` through `apply_env_overrides`; an empty value leaves the file's value.
- [ ] `from vibey.domain.config import ConfigError` and `from vibey.domain.errors import ConfigError` are the same class.
- [ ] `tests/domain/test_domain_purity.py` passes; 100% branch coverage of `src/vibey/domain/*` and `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
`tests/domain/test_loop_services_config.py` (no service; the last two import
`vibey.infrastructure.config_loader`, which a test may do):
- `test_defaults`: behaviour 6's equality and every default in the table.
- `test_root_must_be_absolute` and `test_state_dir_is_empty_or_absolute` (including non-string values).
- `test_replicas_is_refused_at_every_level` (parametrized over the three dotted keys).
- `test_loop_services_has_exactly_two_loops`.
- `test_unknown_loop_key_is_refused`.
- `test_integer_keys_are_bounded` (parametrized over `INTEGER_KEYS`: below the low bound, above the high bound where there is one, a `bool`, and a string).
- `test_number_keys_are_bounded` (`residency_max_wait_seconds = -1`, `schedule_interval_seconds = 0`, an `int` accepted as `float`).
- `test_boolean_keys_refuse_non_booleans`.
- `test_sovereign_models_must_have_unique_unreserved_slugs` (`["gpt-oss:20b", "gpt-oss-20b"]`; `["probe"]`).
- `test_models_must_be_a_list_of_non_empty_strings`.
- `test_default_model_must_be_one_of_models`.
- `test_default_model_is_sovereign_only`: the exact paidloop message.
- `test_paid_models_are_canonical_engine_ids` (`["bogus"]`, `["qwenloop"]`, `["sovereignloop"]` refused; `["claudeloop", "codexloop"]` accepted).
- `test_model_context_is_sovereign_only_and_names_declared_models`.
- `test_context_for_prefers_the_table_then_the_builtin_then_32768`.
- `test_declarations_follow_models_or_the_default` (and `()` for paidloop).
- `test_seat_prefetch_overrides_capacity` (`prefetch_for` both ways).
- `test_seats_must_be_declared_and_hold_only_prefetch` (undeclared name, unknown key, non-table seat, non-table `seats`, prefetch 0 and 65).
- `test_for_loop_returns_each_loop`.
- `test_the_default_model_is_the_8d_designation`: `DEFAULT_SOVEREIGN_MODEL == vibey.infrastructure.engines.ollama_chat.DEFAULT_OLLAMA_MODEL` and `DEFAULT_MODEL_CONTEXT == vibey.domain.config.DEFAULT_LOCAL_CONTEXT_WINDOW`.
- `test_config_error_moved_and_is_re_exported`.
- `test_values_satisfy_their_interfaces` (all four Protocols).
- `test_loop_services_env_overrides_win`: `apply_env_overrides(data, environ={"VIBEY_LOOP_SERVICES_ROOT": "/work", "VIBEY_LOOP_SERVICES_STATE_DIR": "/state"})` then `parse_config(data)`.
- `test_empty_loop_services_env_value_is_unset`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain/test_loop_services_config.py tests/domain/test_config.py tests/domain/test_domain_purity.py tests/infrastructure/test_config_loader.py
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_sovereign_surfaces.py tests/test_bootstrap.py tests/cli
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

The full `--cov` run needs PostgreSQL until lane `fakes-harness-decouple` lands.

## Out of scope
- Reading these keys at runtime (the loop-service lanes, `loops-bootstrap-loop-service`,
  `loops-invocation-composition`) and the tier check of paid seats (composition).
- `[engines] invocation` and `[bus]`/`[queue]` (R01, #348).
- The chart (#377) and the doctor (#380).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees (the docs wave).
- Do not push or change remotes. Commit locally with the Title as the subject.

**Depends on:** `rmq-r01-queue-config`, `loops-residency-policy`, `loops-domain-loop-id`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
