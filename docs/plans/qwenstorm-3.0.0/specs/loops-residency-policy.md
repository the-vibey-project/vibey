## Title
feat(domain): seat slugs and the residency policy that picks sovereignloop's model

ADR-0046 lane L02a (slug `loops-residency-policy`).

## Why
- **The law.** Sub-doctrine 8.c (`src/vibey_tools/gh/docs/doctrines.md:196-234`) makes the inner
  rotation layer "mindful that a machine keeps one model resident", and it runs "a single instance
  per model". The rule was learned by measurement: three qwenloop sessions on one model server
  overflowed its context. 8.d makes `gpt-oss:20b` this era's default model.
- **The decision.**
  - ADR-0046 §3 "Seat names" (`specs/ADR-two-loops.md:154`): a sovereign seat is the model's
    slug, "lower case, and every character outside `[a-z0-9-]` becomes `-`, so `gpt-oss:20b`
    becomes `gpt-oss-20b`". `probe` and `dead` are reserved, and "two models that map to one slug
    are a configuration error".
  - A paid seat is `<engine-id>`, or `<engine-id>.<model-slug>` once an adapter drives several
    models (`:155`).
  - ADR-0046 §4 (`:193-200`): `ResidencyPolicy` chooses the model in a fixed order. First the
    resident model if it can carry the job (a matching pin, and at least `min_context`); else the
    machine's default; else the first declared model that can; else the route is `UNROUTABLE`
    with "no local model can carry this job".
  - §10 places `residency.py` in `domain/` (`:302`), and non-negotiable 4 (`:335`) keeps it pure:
    the caller passes every fact in.
- **The gap, at integration `d3b4a388`.** Nothing in `src/vibey/domain/` names seats or chooses a
  model. The only model choice is an Ollama model string: `OllamaChatClient`'s default and
  `LocalEndpointEnvironment` (`src/vibey/infrastructure/engines/local_engines.py:158-188`), with
  no notion of which model is loaded.
- **9.b** (`doctrines.md:349`): every class gets an interface beside it.

## Required behaviour
1. **`src/vibey/domain/residency.py`** (new). Its module docstring cites ADR-0046 §3 "Seat names"
   and §4, and says the policy is pure: the resident model and every declaration are arguments.
   It defines, in this order:
   ```python
   RESERVED_SEATS: Final[frozenset[str]] = frozenset({"probe", "dead"})
   UNROUTABLE_NO_MODEL: Final = "no local model can carry this job"
   CHOSEN_RESIDENT: Final = "resident"
   CHOSEN_DEFAULT: Final = "default"
   CHOSEN_FIRST_DECLARED: Final = "first declared"
   _OUTSIDE_SLUG: Final = re.compile(r"[^a-z0-9-]")
   ```
2. **`class SeatSlug`** (no state):
   ```python
   class SeatSlug:
       def of(self, name: str) -> str:
           slug = _OUTSIDE_SLUG.sub("-", name.lower())
           if not slug:
               raise ValueError(f"seat name {name!r} is empty")
           if slug in RESERVED_SEATS:
               raise ValueError(f"seat name {name!r} slugs to {slug!r}, which is reserved")
           return slug

       def of_paid(self, engine_id: str, model: str | None = None) -> str:
           return engine_id if model is None else f"{engine_id}.{self.of(model)}"

       def unique(self, names: Sequence[str]) -> Mapping[str, str]:
           seats: dict[str, str] = {}
           for name in names:
               slug = self.of(name)
               if slug in seats:
                   raise ValueError(f"seats {seats[slug]} and {name} share the slug {slug}")
               seats[slug] = name
           return MappingProxyType(seats)
   ```
   - `SeatSlug().of("gpt-oss:20b") == "gpt-oss-20b"`.
   - `unique` maps each slug to its declared name, in declared order. It raises on the second
     name that shares a slug with an earlier one.
3. **`@dataclass(frozen=True, slots=True) class ModelDeclaration`**, with `name: str` and
   `context_window: int`. `__post_init__` raises
   `ValueError(f"ModelDeclaration.context_window must be at least 1, got {self.context_window}")`
   when `context_window < 1`.
4. **`@dataclass(frozen=True, slots=True) class ModelChoice`**, with `model: str`,
   `switched: bool` and `reason: str`. `reason` is one of `CHOSEN_RESIDENT`, `CHOSEN_DEFAULT` or
   `CHOSEN_FIRST_DECLARED`. It is not validated.
