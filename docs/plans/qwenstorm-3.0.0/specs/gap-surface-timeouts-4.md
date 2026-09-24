## Title
fix(surfaces): the Matrix, Wazuh and Kannel send adapters bound every call with a timeout

## Why
Doctrine 10 (`src/vibey_tools/gh/docs/doctrines.md:366-369`): never assumed, always self-healed
around. The three one-way send adapters call their opener with no timeout (gap K3; ADR-0047
`specs/ADR-surface-lanes.md:562`). Anchors at integration `d3b4a388`:
- `src/vibey/infrastructure/messaging/matrix.py:44`
- `src/vibey/infrastructure/siem/wazuh.py:51`
- `src/vibey/infrastructure/sms/kannel.py:55`

A hung send is worse than a failed one: the SIEM port promises "a sink that is down must not
fail the work that produced the event" (`src/vibey/application/interfaces/siem.py:12-13`), and a
thread blocked forever on the sink does exactly that. The opener seam carries the bound
(`UrlOpener.__call__(request, timeout=None)`, `fakes-http-transport`); the default is
`DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS` (`gap-surface-timeouts-1`, 12.c).

## Required behaviour
For each of `MatrixMessagingAdapter`, `WazuhSiemAdapter` and `KannelSmsAdapter`:
1. Import `DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS` from `vibey.domain.config`.
2. `__init__` gains the keyword-only parameter
   `timeout: float = DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS`, directly after `opener`, stored
   as `self._timeout = timeout`.
3. The opener call passes it: `self._opener(req)` becomes
   `self._opener(req, timeout=self._timeout)`; `grep -n "self._opener(req)"` prints nothing for
   the three files.
4. Nothing else changes: the Matrix transaction id (`matrix.py:29-33`), the Wazuh document, the
   Kannel query and its `0:` check, error handling and messages. A call that exceeds the bound
   raises what `urlopen` raises; the adapter does not catch it.
5. The interface files do not change.

If lane `sovereign-surfaces-ports` renamed one of these modules or classes (the operator's tree
has had `sms/fossify.py`), apply the same edits to its replacement and name it in the commit body.

## Where to change
- `src/vibey/infrastructure/messaging/matrix.py`
- `src/vibey/infrastructure/siem/wazuh.py`
- `src/vibey/infrastructure/sms/kannel.py`
- New `tests/infrastructure/test_surface_timeouts_sends.py` (provenance line first, copied
  from `tests/infrastructure/test_sovereign_surfaces.py:1`).
- Use edit_file for each change, then `uv run ruff format` on the four files (Matrix's one-line
  constructor signature will wrap).

## Acceptance criteria
- [ ] Each adapter built with `timeout=7` passes 7 on every request it sends.
- [ ] Each adapter built without `timeout` passes `DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS`.
- [ ] `grep -n "self._opener(req)" src/vibey/infrastructure/{messaging/matrix,siem/wazuh,sms/kannel}.py` prints nothing.
- [ ] Every existing test in `tests/infrastructure/test_sovereign_surfaces.py` passes unchanged.
- [ ] 100% branch coverage of `src/vibey/infrastructure/`; bandit clean.

## Tests to write first (TDD)
`tests/infrastructure/test_surface_timeouts_sends.py`, with
`from tests.fakes.http import InMemoryHttpServer`. A route written ``METHOD → BODY`` means
`server.route_prefix("METHOD", "<the adapter's base URL>/", body=BODY)`. No `MagicMock`, no patching.
- `test_matrix_bounds_every_send_with_its_timeout`:
  `MatrixMessagingAdapter(url="https://matrix.test", token="t", opener=server, timeout=7)`;
  `PUT → {}`; two `send_message("!ops:matrix.test", "hi")` calls; timeouts `[7, 7]`.
- `test_matrix_defaults_to_the_surface_timeout`: no `timeout`; one send;
  `server.requests[0].timeout == DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS`.
- `test_wazuh_bounds_every_send_with_its_timeout`:
  `WazuhSiemAdapter(url="https://wazuh.test", opener=server, timeout=7)`; `POST → {}`;
  `send_event("vibey-audit", {"action": "x"})`; timeouts `[7]`.
- `test_wazuh_defaults_to_the_surface_timeout`.
- `test_kannel_bounds_every_send_with_its_timeout`:
  `KannelSmsAdapter(url="https://kannel.test", username="u", password="p", opener=server, timeout=7)`;
  `GET → "0: Accepted for delivery"`; `send_sms("+15551234567", "hi")`; timeouts `[7]`.
- `test_kannel_defaults_to_the_surface_timeout`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_surface_timeouts_sends.py tests/infrastructure/test_sovereign_surfaces.py tests/fakes
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The other adapters (`gap-surface-timeouts-2`, `-3`, `-5`) and the `build_app` wiring (`-6`).
- ADR-0047's `idempotency_key` on sends (lanes S04–S06), retries and a typed transient error
  (`specs/ADR-surface-lanes.md:563`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `fix(surfaces): bound the Matrix, Wazuh and Kannel sends`. Do not push.

## Lane card
- **Depends on:** `gap-surface-timeouts-1`, `fakes-sovereign-http`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** `tests/infrastructure/test_sovereign_surfaces.py` and the
  protected tests (`tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
