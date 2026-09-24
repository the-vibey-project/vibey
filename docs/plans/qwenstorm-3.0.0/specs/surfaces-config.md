## Title
feat(domain): [surfaces] and [surfaces.cache] declare every surface-lane tunable, validated with its dotted key

## Why
Draft ADR-0047 §13 (`specs/ADR-surface-lanes.md`) makes every tunable of the surface lanes a
`vibey.toml` key (sub-doctrine 12.c: "a hard-coded value that could have been a key is a
decision taken away from the next adopter"), with environment beating the file and the file
beating the default. It also names the two numbers that are deliberately **not** keys: the lane
count per surface, which 8.f fixes at one, and the write prefetch, which is 1 because FIFO
replay safety depends on it (§8).

This lane adds two keys the ADR left open, both for 12.c:
- `adapter_timeout_seconds`: the socket timeout every sovereign adapter passes to every
  network call. Today the adapters pass none (`src/vibey/infrastructure/tracker/plane.py:61`,
  `:77`, and the list in `issue-audit/gaps.md` K3). It must not exceed
  `operation_timeout_seconds`, so an adapter call cannot outlive the operation bound (ADR
  "Consequences", "A timeout is still ambiguous").
- `dead_drain_batch`: how many dead letters one reconcile drains (§9), like R01's
  `dead_drain_batch` for the job queue (`issue-audit/updates/348.md` behaviour 2).

ADR-0047 lane S01. Environment overrides are `surfaces-config-env`.

## Required behaviour
In `src/vibey/domain/config.py`:

1. `DEFAULT_SURFACE_TRANSPORT: Final = "direct"` (module constant; `surfaces-default-flip`
   changes it to `"queue"`).
2. `@dataclass(frozen=True, slots=True) class SurfaceCacheLaneConfig`: `memo: bool = True`,
   `memo_max_entries: int = 10_000`, `memo_max_value_bytes: int = 65_536`.
3. `@dataclass(frozen=True, slots=True) class SurfacesConfig` with these fields and defaults:

   | field | default | constraint (else `ConfigError(<dotted key>, ...)`) |
   |---|---|---|
   | `transport: str` | `DEFAULT_SURFACE_TRANSPORT` | `direct` or `queue` |
   | `adapter_timeout_seconds: int` | 30 | 1–3600, and ≤ `operation_timeout_seconds` |
   | `read_timeout_seconds: int` | 5 | 1–300 |
   | `write_timeout_seconds: int` | 30 | 1–3600 |
   | `operation_timeout_seconds: int` | 60 | 1–3600 |
   | `send_start_by_seconds: int` | 86_400 | 60–2_592_000 |
   | `sends_await_outcome: bool` | False | bool |
   | `delivery_limit: int` | 5 | 1–100 |
   | `consumer_timeout_seconds: int` | 900 | ≥ 60 and ≥ `operation_timeout_seconds × (len(retry_backoff_seconds) + 1) + sum(retry_backoff_seconds) + 60` |
   | `retry_backoff_seconds: tuple[int, ...]` | `(1, 5, 30)` | a TOML list of 0–10 ints, each 0–3600 |
   | `read_prefetch: int` | 64 | 1–1024 |
   | `read_max_length: int` | 10_000 | ≥ 1 |
   | `write_max_length: int` | 100_000 | ≥ 1 |
   | `inline_max_bytes: int` | 8_388_608 | 1_024–15_728_640 |
   | `reconcile_interval_seconds: int` | 30 | ≥ 1 |
   | `dead_drain_batch: int` | 100 | 1–10_000 |
   | `standby_poll_seconds: int` | 5 | ≥ 1 |
   | `drain_grace_seconds: int` | 30 | ≥ 0 |
   | `cache: SurfaceCacheLaneConfig` | `SurfaceCacheLaneConfig()` | `memo` bool; `memo_max_entries` 0–1_000_000 (0 disables); `memo_max_value_bytes` ≥ 0 |

   An `int` field refuses a `bool` (TOML `true` is not `1`). Each error names its dotted key,
   for example `ConfigError("surfaces.cache.memo_max_entries", "must be between 0 and 1000000, got -1")`;
   the consumer-timeout error names the minimum and the formula.
4. `def _parse_surfaces(data: dict[str, Any]) -> SurfacesConfig`, reading `[surfaces]` and
   `[surfaces.cache]` with the `_optional` helper (`config.py:358-364`), copying the
   `_parse_bus` pattern (`:623-629`). A module-level function like its siblings; its docstring
   says so.
5. `VibeyConfig` (`:318-342`) gains `surfaces: SurfacesConfig = field(default_factory=SurfacesConfig)`
   as its last field; `parse_config` (`:652`) passes `surfaces=_parse_surfaces(data)`.
6. In `src/vibey/domain/interfaces/config_interface.py`, add `@runtime_checkable` read-only
   Protocols `SurfaceCacheLaneConfigInterface` and `SurfacesConfigInterface` (one property per
   field; `cache` typed with the first), in the style of `TelemetryConfigInterface` (`:30-36`);
   export both from `src/vibey/domain/interfaces/__init__.py`.

## Where to change
- `src/vibey/domain/config.py`, `src/vibey/domain/interfaces/config_interface.py`,
  `src/vibey/domain/interfaces/__init__.py`.
- New `tests/domain/test_surfaces_config.py` (not an append to `tests/domain/test_config.py`,
  which R01 and T05 also extend).

## Acceptance criteria
- [ ] `parse_config({"project": {"name": "x"}}).surfaces` equals `SurfacesConfig()` with every default in the table, and `transport == "direct"`.
- [ ] Each constraint in the table refuses a bad value with a `ConfigError` whose path is the dotted key (one parametrized case per key, plus `true` for an int).
- [ ] `adapter_timeout_seconds = 90` with `operation_timeout_seconds = 60` is refused; `retry_backoff_seconds = [1, 5, 30, 60]` with `consumer_timeout_seconds = 300` is refused naming the minimum 456 (60 × 5 + 96 + 60).
- [ ] `isinstance(config.surfaces, SurfacesConfigInterface)` and `isinstance(config.surfaces.cache, SurfaceCacheLaneConfigInterface)`.
- [ ] `test_domain_purity.py` passes; 100% `domain/` branch coverage.

## Tests to write first (TDD)
`tests/domain/test_surfaces_config.py` (no service):
- `test_defaults_match_the_adr_table`
- `test_each_key_is_bounded` (parametrized over the table)
- `test_ints_refuse_booleans`
- `test_adapter_timeout_cannot_exceed_the_operation_timeout`
- `test_consumer_timeout_covers_every_retry`
- `test_backoff_is_a_short_list_of_bounded_ints`
- `test_transport_is_direct_or_queue`
- `test_surfaces_config_satisfies_its_interfaces`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/domain/test_surfaces_config.py tests/domain/test_config.py tests/domain/test_domain_purity.py
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- Environment overrides (`surfaces-config-env`). Reading any key at runtime (later lanes).
- CHANGELOG.md, docs/ (`docs/reference/configuration.md` is `surfaces-docs-wave`'s), ADRs,
  CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees. Do not push, open PRs or change remotes.
  Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `rmq-r01-queue-config` (it edits the same `VibeyConfig` and `parse_config`; land after it).
- **Shares a file with:** `src/vibey/domain/config.py` (R01 → T05 → R34 → T28, ADR-0046's loop configuration). Keep every field they added; add yours last.
- **Must keep passing unchanged:** `tests/domain/test_config.py`, `tests/infrastructure/test_config_loader.py`, `tests/domain/test_domain_purity.py`, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `STORM/EDITING-RULES.md` before changing a file. `config.py` is long: `edit_file` only.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from a sibling file.
  - The default run needs no service; never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.
  - `[surfaces] transport` stays `direct` by default until `surfaces-default-flip`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
