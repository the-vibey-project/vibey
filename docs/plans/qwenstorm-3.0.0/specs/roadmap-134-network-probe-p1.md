## Title
feat(gh): an endpoint connector — one TCP or HTTP(S) attempt, timed, behind a declared seam with a scripted fake

## Why
Issue #134 (rewrite: `issue-audit/updates/134.md`, Scope 1 *network*: "reachability, latency and
loss to each required endpoint (declared per stage in `[estimate]`)"; "Proposed child issues" 3: "A
TCP/HTTP reachability, latency and loss sample, behind the offline switch. Tests with a fake
connector"). The network material has no reader anywhere in vibey-gh: `MEASURED_BY` names what
would measure it (`src/vibey_tools/gh/vibey_gh/feasibility.py:94-96`) and nothing does. The
network probe (`roadmap-134-network-probe-p2`) needs one I/O primitive — "attempt this endpoint once
and say how long it took, or that it was lost" — and sub-doctrine 9.b
(`src/vibey_tools/gh/docs/doctrines.md:349`) puts that primitive behind a declared seam with an
in-memory fake, so the probe's arithmetic is tested without a socket. This lane is that seam, its
stdlib implementation (`socket`, `http.client`; vibey-gh stays `dependencies = []`,
`src/vibey_tools/gh/pyproject.toml:30`) and its fake. Sub-doctrine 8.h (`doctrines.md:326-333`): the
stdlib calls used behave the same on Arch Linux and macOS, and the tests run on both.

Every path below is relative to `src/vibey_tools/gh/` unless it starts with `src/`.

## Required behaviour
1. **New module `vibey_gh/endpoint_connector.py`** (provenance line 1 from
   `vibey_gh/fit.py:1`), module docstring: "One attempt at one declared endpoint, timed (#134).
   `tcp://host:port` opens a TCP connection; `http://` and `https://` send a `HEAD` and count any
   HTTP status as an answer, because reachability asks whether the endpoint answers, not whether
   it approves. An attempt that fails for any reason is lost: `None`, never a raise." It holds:
   - `@dataclass(frozen=True) class Endpoint:` fields `scheme: str`, `host: str`, `port: int`,
     `path: str`.
   - `class EndpointConnector(EndpointConnectorInterface)`:
     - `__init__(self, *, clock: Callable[[], float] | None = None) -> None`:
       `self._clock = clock or time.monotonic`.
     - `@staticmethod parse(endpoint: str) -> Endpoint | None`, exactly:
       ```python
               try:
                   parts = urlsplit(endpoint)
                   port = parts.port
               except ValueError:
                   return None
               scheme = parts.scheme.lower()
               host = parts.hostname or ""
               if scheme not in ("tcp", "http", "https") or not host:
                   return None
               if port is None:
                   if scheme == "tcp":
                       return None
                   port = 443 if scheme == "https" else 80
               if port < 1:
                   return None
               path = parts.path or "/"
               if parts.query:
                   path = f"{path}?{parts.query}"
               return Endpoint(scheme, host, port, path)
       ```
     - `attempt(self, endpoint: str, *, timeout_s: float) -> float | None`, exactly:
       ```python
               target = self.parse(endpoint)
               if target is None:
                   return None
               start = self._clock()
               try:
                   if target.scheme == "tcp":
                       with socket.create_connection((target.host, target.port), timeout=timeout_s):
                           pass
                   else:
                       factory: type[http.client.HTTPConnection] = (
                           http.client.HTTPSConnection
                           if target.scheme == "https"
                           else http.client.HTTPConnection
                       )
                       connection = factory(target.host, target.port, timeout=timeout_s)
                       try:
                           connection.request("HEAD", target.path)
                           connection.getresponse().close()
                       finally:
                           connection.close()
               except (OSError, http.client.HTTPException):
                   return None
               return round(max(self._clock() - start, 0.0), 6)
       ```
   - Imports: `http.client`, `socket`, `time`, `from collections.abc import Callable`,
     `from dataclasses import dataclass`, `from urllib.parse import urlsplit`, and the interface.
2. **New interface `vibey_gh/interfaces/endpoint_connector_interface.py`** (provenance line from
   `vibey_gh/interfaces/memory_sampler_interface.py:1`): a `runtime_checkable`
   `EndpointConnectorInterface(Protocol)` declaring
   `def attempt(self, endpoint: str, *, timeout_s: float) -> float | None:` with the docstring
   "Seconds one attempt at `endpoint` took to be answered, or `None` when it was lost or is not an
   endpoint at all. Never raises."
3. **Fake** appended to `test/fakes.py`:
   ```python
   class ScriptedEndpointConnector:
       """An endpoint connector that answers from a script and records every attempt as
       `(endpoint, timeout_s)` (#134). Each endpoint's answers are handed out in order and the
       last one repeats; an endpoint with no script is lost, as an unreachable one would be."""

       def __init__(self, answers: Mapping[str, Sequence[float | None]] | None = None) -> None:
           self.answers = {endpoint: list(script) for endpoint, script in (answers or {}).items()}
           self.calls: list[tuple[str, float]] = []

       def attempt(self, endpoint: str, *, timeout_s: float) -> float | None:
           self.calls.append((endpoint, timeout_s))
           script = self.answers.get(endpoint)
           if not script:
               return None
           return script.pop(0) if len(script) > 1 else script[0]
   ```
   Register `EndpointConnectorInterface` → `ScriptedEndpointConnector` in `test/test_port_parity.py`
   the way `ScriptedGitRunner` is registered.

