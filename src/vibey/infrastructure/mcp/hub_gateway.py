# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The MCP hub gateway: forwards validated host-LLM tool calls to the running hub (ADR-0100).

Mirrors `cli/hub_pair.py::HubPairCommand._call`, with two deliberate differences:
1. It presents `<state_dir>/agent.token` (`LocalTokenStore.agent_token()`), never the host token,
   so the hub enforces `[hub] agent_scopes` (no `spend`, `bump` or `workflows`).
2. When no hub is running (or a stale `serving.json` fails to answer), it invokes the `starter`
   seam once (`vibey hub start`) and retries before returning an error naming `vibey hub start`.
3. It sends a request at most once more, and only when the first never reached the hub (the
   connection was refused or never made): a request that may have arrived -- a read timeout, a
   reset after sending -- is never sent again, and the hub is not started over it. A web search
   or fetch is not something to repeat: it would leave the computer twice and spend twice.
4. A call to the open web (`vibey_search`, `vibey_fetch`) waits longer than the hub's own web
   deadline (`[web] timeout_seconds`, and three search timeouts for SearXNG's identity check,
   SearXNG and the Brave backup) plus `WEB_TIMEOUT_MARGIN`, so the hub always answers first.
5. `[hub]` is the person's own (`config_path`, their configuration folder's `vibey.toml`): the
   state folder -- so the agent token and the runtime record -- and the ceiling on
   `agent_scopes`. The `vibey.toml` of the folder the client opened (`project_config`) may be a
   cloned repository's: it may only narrow `agent_scopes` and `[web]`, never name a state folder
   (SP-ACP Task 11a, the Task 8 trust split). A hub this gateway starts runs in the person's
   configuration folder, so it reads the same file.
6. It reaches only a hub on this computer's loopback: a runtime record naming any other host is
   refused before the token, or a call -- a gate answer, a search query, a URL -- is sent
   anywhere, and the connection goes to the fixed loopback literal `HUB_TARGETS` returns, never
   to the record's name resolved again (SP-ACP Task 9b).
"""

from __future__ import annotations

import os
import subprocess  # nosec B404
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import httpx

from vibey.domain.config import ConfigError
from vibey.domain.errors import VibeyError
from vibey.domain.host_tools import HubCall
from vibey.domain.hub_scope import AGENT_DEFAULT_SCOPES, HubScope
from vibey.domain.hub_target import HUB_TARGETS
from vibey.domain.web_tools import WebToolSettings
from vibey.infrastructure.hub.interfaces.settings_interface import HubSettingsLoaderInterface
from vibey.infrastructure.hub.local_token import LocalTokenStore, ServingRecord
from vibey.infrastructure.hub.settings import HUB_SETTINGS, HubSettings
from vibey.infrastructure.hub.tls import CERT_FILE
from vibey.infrastructure.mcp.interfaces.hub_gateway_interface import HubGatewayInterface
from vibey.infrastructure.user_config_folder import UserConfigFolder
from vibey.infrastructure.web.search import DEFAULT_TIMEOUT_SECONDS as DEFAULT_SEARCH_TIMEOUT
from vibey.infrastructure.web.search import WebSearchSettings
from vibey.infrastructure.web.web_settings_loader import WEB_SETTINGS

START_TIMEOUT_SECONDS: Final = 15.0
WEB_TIMEOUT_MARGIN: Final = 15.0
"""Seconds a web call waits beyond the hub's own deadline for it, so the hub answers first."""
_NEVER_ARRIVED: Final = (httpx.ConnectError, httpx.ConnectTimeout)
"""Failures that prove the request never reached the hub: only these are sent again."""


def personal_config() -> Path:
    """The person's own `vibey.toml`, where `[hub]` and `[web]` are granted.

    Module-level by design: the default of `HubGateway`'s `user_config` seam, kept here so the
    test suite can stand another in for the developer's own file."""
    return UserConfigFolder().path() / "vibey.toml"


type ClientFactory = Callable[..., httpx.Client]
type HubStarter = Callable[[], bool]
type _Seen = tuple[Path, int, int, int, int]
"""A file as last seen: path, inode, mtime, ctime and size (all -1 when it did not exist)."""


class HubGatewayError(VibeyError):
    """The hub could not be reached or refused the agent principal."""


