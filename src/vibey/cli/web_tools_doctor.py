# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey doctor`'s `web-tools` line (ADR-0102, SP-ACP Task 9b): whether the hub serves
`vibey_search` and `vibey_fetch` to the agent principal, and under which budgets.

One line in doctor's `MARK name detail` grammar, added after the `web-search` lines (so `vibey
doctor --json` reads it as one more check and no key changes):

    PASS web-tools                  the hub serves vibey_search and vibey_fetch to the agent ...

- `PASS`: the agent holds `web` (`[hub] agent_scopes`), a hub is running, and its OpenAPI
  document (public, no credential) lists `/api/v1/web/search` and `/web/fetch`.
- `WARN`: the agent is not granted `web`; no hub is running (doctor never starts one); or the
  running hub does not answer, or does not offer the routes (an older vibey still running).
- `FAIL`: a `[hub]` or `[web]` setting the hub would refuse to start with.

The hub this line asks about is the person's own: its state folder and `agent_scopes` come from
their own `vibey.toml` (`bootstrap.acp_user_config`), never from the folder doctor runs in, which
may be a cloned repository's (ADR-0101's trust model). The probe goes only to a loopback address
named by the hub's runtime record -- a record naming any other host is a `WARN` and nothing is
sent -- with no credential, bounded in time and size, and no redirect off its own origin. The
budgets are the person's `[web]`, narrowed by the folder's (the hub reads them the same way). Every detail is cleaned as a raised check's is (`DoctorChecks.cleaned`); the line never
raises. Declared by `interfaces/web_tools_doctor_interface.py` (ADR-0016).
"""

from __future__ import annotations

import json
import ssl
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Final

from vibey.application.acp.doctor_checks import DoctorChecks
from vibey.bootstrap import acp_user_config
from vibey.domain.config import ConfigError
from vibey.domain.hub_scope import HubScope
from vibey.domain.hub_target import HUB_TARGETS
from vibey.infrastructure.hub.local_token import LocalTokenStore
from vibey.infrastructure.hub.settings import HUB_SETTINGS
from vibey.infrastructure.hub.tls import CERT_FILE
from vibey.infrastructure.web.bounded_request import BoundedRequest, DeadlineExceeded
from vibey.infrastructure.web.guarded_opener import SameOriginRedirects
from vibey.infrastructure.web.web_settings_loader import WEB_SETTINGS

NAME: Final = "web-tools"
ROUTES: Final = ("/api/v1/web/search", "/api/v1/web/fetch")
PROBE_SECONDS: Final = 3.0
PROBE_BYTES: Final = 1_000_000
"""The most of the OpenAPI document read; it is about a tenth of that."""
_WIDTH: Final = 26

type Probe = Callable[[str, Path | None], bytes]
"""Reads a URL on this computer's loopback, trusting `cafile` for https; at most `PROBE_BYTES`."""


class WebToolsDoctor:
    """Declared by `interfaces/web_tools_doctor_interface.py::WebToolsDoctorInterface`."""

    def __init__(
        self,
        *,
        config_path: Callable[[], Path] = lambda: Path.cwd() / "vibey.toml",
        user_config: Callable[[], Path] | None = None,
        probe: Probe | None = None,
    ) -> None:
        self._config_path = config_path
        self._user_config = user_config or (lambda: acp_user_config())
        self._probe = probe if probe is not None else self.loopback_document

    def line(self) -> str:
        try:
            return self._line()
        except Exception as exc:  # noqa: BLE001 - the line never breaks doctor
            reason = DoctorChecks.cleaned(f"{type(exc).__name__}: {exc}")
            return f"UNKNOWN {NAME:<{_WIDTH}} could not check the hub's web tools ({reason})"

    def _line(self) -> str:
        mine = self._user_config()
        try:
            # The person's own hub: never a state folder a project's vibey.toml names.
            hub = HUB_SETTINGS.load(mine)
            web = WEB_SETTINGS.load_trusted(mine, self._config_path())
        except ConfigError as exc:
            return f"FAIL {NAME:<{_WIDTH}} {DoctorChecks.cleaned(str(exc), limit=400)}"
        budgets = (
            f"budgets: {web.searches_per_hour} searches and {web.fetches_per_hour} fetches per "
            "hour per principal ([web])"
        )
        if HubScope.WEB not in hub.agent_scopes:
            return (
                f"WARN {NAME:<{_WIDTH}} the agent principal is not granted `web` ([hub] "
                "agent_scopes), so MCP clients are not offered vibey_search and vibey_fetch; add "
                f"it to turn them on; {budgets}"
            )
        problem = self._hub_problem(hub.state_dir)
        if problem is not None:
            return f"WARN {NAME:<{_WIDTH}} {DoctorChecks.cleaned(problem)}; {budgets}"
        return (
            f"PASS {NAME:<{_WIDTH}} the hub serves vibey_search and vibey_fetch to the agent "
            f"(web granted in your own [hub]; each use needs a project to record it on); {budgets}"
        )

    def _hub_problem(self, state_dir: Path) -> str | None:
        try:
            record = LocalTokenStore(state_dir).serving()
        except ValueError:
            record = None
        if record is None:
            return (
                "no hub is running, so vibey_search and vibey_fetch cannot answer until one is "
                "(`vibey hub start`)"
            )
        host = HUB_TARGETS.loopback_address(record.host)
        if host is None:
            return "the hub's runtime record names a non-loopback address; not probed"
        shown = f"[{host}]" if ":" in host else host
        scheme = "https" if record.tls else "http"
        cafile = state_dir / CERT_FILE if record.tls else None
        try:
            document = json.loads(
                self._probe(f"{scheme}://{shown}:{record.port}/api/v1/openapi.json", cafile)
            )
            paths = document.get("paths", {})
        except (OSError, ValueError, AttributeError, RecursionError, DeadlineExceeded) as exc:
            return f"the running hub did not answer ({type(exc).__name__})"
        if not all(route in paths for route in ROUTES):
            return (
                "the running hub does not offer /api/v1/web/search and /web/fetch: it is an "
                "older vibey; `vibey hub stop` and `vibey hub start` run this one"
            )
        return None

    @staticmethod
    def loopback_document(url: str, cafile: Path | None) -> bytes:
        """`url`'s body, read with no credential, no proxy and no redirect off its own origin,
        within `PROBE_SECONDS` and `PROBE_BYTES` (`BoundedRequest`)."""
        handlers: list[urllib.request.BaseHandler] = [
            SameOriginRedirects(),
            urllib.request.ProxyHandler({}),
        ]
        if cafile is not None:
            handlers.append(
                urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=str(cafile)))
            )
        opener = urllib.request.build_opener(*handlers)
        request = urllib.request.Request(url, headers={"Accept": "application/json"})  # nosec B310
        return (
            BoundedRequest(lambda r, timeout: opener.open(r, timeout=timeout))
            .fetch(request, deadline=PROBE_SECONDS, limit=PROBE_BYTES)
            .body
        )


WEB_TOOLS_DOCTOR: Final = WebToolsDoctor()
"""The line as `vibey doctor` and `vibey acp` print it: the person's own `[hub]`, their `[web]`
narrowed by this folder's, and the hub on this computer's loopback."""
