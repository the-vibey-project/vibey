## Title
feat(surfaces): build_app hands `[surfaces] adapter_timeout_seconds` to every real surface adapter, Redis included

## Why
Gap K3 requires every sovereign adapter to bound each call "with a configured timeout"; 12.c
(`src/vibey_tools/gh/docs/doctrines.md:455`) requires the bound to be a declared key. Lane
`gap-surface-timeouts-1` declares `[surfaces] adapter_timeout_seconds`
(`VIBEY_SURFACES_ADAPTER_TIMEOUT_SECONDS`, default 10), and lanes `-2` to `-5` give every
adapter a `timeout=` keyword. Nothing yet passes the configured value: `build_app` builds each
adapter with its default (`src/vibey/bootstrap.py:758-906` at integration `d3b4a388`), and
`RedisCacheAdapter(url=resolved_config.cache.url)` (`:860`) keeps its hard-coded
`timeout: int = 5` (`src/vibey/infrastructure/cache/redis.py:54`). This lane wires the key into
all twelve real adapters. The in-memory adapters take no timeout and are unchanged.

## Required behaviour
1. `src/vibey/bootstrap.py` imports `DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS` beside
   `VibeyConfig` (`from vibey.domain.config import ...`, `:77`).
2. Immediately before the tracker selection (`if (` above `and resolved_config.tracker.url`,
   `:751-757`), at that `if`'s indentation:
   ```python
   adapter_timeout = (
       resolved_config.surfaces.adapter_timeout_seconds
       if resolved_config is not None
       else DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS
   )
   ```
3. Each of the eleven multi-line constructor calls — `PlaneTrackerAdapter(`,
   `BookStackDocsAdapter(`, `OpenBaoSecretsAdapter(`, `NextcloudFilesAdapter(`,
   `ForwardEmailAdapter(`, `KannelSmsAdapter(`, `MatrixMessagingAdapter(`,
   `InfisicalConfigStoreAdapter(`, `RabbitMqBusAdapter(`, `GarageBlobAdapter(`,
   `WazuhSiemAdapter(` — gains `timeout=adapter_timeout,` as its first argument line, and
   `RedisCacheAdapter(url=resolved_config.cache.url)` becomes
   `RedisCacheAdapter(url=resolved_config.cache.url, timeout=adapter_timeout)`.
   Make behaviours 2 and 3 with this checked script through the `shell` tool (it anchors on
   text, not line numbers, because `surfaces-env`, `fakes-bootstrap-seam` and
   `gap-surface-notify-wiring` also edit this function):
   ```python
   from pathlib import Path
   p = Path("src/vibey/bootstrap.py")
   s = p.read_text()
   names = ["PlaneTrackerAdapter", "BookStackDocsAdapter", "OpenBaoSecretsAdapter",
            "NextcloudFilesAdapter", "ForwardEmailAdapter", "KannelSmsAdapter",
            "MatrixMessagingAdapter", "InfisicalConfigStoreAdapter", "RabbitMqBusAdapter",
            "GarageBlobAdapter", "WazuhSiemAdapter"]
   for name in names:
       opening = f" = {name}(\n"
       assert s.count(opening) == 1, (name, s.count(opening))
       at = s.index(opening) + len(opening)
       first_arg = s[at:s.index("\n", at)]
       indent = first_arg[: len(first_arg) - len(first_arg.lstrip(" "))]
       s = s[:at] + f"{indent}timeout=adapter_timeout,\n" + s[at:]
   redis = "RedisCacheAdapter(url=resolved_config.cache.url)"
   assert s.count(redis) == 1
   s = s.replace(redis, "RedisCacheAdapter(url=resolved_config.cache.url, timeout=adapter_timeout)")
   marker = "and resolved_config.tracker.url\n"
   assert s.count(marker) == 1
   if_at = s.rindex("if (\n", 0, s.index(marker))
   line_start = s.rindex("\n", 0, if_at) + 1
   pad = s[line_start:if_at]
   assert pad.strip() == "", repr(pad)
   block = (f"{pad}adapter_timeout = (\n{pad}    resolved_config.surfaces.adapter_timeout_seconds\n"
            f"{pad}    if resolved_config is not None\n"
            f"{pad}    else DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS\n{pad})\n")
   p.write_text(s[:line_start] + block + s[line_start:])
   ```
   Then add the import with edit_file and run `uv run ruff format src/vibey/bootstrap.py`.