@dataclass(frozen=True, slots=True)
class HubGatewayResponse:
    status_code: int
    text: str
    ok: bool


def _default_starter(cwd: Path | None = None) -> bool:
    """Run `vibey hub start` in a child process and return True when it exits 0.

    Module-level by design: the default of `HubGateway`'s `starter` seam. The child's stdin is
    closed and its output captured: under `vibey mcp` and `vibey acp` this process's stdin and
    stdout are the client's protocol streams, and neither the child nor a hub it leaves behind
    may read or write them. `cwd` is the folder the hub starts in, and so whose `vibey.toml` it
    reads: `vibey acp` gives the user's own configuration folder (made, owner-only, if missing),
    never the project an editor opened (ADR-0101).
    """
    try:
        if cwd is not None:
            cwd.mkdir(mode=0o700, parents=True, exist_ok=True)
        completed = subprocess.run(  # noqa: S603  # nosec B603
            [sys.executable, "-c", "from vibey.cli.main import run; run(['hub', 'start'])"],
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=START_TIMEOUT_SECONDS,
            check=False,
        )
    except OSError:
        return False
    return completed.returncode == 0


default_hub_starter = _default_starter
"""The public name of `vibey hub start` run as a child, for the composition root and `vibey acp`
to give a `cwd` (the module-private name stays for the gateway's own default)."""


