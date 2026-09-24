## Title
fix(surfaces): the Nextcloud, Garage and RabbitMQ-management adapters bound every call with a timeout

## Why
Doctrine 10 (`src/vibey_tools/gh/docs/doctrines.md:366-369`): never assumed, always self-healed
around. These three adapters call their opener with no timeout (gap K3; ADR-0047
`specs/ADR-surface-lanes.md:562`), so a server that accepts the connection and never answers
blocks the calling thread forever. Anchors at integration `d3b4a388`:
- `src/vibey/infrastructure/files/nextcloud.py:47`, `:61` (upload, download);
- `src/vibey/infrastructure/blob/garage.py:112` (`_send`, used by every put and get);
- `src/vibey/infrastructure/bus/rabbitmq.py:50` (`_request`, used by every operation). The bus
  is exempt from 8.f's lanes (ADR-0047 §11), but its diagnostics adapter still must not hang.

The opener seam already carries the bound (`UrlOpener.__call__(request, timeout=None)`,
`fakes-http-transport`), and `InMemoryHttpServer` records it. The default is
`DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS` (`gap-surface-timeouts-1`, 12.c).

## Required behaviour
For each of `NextcloudFilesAdapter`, `GarageBlobAdapter` and `RabbitMqBusAdapter`:
1. Import `DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS` from `vibey.domain.config`.
2. `__init__` gains the keyword-only parameter
   `timeout: float = DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS`, directly after `opener`, stored
   as `self._timeout = timeout`.
3. Every opener call passes it: `self._opener(req)` becomes
   `self._opener(req, timeout=self._timeout)`. Afterwards `grep -n "self._opener(req)"` prints
   nothing for the three files.
4. Nothing else changes: URLs, signing (Garage's SigV4 is computed before the call and does not
   involve the timeout), headers, bodies, error handling and messages. A call that exceeds the
   bound raises what `urlopen` raises; the adapter does not catch it.
5. The interface files do not change (they declare methods, not constructors).

If lane `sovereign-surfaces-ports` renamed one of these modules or classes, apply the same edits
to its replacement and name it in the commit body.

## Where to change
- `src/vibey/infrastructure/files/nextcloud.py`
- `src/vibey/infrastructure/blob/garage.py`
- `src/vibey/infrastructure/bus/rabbitmq.py`
- New `tests/infrastructure/test_surface_timeouts_transfers.py` (provenance line first, copied
  from `tests/infrastructure/test_sovereign_surfaces.py:1`).
- Use edit_file for each change, then `uv run ruff format` on the four files.

## Acceptance criteria
- [ ] Each adapter built with `timeout=7` passes 7 on every request it sends.
- [ ] Each adapter built without `timeout` passes `DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS`.
- [ ] `grep -n "self._opener(req)" src/vibey/infrastructure/{files/nextcloud,blob/garage,bus/rabbitmq}.py` prints nothing.
- [ ] Every existing test in `tests/infrastructure/test_sovereign_surfaces.py` passes unchanged.
- [ ] 100% branch coverage of `src/vibey/infrastructure/`; bandit clean.

## Tests to write first (TDD)
`tests/infrastructure/test_surface_timeouts_transfers.py`, with
`from tests.fakes.http import InMemoryHttpServer`. A route written ``METHOD → BODY`` means
`server.route_prefix("METHOD", "<the adapter's base URL>/", body=BODY)`. No `MagicMock`, no patching.
- `test_nextcloud_bounds_every_call_with_its_timeout`:
  `NextcloudFilesAdapter(url="https://cloud.test", user="alice", password="pw", opener=server, timeout=7)`;
  `PUT → b""`, `GET → b"hello"`; `upload_file("a.txt", b"hi")`, then
  `download_file("a.txt") == b"hello"`; `[r.timeout for r in server.requests] == [7, 7]`.
- `test_nextcloud_defaults_to_the_surface_timeout`: no `timeout`; one upload;
  `server.requests[0].timeout == DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS`.
- `test_garage_bounds_every_call_with_its_timeout`:
  `GarageBlobAdapter(url="https://garage.test", access_key="a", secret_key="s", opener=server, timeout=7)`;
  `PUT → b""`, `GET → b"data"`; `put_blob("bucket", "key", b"x")` (two requests: bucket, then
  object), then `get_blob("bucket", "key") == b"data"`; three requests, all 7.
- `test_garage_defaults_to_the_surface_timeout`: one `get_blob`.
- `test_rabbitmq_bounds_every_call_with_its_timeout`:
  `RabbitMqBusAdapter(url="https://mq.test", username="u", password="p", opener=server, timeout=7)`;
  `PUT → ""`, `POST → "[]"`; `declare_queue("q")` (four requests) then `consume("q") is None`
  (one request); five requests, all 7.
- `test_rabbitmq_defaults_to_the_surface_timeout`: one `consume("q")`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_surface_timeouts_transfers.py tests/infrastructure/test_sovereign_surfaces.py tests/fakes
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The other adapters (`gap-surface-timeouts-2`, `-4`, `-5`) and the `build_app` wiring (`-6`).
- Retrying, a typed transient error (`specs/ADR-surface-lanes.md:563`), connection reuse, and
  ADR-0047's `inline_max_bytes` payload bound.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `fix(surfaces): bound the Nextcloud, Garage and RabbitMQ-management calls`. Do not push.

## Lane card
- **Depends on:** `gap-surface-timeouts-1`, `fakes-sovereign-http` (which follows
  `fakes-http-transport`, the lane that retyped the Garage and RabbitMQ openers).
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** `tests/infrastructure/test_sovereign_surfaces.py` and the
  protected tests (`tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