## Where to change
- New: `vibey_gh/endpoint_connector.py`, `vibey_gh/interfaces/endpoint_connector_interface.py`,
  `test/test_endpoint_connector.py`.
- Append to `test/fakes.py` and `test/test_fakes.py`; one entry in `test/test_port_parity.py`.
- Pattern to copy for an injected clock: `OperationEstimator(clock=...)`
  (`vibey_gh/operation_estimate.py:82`, `:104`).

## Acceptance criteria
- [ ] A listening loopback TCP port answers with the clock's elapsed time; a closed one is `None`.
- [ ] An HTTP endpoint that answers `404` is reachable; an HTTPS endpoint whose peer breaks the
      handshake is `None`; an unparsable endpoint is `None` without starting the clock.
- [ ] No test leaves the machine: every socket in the tests is bound to `127.0.0.1` inside the test.
- [ ] The whole vibey-gh suite passes at 100% line+branch; black, isort, mypy, ruff, import-linter clean.

## Tests to write first (TDD)
New `test/test_endpoint_connector.py` (provenance line 1 from `test/test_fit.py:1`). Every server
is a loopback socket opened by the test and closed in a `finally`; nothing reaches another machine:
- `test_the_connector_declares_its_seam` — `isinstance(EndpointConnector(), EndpointConnectorInterface)`.
- `test_endpoints_parse_into_scheme_host_port_and_path` (parametrised) —
  `"tcp://db.example:5432"` → `Endpoint("tcp", "db.example", 5432, "/")`;
  `"https://git.example"` → `Endpoint("https", "git.example", 443, "/")`;
  `"http://127.0.0.1:8080/healthz?deep=1"` → `Endpoint("http", "127.0.0.1", 8080, "/healthz?deep=1")`;
  `"HTTPS://Git.Example/x"` → `Endpoint("https", "git.example", 443, "/x")`.
- `test_what_is_not_an_endpoint_is_refused` (parametrised) — `"tcp://db.example"`,
  `"ftp://host:21"`, `"https://"`, `"db.example:5432"`, `"tcp://host:99999"`, `"tcp://host:0"`
  each parse to `None`.
- `test_a_listening_tcp_port_answers_and_a_closed_one_does_not` — a `socket.socket()` bound to
  `("127.0.0.1", 0)` and listening; `ticks = iter([10.0, 10.25])`;
  `EndpointConnector(clock=lambda: next(ticks)).attempt(f"tcp://127.0.0.1:{port}", timeout_s=2.0) == 0.25`.
  A second socket bound to `("127.0.0.1", 0)` and closed without listening gives its port;
  `EndpointConnector().attempt(f"tcp://127.0.0.1:{closed}", timeout_s=2.0) is None`.
- `test_an_http_endpoint_answers_with_any_status` — `http.server.HTTPServer(("127.0.0.1", 0), Handler)`
  where `Handler(http.server.BaseHTTPRequestHandler)` answers `do_HEAD` with
  `self.send_response(404); self.end_headers()` and silences `log_message`; serve one request on
  a daemon `threading.Thread(target=server.handle_request)`;
  `EndpointConnector().attempt(f"http://127.0.0.1:{port}/healthz", timeout_s=2.0)` is a `float`
  `>= 0`; join the thread, `server.server_close()`.
- `test_an_https_endpoint_that_breaks_the_handshake_is_lost` — a loopback listener whose daemon
  thread `accept()`s one connection and closes it at once;
  `EndpointConnector().attempt(f"https://127.0.0.1:{port}", timeout_s=2.0) is None`.
- `test_an_unparsable_endpoint_is_lost_without_timing_anything` —
  `EndpointConnector(clock=lambda: pytest.fail("no attempt should be timed")).attempt("tcp://nowhere", timeout_s=1.0) is None`.

Append to `test/test_fakes.py`:
- `test_endpoint_connector_fake_answers_in_order_and_repeats_the_last` —
  `ScriptedEndpointConnector({"tcp://a:1": [0.1, None]})` answers `0.1`, `None`, `None` for three
  attempts at `"tcp://a:1"`, `None` for `"tcp://b:2"`, and `calls` lists all four with their
  `timeout_s`.

## Checks the lane must run (all must pass)
    cd src/vibey_tools/gh && (python -c "import vibey_gh" || python -m pip install -e ".[dev]")
    cd src/vibey_tools/gh && python -m pytest -q --no-cov test/test_endpoint_connector.py test/test_fakes.py test/test_port_parity.py
    cd src/vibey_tools/gh && python -m pytest -q      # whole suite: --cov-fail-under=100 --cov-branch (pyproject.toml:66-70)
    cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh
    uv run ruff check . && uv run ruff format --check .
    uv run lint-imports
    git diff --stat   # exactly the files named under "Where to change"

Formatter trap (`specs/forge-adapter.md` C8): black and ruff format both check this tenant; keep
lines at or under 100 columns and restructure any line they disagree on.

## Out of scope
- The network probe, `[estimate.endpoints]` and the wiring (`roadmap-134-network-probe-p2`).
- Which endpoints a stage needs: #134 open question 3 is the operator's; nothing here names one.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the four agent-surface trees.
- Do not push, open PRs or change remotes. Commit locally with the Title as the subject.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