class HubGateway:
    """Synchronous HTTP client from `vibey mcp` to the local hub using the agent token.

    Declared by `interfaces/hub_gateway_interface.py::HubGatewayInterface`.
    """

    def __init__(
        self,
        *,
        settings: HubSettingsLoaderInterface = HUB_SETTINGS,
        config_path: Callable[[], Path] = lambda: personal_config(),
        project_config: Callable[[], Path] = lambda: Path.cwd() / "vibey.toml",
        client: ClientFactory = httpx.Client,
        starter: HubStarter | None = None,
        timeout: float = 15.0,
        environ: Callable[[], Mapping[str, str]] = lambda: os.environ,
    ) -> None:
        self._settings = settings
        self._config_path = config_path
        self._project_config = project_config
        self._client = client
        # A hub this gateway starts runs in the person's configuration folder, so it reads their
        # `[hub]` -- the same state folder this gateway reads the record and token from.
        self._starter = starter or (lambda: _default_starter(self._config_path().parent))
        self._timeout = timeout
        self._environ = environ
        self._scopes: tuple[tuple[_Seen, _Seen], frozenset[HubScope]] | None = None
        """The scopes last read, with the two `vibey.toml` files they were read from."""

    def agent_scopes(self) -> frozenset[HubScope]:
        """The scopes declared for the agent principal -- the person's own, narrowed by the
        opened folder's -- or `AGENT_DEFAULT_SCOPES` if config fails.

        Read again only when either `vibey.toml` changed -- another inode (a file swapped in by
        a rename), mtime, ctime or size: `vibey acp` asks on every prompt, from its event loop,
        and a `stat` is all that costs while the files stay as they were."""
        user, project = self._config_path(), self._project_config()
        seen = (self._seen(user), self._seen(project))
        if self._scopes is not None and self._scopes[0] == seen:
            return self._scopes[1]
        try:
            scopes = self._settings.load_trusted(user, project).agent_scopes
        except ConfigError:
            scopes = AGENT_DEFAULT_SCOPES
        self._scopes = (seen, scopes)
        return scopes

    @staticmethod
    def _seen(path: Path) -> _Seen:
        try:
            stat = path.stat()
        except OSError:
            return (path, -1, -1, -1, -1)
        return (path, stat.st_ino, stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size)

    def call(self, call: HubCall) -> HubGatewayResponse:
        return self._call(call, start=True)

    def reach(self, call: HubCall) -> HubGatewayResponse:
        """`call` with no side effect on the hub: a missing or silent hub is an error at once,
        and the starter is never run. A liveness probe goes this way, so probing whether the
        hub is up never starts or restarts it (ADR-0101: the keep-alive is the one authority
        that restarts a hub unit)."""
        return self._call(call, start=False)

    def _call(self, call: HubCall, *, start: bool) -> HubGatewayResponse:
        settings = self._load_settings()
        if not settings.agent_scopes:
            raise HubGatewayError(
                "agent access is disabled on this hub ([hub] agent_scopes = [] in vibey.toml)"
            )
        store = LocalTokenStore(settings.state_dir)
        try:
            token = store.agent_token()
        except (PermissionError, ValueError) as exc:
            raise HubGatewayError(f"agent token unusable: {exc}") from exc

        record = self._read_serving(store)
        if record is None:
            if not start:
                raise HubGatewayError("no hub is running on this computer")
            record = self._start_and_read(store)
        try:
            return self._send(settings, record, token, call)
        except httpx.HTTPError as first_exc:
            if not isinstance(first_exc, _NEVER_ARRIVED):
                raise HubGatewayError(
                    f"the hub did not answer in time ({type(first_exc).__name__}); the request may "
                    "have reached it, so it is not sent again"
                ) from first_exc
            if not start:
                raise HubGatewayError(f"the hub did not answer ({first_exc})") from first_exc
            if not self._starter():
                raise HubGatewayError(
                    f"the hub did not answer ({first_exc}); start it with `vibey hub start`"
                ) from first_exc
            refreshed = self._read_serving(store)
            if refreshed is None:
                raise HubGatewayError(
                    "no hub is running after `vibey hub start`; run `vibey hub start` to inspect"
                ) from first_exc
            try:
                return self._send(settings, refreshed, token, call)
            except httpx.HTTPError as second_exc:
                raise HubGatewayError(
                    f"the hub did not answer ({second_exc}); start it with `vibey hub start`"
                ) from second_exc

    def _load_settings(self) -> HubSettings:
        try:
            return self._settings.load_trusted(self._config_path(), self._project_config())
        except ConfigError as exc:
            raise HubGatewayError(str(exc)) from exc

    def _web_timeout(self) -> float:
        """How long a web call waits: the hub's longest web deadline plus the margin. The
        person's own `[web]` (narrowed by the folder's, as the hub reads it) and this process's
        search timeout, which is the hub's when the two share an environment."""
        try:
            fetch = WEB_SETTINGS.load_trusted(self._config_path(), self._project_config())
            deadline = fetch.timeout_seconds
        except ConfigError:
            deadline = WebToolSettings().timeout_seconds
        try:
            search = WebSearchSettings.from_environment(
                self._environ(), provisioned=lambda: None
            ).timeout_seconds
        except ConfigError:
            search = DEFAULT_SEARCH_TIMEOUT
        return max(self._timeout, deadline, 3 * search) + WEB_TIMEOUT_MARGIN

    @staticmethod
    def _read_serving(store: LocalTokenStore) -> ServingRecord | None:
        try:
            return store.serving()
        except ValueError:
            return None

    def _start_and_read(self, store: LocalTokenStore) -> ServingRecord:
        self._starter()
        record = self._read_serving(store)
        if record is None:
            raise HubGatewayError(
                "no hub is running on this computer; start one with `vibey hub start`"
            )
        return record

    def _send(
        self,
        settings: HubSettings,
        record: ServingRecord,
        token: str,
        call: HubCall,
    ) -> HubGatewayResponse:
        # The record's host is untrusted: connect to the fixed loopback literal it maps to, never
        # to its name resolved again, or to nothing at all.
        host = HUB_TARGETS.loopback_address(record.host)
        if host is None:
            raise HubGatewayError(
                "the hub's runtime record names a non-loopback address; vibey reaches only a hub "
                "on this computer's loopback, so nothing was sent"
            )
        shown = f"[{host}]" if ":" in host else host
        scheme = "https" if record.tls else "http"
        verify: str | bool = str(settings.state_dir / CERT_FILE) if record.tls else True
        with self._client(
            base_url=f"{scheme}://{shown}:{record.port}",
            headers={"authorization": f"Bearer {token}"},
            verify=verify,
            timeout=self._web_timeout() if call.open_world else self._timeout,
        ) as http:
            response = http.request(
                call.method,
                call.route,
                params=list(call.query) if call.query else None,
                json=dict(call.body) if call.body is not None else None,
            )
        return HubGatewayResponse(
            status_code=response.status_code,
            text=response.text,
            ok=response.status_code < 400,
        )


HUB_GATEWAY: Final[HubGatewayInterface] = HubGateway()