5. **`class ResidencyPolicy`** (no state):
   ```python
   class ResidencyPolicy:
       def choose(
           self,
           *,
           resident: str | None,
           default: str | None,
           declared: Sequence[ModelDeclaration],
           model_pin: str | None,
           min_context: int | None,
       ) -> ModelChoice | None:
           order: list[tuple[str | None, str]] = [
               (resident, CHOSEN_RESIDENT),
               (default, CHOSEN_DEFAULT),
               *((d.name, CHOSEN_FIRST_DECLARED) for d in declared),
           ]
           for name, reason in order:
               if name is not None and self._can_carry(name, declared, model_pin, min_context):
                   switched = resident is not None and name != resident
                   return ModelChoice(model=name, switched=switched, reason=reason)
           return None

       @staticmethod
       def _can_carry(
           name: str,
           declared: Sequence[ModelDeclaration],
           model_pin: str | None,
           min_context: int | None,
       ) -> bool:
           declaration = next((d for d in declared if d.name == name), None)
           if declaration is None:
               return False
           if model_pin is not None and name != model_pin:
               return False
           return min_context is None or declaration.context_window >= min_context
   ```
   - A model "can carry" the job when it is declared, matches the pin (if any), and has at least
     `min_context` (if any).
   - The order is: the resident model, then the default, then the first declared model that can.
   - `switched` is True exactly when a resident exists and the chosen model is not it.
   - `None` means unroutable. The router (a later lane) replies `UNROUTABLE` with the reason
     `UNROUTABLE_NO_MODEL`.
   - A resident or default model that is not declared is never chosen.
6. **`src/vibey/domain/interfaces/residency_interface.py`** (new) declares these
   `@runtime_checkable` Protocols. It starts with `from __future__ import annotations`, and it
   imports `ModelChoice` and `ModelDeclaration` only under `if TYPE_CHECKING:`.
   - `SeatSlugInterface`, with `of`, `of_paid` and `unique` (the signatures above).
   - `ModelDeclarationInterface`, with read-only properties `name: str` and `context_window: int`.
   - `ModelChoiceInterface`, with properties `model: str`, `switched: bool` and `reason: str`.
   - `ResidencyPolicyInterface`, with `choose` (the keyword-only signature above; `declared` is
     `Sequence[ModelDeclaration]`, and it returns `ModelChoice | None`).

   Copy the layout of `src/vibey/domain/interfaces/ledger_query_interface.py:1-21`. A property
   Protocol is written as `@property` then `def name(self) -> str: ...`, as in
   `value_objects_interface.py:32-38`.
7. The module is pure: `re` is stdlib, and there is no I/O, clock or async.
   `tests/domain/test_domain_purity.py` walks it.
8. Lane `loops-residency-schedule` appends to both files next. Keep `from collections.abc import
   Mapping, Sequence` and `from dataclasses import dataclass` imported, because it needs them.

## Where to change
- New: `src/vibey/domain/residency.py`, `src/vibey/domain/interfaces/residency_interface.py`,
  `tests/domain/test_residency_policy.py`.
- Line 1 of each new file is the provenance comment, copied byte for byte from line 1 of
  `src/vibey/domain/engine.py`.
- Imports in `residency.py`: `re`; `Mapping` and `Sequence` from `collections.abc`; `dataclass`;
  `MappingProxyType` from `types`; `Final` from `typing`.
- No fake is registered: domain policies are tested with the real pure classes.

## Acceptance criteria
- [ ] `SeatSlug().of("gpt-oss:20b") == "gpt-oss-20b"` (`test_the_default_model_slugs_as_the_adr_says`).
- [ ] `SeatSlug().unique(["gpt-oss:20b", "gpt-oss-20b"])` raises `ValueError` with exactly
      `seats gpt-oss:20b and gpt-oss-20b share the slug gpt-oss-20b`.
- [ ] `probe` and `dead`, in any case, are refused as seats.
- [ ] Each branch of `ResidencyPolicy.choose` has its own test, below.
- [ ] `tests/domain/test_domain_purity.py` passes, and 100% branch coverage of `src/vibey/domain/*`.

## Tests to write first (TDD)
`tests/domain/test_residency_policy.py` (pure objects only). Use
`GPT = ModelDeclaration("gpt-oss:20b", 131072)` and `QWEN = ModelDeclaration("qwen2.5-coder:14b", 32768)`.
- `test_the_default_model_slugs_as_the_adr_says`: `"gpt-oss:20b"` gives `"gpt-oss-20b"`;
  `"Qwen2.5-Coder:14B"` gives `"qwen2-5-coder-14b"`; `"a/b c"` gives `"a-b-c"`.
