## Title
fix(surfaces): the Plane, BookStack, OpenBao and Infisical adapters bound every call with a timeout

## Why
Doctrine 10 (`src/vibey_tools/gh/docs/doctrines.md:366-369`) says a dependency is never
assumed and always self-healed around. These four adapters call their opener with no timeout,
so a server that accepts the connection and never answers blocks the calling thread forever
(gap K3; ADR-0047 `specs/ADR-surface-lanes.md:562` names this "a follow-up defect fix"):
- `src/vibey/infrastructure/tracker/plane.py:61`, `:77`
- `src/vibey/infrastructure/docs/bookstack.py:53`, `:73`
- `src/vibey/infrastructure/secrets/openbao.py:47`, `:70`
- `src/vibey/infrastructure/config_store/infisical.py:54`, `:81`

(anchors at integration `d3b4a388`). The opener seam already carries the bound:
`UrlOpener.__call__(request, timeout: float | None = None)` (`fakes-http-transport`), and
`InMemoryHttpServer` records it as `RecordedRequest.timeout`. The default comes from
`DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS` (`gap-surface-timeouts-1`, 12.c).

## Required behaviour
For each of the four adapter classes — `PlaneTrackerAdapter`, `BookStackDocsAdapter`,
`OpenBaoSecretsAdapter`, `InfisicalConfigStoreAdapter`:
1. Import `DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS` from `vibey.domain.config`.
2. `__init__` gains the keyword-only parameter
   `timeout: float = DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS`, placed directly after `opener`,
   and stores it as `self._timeout = timeout`.
3. Every call of the opener passes it: `self._opener(req)` becomes
   `self._opener(req, timeout=self._timeout)`. Afterwards
   `grep -n "self._opener(req)" <file>` prints nothing for each of the four files.
4. Nothing else changes: URLs, headers, bodies, the `HTTPError` handling and every message.
   A call that exceeds the bound raises what `urlopen` raises (`TimeoutError`, or
   `urllib.error.URLError` whose `reason` is a `TimeoutError`); the adapter does not catch it.
5. The interface files (`tracker/interfaces/plane_interface.py` and its siblings) do not change:
   they declare the port's methods, not the constructor.

If lane `sovereign-surfaces-ports` renamed one of these modules or classes, apply the same edits
to the module that replaced it, and name it in the commit body.

## Where to change
- `src/vibey/infrastructure/tracker/plane.py`
- `src/vibey/infrastructure/docs/bookstack.py`
- `src/vibey/infrastructure/secrets/openbao.py`
- `src/vibey/infrastructure/config_store/infisical.py`
- New `tests/infrastructure/test_surface_timeouts_records.py` (provenance line first, copied
  from `tests/infrastructure/test_sovereign_surfaces.py:1`).
- Use edit_file for each change. Then run `uv run ruff format` on the five files (OpenBao's
  one-line constructor signature will wrap).

## Acceptance criteria
- [ ] Each adapter built with `timeout=7` passes `timeout=7` on every request it sends
      (`[r.timeout for r in server.requests]` is all 7).
- [ ] Each adapter built without `timeout` passes `DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS`.
- [ ] `grep -n "self._opener(req)" src/vibey/infrastructure/{tracker/plane,docs/bookstack,secrets/openbao,config_store/infisical}.py` prints nothing.
- [ ] Every existing test in `tests/infrastructure/test_sovereign_surfaces.py` passes unchanged.
- [ ] 100% branch coverage of `src/vibey/infrastructure/`; bandit clean.

## Tests to write first (TDD)
`tests/infrastructure/test_surface_timeouts_records.py`, using
`from tests.fakes.http import InMemoryHttpServer` and `route_prefix` (the paths themselves are
pinned by `fakes-sovereign-http`'s tests; these tests pin the bound). No `MagicMock`, no patching.
A route written ``METHOD URL → BODY`` means `server.route_prefix("METHOD", "URL", body=BODY)`;
where only the method is given, the URL is the adapter's base URL plus `/`.
- `test_plane_bounds_every_call_with_its_timeout`:
  `PlaneTrackerAdapter(url="https://plane.test", token="t", workspace_slug="ws", project_id="p1", opener=server, timeout=7)`;
  routes `POST https://plane.test/` → body `{"id": "t-1"}` and `GET https://plane.test/` →
  `{"state": "Todo"}`; `create_ticket("a", "b")` then `get_ticket_status("t-1")`; timeouts `[7, 7]`.
- `test_plane_defaults_to_the_surface_timeout`: no `timeout`; one `create_ticket`;
  `server.requests[0].timeout == DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS`.
- `test_bookstack_bounds_every_call_with_its_timeout`:
  `BookStackDocsAdapter(url="https://docs.test", token_id="i", token_secret="s", opener=server, timeout=7)`;
  `POST` → `{"id": 5}`, `PUT` → `{}`; `create_page("T", "<p>x</p>")`, `update_page("5", "<p>y</p>")`; `[7, 7]`.
- `test_bookstack_defaults_to_the_surface_timeout`.
- `test_openbao_bounds_every_call_with_its_timeout`:
  `OpenBaoSecretsAdapter(url="https://bao.test", token="t", opener=server, timeout=7)`;
  `PUT` → `{}`, `GET` → `{"data": {"data": {"value": "v"}}}`; `set_secret("k", "v")`,
  `get_secret("k") == "v"`; `[7, 7]`.
- `test_openbao_defaults_to_the_surface_timeout`.
- `test_infisical_bounds_every_call_with_its_timeout`:
  `InfisicalConfigStoreAdapter(url="https://inf.test", token="t", project_id="p", opener=server, timeout=7)`;
  `POST` → `{}`, `GET` → `{"secret": {"secretValue": "v"}}`; `create_config("k", "v")`,
  `get_config("k") == "v"`; `[7, 7]`.
- `test_infisical_defaults_to_the_surface_timeout`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_surface_timeouts_records.py tests/infrastructure/test_sovereign_surfaces.py tests/fakes
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The other adapters (`gap-surface-timeouts-3`, `-4`, `-5`) and the `build_app` wiring (`-6`).
- Retrying, or a typed transient error for timeouts and HTTP 5xx (ADR-0047
  `specs/ADR-surface-lanes.md:563`; not this lane).
- Connection reuse (keep-alive). ADR-0047 lane S13 covers the Redis connection only.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `fix(surfaces): bound the Plane, BookStack, OpenBao and Infisical calls`. Do not push.

## Lane card
- **Depends on:** `gap-surface-timeouts-1`, `fakes-sovereign-http`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** `tests/infrastructure/test_sovereign_surfaces.py` and the
  protected tests (`tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
