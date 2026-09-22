## Title
feat(explorer): a polite fetcher — robots.txt per RFC 9309, a per-host token bucket, and an identified user agent on every request

## Why
Issue #87 (rewrite: `issue-audit/updates/87.md`, Scope 1 "A polite fetcher (robots.txt, per-host rate
limits, an identified user agent) covers the rest", "Proposed child issues" 4). The operator's
original constraint: "Scraping is polite: robots.txt, rate limits, identified user agent. This bot
represents the project publicly." SD-01 §1 (carried in CLAUDE.md): reach people only through
published, official channels, and gather no private details; §4: fetched text is data. Sub-doctrine
10.e (`src/vibey_tools/gh/docs/doctrines.md:417`): the standard library's `urllib.robotparser` is
used, not a third-party crawler; the explorer stays stdlib-only (`roadmap-87-explorer-skeleton-p1`).
12.c (`doctrines.md:455`): rates and the user agent are declared by the caller, never constants.

## Required behaviour
All in `src/vibey_tools/explorer/vibey_explorer/fetcher.py`, with every class's contract in
`vibey_explorer/interfaces/fetcher_interface.py` (stdlib imports only).
1. Seams (Protocols in the interface module): `OpenerInterface.__call__(request: urllib.request.Request, timeout: float) -> Any`
   (what `urllib.request.urlopen` satisfies: a context manager with `.status`/`.getcode()` and
   `.read()`, raising `urllib.error.HTTPError`/`URLError`); `ClockInterface.monotonic() -> float`;
   `SleeperInterface.sleep(seconds: float) -> None`.
2. `class SystemClock` (implements both clock and sleeper with `time.monotonic` / `time.sleep`).
3. `@dataclass(frozen=True, slots=True) class FetchPolicy`: `user_agent: str`,
   `requests_per_minute: float`, `burst: int`, `timeout_seconds: float`. No defaults. Validation:
   `user_agent` non-empty with no control characters (`"fetch policy user_agent must identify the fetcher"`);
   `requests_per_minute > 0` (`"fetch policy requests_per_minute must be positive"`);
   `burst >= 1` (`"fetch policy burst must be at least 1"`); `timeout_seconds > 0`
   (`"fetch policy timeout_seconds must be positive"`).
4. `class TokenBucket`: `__init__(self, *, rate_per_second: float, capacity: int, clock: ClockInterface)`,
   starts full; `wait_seconds(self) -> float` (0.0 when a token is available, else the time until
   one is); `take(self) -> None` (removes a token; raises `RuntimeError("no token available")` if
   none). Refill is continuous: `tokens = min(capacity, tokens + elapsed * rate)`.
5. `@dataclass(frozen=True, slots=True) class FetchResult`: `url: str`, `allowed: bool`,
   `status: int | None`, `body: bytes`, `reason: str`.
6. `class PoliteFetcher`: `__init__(self, policy: FetchPolicy, *, opener: OpenerInterface = urllib.request.urlopen, clock: ClockInterface | None = None, sleeper: SleeperInterface | None = None)`
   (defaults: one `SystemClock()` for both).
   - One `TokenBucket` per host (`urlsplit(url).netloc.lower()`), rate `requests_per_minute / 60`,
     capacity `burst`. The robots.txt request and the page request **both** take a token.
   - Before each request: `wait = bucket.wait_seconds()`; if `wait > 0`, `sleeper.sleep(wait)`; then `take()`.
   - Every request carries `User-Agent: <policy.user_agent>` and uses `timeout=policy.timeout_seconds`.
   - robots.txt is fetched once per host (`<scheme>://<netloc>/robots.txt`) and cached. Per RFC 9309:
     2xx → parse with `urllib.robotparser.RobotFileParser.parse(body.decode("utf-8", "replace").splitlines())`;
     any 4xx → everything allowed; 5xx or unreachable (`URLError`, `OSError`, timeout) → everything
     disallowed for that host until a later fetcher is constructed.
   - `fetch(self, url: str) -> FetchResult`: a non-http(s) URL → `FetchResult(url, False, None, b"", "only http and https are fetched")`;
     disallowed by robots → `FetchResult(url, False, None, b"", "robots.txt disallows this path")`
     with **no** page request made; otherwise the page: 2xx → `(url, True, status, body, "")`;
     `HTTPError` → `(url, True, code, b"", f"HTTP {code}")`; `URLError`/`OSError` →
     `(url, True, None, b"", f"unreachable: {reason}")`. `can_fetch` is asked with the policy's
     user agent.
7. Module docstring: the three courtesies, RFC 9309's rules, and that nothing here stores personal
   data (SD-01 §1).

## Where to change
- New: `vibey_explorer/fetcher.py`, `vibey_explorer/interfaces/fetcher_interface.py` (provenance header).
- New test file `src/vibey_tools/explorer/test/test_fetcher.py`.

## Acceptance criteria
- [ ] Against a loopback `http.server.ThreadingHTTPServer` the test starts on `127.0.0.1:0`
      (allowed in the default tier): a disallowed path is never requested (the server's log shows
      only `/robots.txt`); an allowed path is fetched with the declared `User-Agent`.
- [ ] Robots 404 → allowed; robots 503 → the whole host disallowed.
- [ ] With a fake clock and a recording sleeper, `burst=2`, `requests_per_minute=60`: the third
      request within one second sleeps `1.0` second; after the clock advances 1 s no sleep occurs.
- [ ] 100% branch coverage of the tenant; mypy clean; stdlib only.

## Tests to write first (TDD)
`src/vibey_tools/explorer/test/test_fetcher.py`:
- `test_every_request_identifies_the_fetcher` (loopback server records headers)
- `test_a_path_robots_disallows_is_never_requested`
- `test_robots_4xx_allows_and_5xx_disallows_the_host` (and an unreachable host → disallowed)
- `test_the_bucket_makes_the_caller_wait_per_host` (fake clock + recording sleeper; two hosts do not share a bucket)
- `test_robots_is_fetched_once_per_host`
- `test_non_http_urls_are_refused`
- `test_http_errors_and_unreachable_pages_are_reported_not_raised`
- `test_an_unusable_policy_is_refused` (the four messages)
- `test_the_fetcher_and_bucket_satisfy_their_interfaces`

## Checks the lane must run (all must pass)
    cd src/vibey_tools/explorer && python -m pytest -q && python -m mypy
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- Which sites are fetched (discovery sources are blocked on #87 open question 2) and daily PR caps
  (blocked on #87 open question 3). Any parsing of fetched pages. Docs, CHANGELOG. Do not push;
  commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