- `test_every_slug_uses_only_the_seat_alphabet` (Hypothesis, `@given(st.text(min_size=1))`):
  skip a slug that is reserved (`assume`); otherwise `re.fullmatch(r"[a-z0-9-]+", SeatSlug().of(name))`
  is not None and `len(slug) == len(name.lower())`.
- `test_an_empty_name_is_refused`: `pytest.raises(ValueError, match="seat name '' is empty")`.
- `test_reserved_slugs_are_refused`: `"probe"`, `"PROBE"` and `"dead"` raise `ValueError`; for
  `"PROBE"` the message is exactly `seat name 'PROBE' slugs to 'probe', which is reserved`.
- `test_a_paid_seat_is_the_engine_id_or_engine_dot_model`: `of_paid("claudeloop") == "claudeloop"`
  and `of_paid("vscode-paid", "gpt-5:mini") == "vscode-paid.gpt-5-mini"`.
- `test_unique_maps_slugs_to_names_in_declared_order`:
  `list(unique(["gpt-oss:20b", "qwen2.5-coder:14b"]).items()) == [("gpt-oss-20b", "gpt-oss:20b"),
  ("qwen2-5-coder-14b", "qwen2.5-coder:14b")]`, and assigning into the result raises `TypeError`.
- `test_unique_refuses_two_names_that_share_a_slug` (the acceptance message).
- `test_a_model_declaration_needs_a_positive_context_window`: `ModelDeclaration("m", 0)` raises
  with `ModelDeclaration.context_window must be at least 1, got 0`.
- `test_the_resident_model_is_kept_when_it_can_carry`: resident `"qwen2.5-coder:14b"`, default
  `"gpt-oss:20b"`, declared `(GPT, QWEN)`, no pin, no min_context →
  `ModelChoice("qwen2.5-coder:14b", switched=False, reason="resident")`.
- `test_the_default_is_chosen_when_the_resident_cannot_carry`: the same with `min_context=65536` →
  `ModelChoice("gpt-oss:20b", switched=True, reason="default")`.
- `test_the_first_declared_model_is_the_last_resort`: resident None, default `"missing:1b"` (not
  declared), declared `(QWEN, GPT)`, `min_context=65536` →
  `ModelChoice("gpt-oss:20b", switched=False, reason="first declared")`.
- `test_a_pin_names_the_only_model_that_can_carry`: resident `"gpt-oss:20b"`, default
  `"gpt-oss:20b"`, declared `(GPT, QWEN)`, pin `"qwen2.5-coder:14b"` →
  `ModelChoice("qwen2.5-coder:14b", switched=True, reason="first declared")`.
- `test_an_undeclared_resident_is_never_chosen`: resident `"phantom:7b"`, default None, declared
  `(GPT,)` → `ModelChoice("gpt-oss:20b", switched=True, reason="first declared")`.
- `test_nothing_can_carry_is_unroutable`: `min_context=10**6` → `None`; and
  `UNROUTABLE_NO_MODEL == "no local model can carry this job"`.
- `test_no_resident_is_never_a_switch`: resident None, default `"gpt-oss:20b"` → `switched=False`,
  `reason="default"`.
- `test_classes_satisfy_their_interfaces`: `SeatSlug()`, `ResidencyPolicy()`, `GPT` and a
  `ModelChoice` are instances of their four interfaces.

## Checks the lane must run (all must pass)
At `d3b4a388` the root `tests/conftest.py:146-151` creates a per-worker PostgreSQL database in
`pytest_configure`, so every pytest command below needs a reachable PostgreSQL
(`VIBEY_TEST_DATABASE_URL`) until lane `fakes-harness-decouple` lands.

    uv run ruff format src/vibey/domain/residency.py src/vibey/domain/interfaces/residency_interface.py tests/domain/test_residency_policy.py
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain/test_residency_policy.py tests/domain/test_domain_purity.py
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- `ResidencySchedule` and `SeatLoad` (lane `loops-residency-schedule`).
- The configuration that declares models and the default model (lane `loops-config-loop-services`).
- The RAM-tier catalogue default (#383). The caller passes `default`.
- Any runtime check of what Ollama has loaded (lane `loops-model-runtime`).
- Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees (the docs wave).
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

**Depends on:** nothing unmerged.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
