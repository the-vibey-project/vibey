# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The MCP hub gateway: forwards validated host-LLM tool calls to the running hub (ADR-0100).

Mirrors `cli/hub_pair.py::HubPairCommand._call`, with two deliberate differences:
1. It presents `<state_dir>/agent.token` (`LocalTokenStore.agent_token()`), never the host token,
   so the hub enforces `[hub] agent_scopes` (no `spend`, `bump` or `workflows`).
2. When no hub is running (or a stale `serving.json` fails to answer), it invokes the `starter`
   seam once (`vibey hub start`) and retries before returning an error naming `vibey hub start`.
"""

from __future__ import annotations

import subprocess  # nosec B404
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import httpx

from vibey.domain.config import ConfigError
from vibey.domain.errors import VibeyError
from vibey.domain.host_tools import HubCall
from vibey.domain.hub_scope import AGENT_DEFAULT_SCOPES, HubScope
from vibey.infrastructure.hub.interfaces.settings_interface import HubSettingsLoaderInterface
from vibey.infrastructure.hub.local_token import LocalTokenStore, ServingRecord
from vibey.infrastructure.hub.settings import HUB_SETTINGS, HubSettings
from vibey.infrastructure.hub.tls import CERT_FILE
from vibey.infrastructure.mcp.interfaces.hub_gateway_interface import HubGatewayInterface

WILDCARDS: Final = frozenset({"0.0.0.0", "::"})  # nosec B104 - compared, never bound
START_TIMEOUT_SECONDS: Final = 15.0

type ClientFactory = Callable[..., httpx.Client]
type HubStarter = Callable[[], bool]


class HubGatewayError(VibeyError):
    """The hub could not be reached or refused the agent principal."""


@dataclass(frozen=True, slots=True)
class HubGatewayResponse:
    status_code: int
    text: str
    ok: bool


def _default_starter() -> bool:
    """Run `vibey hub start` in a child process and return True when it exits 0.

    Module-level by design: the default of `HubGateway`'s `starter` seam.
    """
    try:
        completed = subprocess.run(  # noqa: S603  # nosec B603
            [sys.executable, "-c", "from vibey.cli.main import run; run(['hub', 'start'])"],
            capture_output=True,
            text=True,
            timeout=START_TIMEOUT_SECONDS,
            check=False,
        )
    except OSError:
        return False
    return completed.returncode == 0


class HubGateway:
    """Synchronous HTTP client from `vibey mcp` to the local hub using the agent token.

    Declared by `interfaces/hub_gateway_interface.py::HubGatewayInterface`.
    """

    def __init__(
        self,
        *,
        settings: HubSettingsLoaderInterface = HUB_SETTINGS,
        config_path: Callable[[], Path] = lambda: Path.cwd() / "vibey.toml",
        client: ClientFactory = httpx.Client,
        starter: HubStarter = _default_starter,
        timeout: float = 15.0,
    ) -> None:
        self._settings = settings
        self._config_path = config_path
        self._client = client
        self._starter = starter
        self._timeout = timeout

    def agent_scopes(self) -> frozenset[HubScope]:
        """The scopes declared for the agent principal, or `AGENT_DEFAULT_SCOPES` if config fails."""
        try:
            loaded = self._settings.load(self._config_path())
        except ConfigError:
            return AGENT_DEFAULT_SCOPES
        return loaded.agent_scopes

    def call(self, call: HubCall) -> HubGatewayResponse:
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
            record = self._start_and_read(store)
        try:
            return self._send(settings, record, token, call)
        except httpx.HTTPError as first_exc:
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
            return self._settings.load(self._config_path())
        except ConfigError as exc:
            raise HubGatewayError(str(exc)) from exc

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
        host = "127.0.0.1" if record.host in WILDCARDS else record.host
        shown = f"[{host}]" if ":" in host else host
        scheme = "https" if record.tls else "http"
        verify: str | bool = str(settings.state_dir / CERT_FILE) if record.tls else True
        with self._client(
            base_url=f"{scheme}://{shown}:{record.port}",
            headers={"authorization": f"Bearer {token}"},
            verify=verify,
            timeout=self._timeout,
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