4. **If `src/vibey/infrastructure/surface_lanes/direct_factory.py` exists** (ADR-0047 lane S14
   moved the selection there), run the same script against that file instead, reading the
   timeout from the `VibeyConfig` it receives, and change `bootstrap.py` only if it still
   constructs an adapter.
5. Nothing else changes: which adapter each surface gets, and every in-memory fallback.

## Where to change
- `src/vibey/bootstrap.py` (or `direct_factory.py`, behaviour 4).
- New `tests/test_bootstrap_surface_timeouts.py` (provenance line first, copied from
  `tests/test_bootstrap.py:1`).

## Acceptance criteria
- [ ] With `[surfaces] adapter_timeout_seconds = 7` and all twelve surfaces configured, every
      real adapter on `AppResources` has `_timeout == 7` (the existing test precedent is
      `tests/infrastructure/engines/test_ollama_chat.py:82`, `client._timeout == 120`).
- [ ] Without `[surfaces]`, every one has `_timeout == DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS`,
      Redis included (its bound moves from 5 s to the declared 10 s; say so in the commit body).
- [ ] With no `vibey.toml`, `VIBEY_SURFACES_ADAPTER_TIMEOUT_SECONDS=9` and the four
      `VIBEY_TRACKER_*` variables set, `resources.tracker._timeout == 9`.
- [ ] `grep -c "timeout=adapter_timeout" src/vibey/bootstrap.py` prints `12` (or the same count
      in `direct_factory.py`, behaviour 4).
- [ ] `test_build_app_defaults_to_in_memory_surfaces` and
      `test_build_app_wires_concrete_adapters_from_config` pass unchanged.

## Tests to write first (TDD)
`tests/test_bootstrap_surface_timeouts.py`. Open the app with `tests/fakes/app.py`'s
`InMemoryApp` (lane `fakes-bootstrap-seam`; read its constructor, which takes the `config`), as
`async with app.open_app() as resources:`. No PostgreSQL, no `patch`, no `MagicMock`.
- `test_build_app_hands_the_declared_timeout_to_every_real_adapter`: the `VibeyConfig` of
  `tests/infrastructure/test_sovereign_surfaces.py:684-699` plus
  `surfaces=SurfacesConfig(adapter_timeout_seconds=7)`; asserts `_timeout == 7` on
  `resources.tracker`, `.docs`, `.secrets`, `.files`, `.email`, `.sms`, `.messaging`,
  `.config_store`, `.cache`, `.bus`, `.blob` and `.siem`.
- `test_build_app_defaults_every_real_adapter_to_the_surface_timeout`: the same config without
  `surfaces`; all twelve equal `DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS`.
- `test_the_environment_declares_the_adapter_timeout`: `monkeypatch.chdir(tmp_path)`,
  `monkeypatch.setenv` for `VIBEY_SURFACES_ADAPTER_TIMEOUT_SECONDS=9` and
  `VIBEY_TRACKER_URL`, `_TOKEN`, `_WORKSPACE_SLUG`, `_PROJECT_ID`; the app with no config;
  `resources.tracker._timeout == 9`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/test_bootstrap_surface_timeouts.py tests/test_bootstrap.py tests/infrastructure/test_sovereign_surfaces.py tests/fakes
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- The adapters themselves (`gap-surface-timeouts-2` to `-5`) and the key (`-1`).
- ADR-0047's lane transport and its own windows (`read_timeout_seconds`,
  `operation_timeout_seconds`); the lane host builds adapters through the same selection code.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(surfaces): wire the declared adapter timeout into build_app`. Do not push.

## Lane card
- **Depends on:** `gap-surface-timeouts-2`, `gap-surface-timeouts-3`, `gap-surface-timeouts-4`,
  `gap-surface-timeouts-5`, `surfaces-env`, `fakes-bootstrap-seam`.
- **Shares a file with:** `src/vibey/bootstrap.py` (`surfaces-env`, `fakes-bootstrap-seam`,
  the `orm-*` bootstrap lanes, R17, `gap-surface-notify-wiring`, ADR-0047 S14/S26). The script
  anchors on text so it survives their moves; if an `assert` fails, read the file, report the
  anchor that moved, and stop.
- **Must keep passing unchanged:** the two `build_app` wiring tests and the protected tests
  (`tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
