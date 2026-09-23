## Title
feat(tracker): a declared-only Jira adapter on `IssueTrackerPort`, built but never selected by default

## Why
Issue #85 (rewrite: `issue-audit/updates/85.md`, Scope 2 "**Jira**: a declared relay adapter on
`IssueTrackerPort`. Plane stays the source of truth (8.b)", "Proposed child issues" 2). Sub-doctrine
8.b (`src/vibey_tools/gh/docs/doctrines.md:140-142`) makes ticketing default to self-hosted Plane,
with Jira declared-only; `:168-177` realises every surface as one vibey-owned protocol with one
adapter per platform; `:179-186` says a declared paid platform "relays through the sovereign host
rather than replacing it". Today the tracker surface has only the sovereign adapter and the fake:
`src/vibey/infrastructure/tracker/{plane.py,in_memory.py}` (port:
`src/vibey/application/interfaces/tracker.py:8-18`, `create_ticket` and `get_ticket_status`), and
`build_app` selects Plane when `[tracker]` is complete (`src/vibey/bootstrap.py:753-760`).

This lane builds **only the adapter**, so a later relay lane has a tested Jira client to wire. It
is not wired into `build_app` and cannot become a default: how a declared paid tracker feeds Plane
(the relay) is the gaps.md §C3 lane, and the set of declared-only adapters is gaps.md §C4. Jira's
REST API version 2 paths serve both Jira Cloud and Jira Data Center, so no Cloud-vs-DC choice is
made here; the authentication scheme is declared by the caller (12.c).

## Required behaviour
1. New `src/vibey/infrastructure/tracker/jira.py`, class `JiraTrackerAdapter(JiraTrackerAdapterInterface)`:
   - `__init__(self, *, base_url: str, project_key: str, token: str, auth_scheme: str, username: str | None = None, issue_type: str = "Task", timeout_seconds: float = 30.0, opener: UrlOpener = urllib.request.urlopen) -> None`.
     `auth_scheme` must be `"basic"` or `"bearer"`, else
     `ValueError("jira auth_scheme must be 'basic' (email and API token) or 'bearer' (personal access token)")`;
     `"basic"` requires a non-empty `username`, else
     `ValueError("jira basic auth needs the account email as username")`; `timeout_seconds` must be
     `> 0`, else `ValueError("jira timeout_seconds must be positive")`; `base_url` is stored
     `rstrip("/")` and must start with `https://` or `http://`, else
     `ValueError(f"jira base_url must be an http(s) URL: {base_url!r}")`.
   - `_headers()`: `Accept: application/json`, `Content-Type: application/json`, and
     `Authorization: Basic <base64(username:token)>` or `Authorization: Bearer <token>`.
   - `async create_ticket(title, description) -> str` via `asyncio.to_thread` (copy
     `plane.py:47-65`'s shape): `POST {base_url}/rest/api/2/issue` with body
     `{"fields": {"project": {"key": project_key}, "summary": title, "description": description, "issuetype": {"name": issue_type}}}`;
     returns the response's `"key"` as `str`. HTTP errors raise
     `RuntimeError(f"Jira API error {exc.code}: {exc.reason}")`; an answer without `"key"` raises
     `RuntimeError("Jira created an issue but returned no key")`.
   - `async get_ticket_status(ticket_id) -> str`: `GET {base_url}/rest/api/2/issue/{quote(ticket_id, safe='')}?fields=status`;
     returns `fields.status.name`, or `"unknown"` when absent. A 404 raises
     `KeyError(f"ticket {ticket_id!r} not found")`; any other HTTP error raises the `RuntimeError` above.
   - Every request passes `timeout=self._timeout_seconds` to the opener (the gaps.md §K3 rule,
     from day one). A `urllib.error.URLError` raises
     `RuntimeError(f"Jira unreachable: {exc.reason}")`.
   - The module docstring says: declared-only under 8.b, never selected by `build_app`, and that the
     relay through Plane is the gaps.md §C3 lane.
2. New `src/vibey/infrastructure/tracker/interfaces/jira_interface.py`:
   `JiraTrackerAdapterInterface(IssueTrackerPort, Protocol)`, `runtime_checkable`, copied from
   `tracker/interfaces/plane_interface.py:1-15`.
3. `UrlOpener` is `vibey.infrastructure.interfaces.UrlOpener` (lane `fakes-http-transport`); use the
   same constructor form `fakes-sovereign-http` gives `plane.py`.
4. No change to `bootstrap.py`, `domain/config.py` or `TrackerConfig`: nothing selects the adapter.

## Where to change
- New: `src/vibey/infrastructure/tracker/jira.py`,
  `src/vibey/infrastructure/tracker/interfaces/jira_interface.py` (provenance header copied from
  `tracker/plane.py:1`).
- New test file `tests/infrastructure/test_jira_tracker.py`.

## Acceptance criteria
- [ ] `isinstance(JiraTrackerAdapter(...), JiraTrackerAdapterInterface)` and `isinstance(..., IssueTrackerPort)`.
- [ ] The create request is exactly `POST https://jira.example/rest/api/2/issue` with the body above
      and the declared auth header, for both schemes.
- [ ] The status read is `GET …/rest/api/2/issue/PRJ-7?fields=status`; 404 → `KeyError`; 500 → `RuntimeError`;
      unreachable → `RuntimeError`.
- [ ] Every recorded request carries `timeout == 30.0` by default and the configured value otherwise.
- [ ] `grep -n "JiraTrackerAdapter" src/vibey/bootstrap.py` finds nothing.
- [ ] 100% branch coverage of `src/vibey/infrastructure/`; bandit clean (keep the
      `# nosec B310` comment form `plane.py:51` uses).

## Tests to write first (TDD)
`tests/infrastructure/test_jira_tracker.py`, using `InMemoryHttpServer` from `tests/fakes/http.py`
(lane `fakes-http-transport`) — no `MagicMock`:
- `test_jira_creates_an_issue_with_basic_auth` — route `POST https://jira.example/rest/api/2/issue`
  with body `{"id": "10001", "key": "PRJ-7"}`; assert the returned key, the method, URL,
  `authorization == "Basic " + base64("me@example.org:tok")`, and `server.json(0)`.
- `test_jira_creates_an_issue_with_a_bearer_token`
- `test_jira_reads_a_status_name` — `{"fields": {"status": {"name": "In Progress"}}}` → `"In Progress"`;
  `{"fields": {}}` → `"unknown"`.
- `test_jira_maps_errors` — 404 → `KeyError`; 500 → `RuntimeError("Jira API error 500 …")`;
  `unreachable(...)` → `RuntimeError("Jira unreachable …")`; a create answer without `key` → `RuntimeError`.
- `test_jira_bounds_every_call_with_the_configured_timeout`
- `test_jira_rejects_an_unusable_declaration` — the four `ValueError`s of Required behaviour 1.
- `test_jira_is_never_selected_by_build_app` — `inspect.getsource(vibey.bootstrap)` does not contain
  `"JiraTrackerAdapter"`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey/infrastructure/tracker
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_jira_tracker.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Wiring, config (`[tracker] relay`), and the Plane↔Jira relay (gaps.md §C3/§C4 lanes).
- Other paid trackers (Linear, Asana); ADR-0047's surface catalogue (the adapter adds no operation).
- Docs, runbook 01's status note (docs wave), CHANGELOG. Do not push; commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
