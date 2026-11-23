# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey hub pair | devices | revoke`: the host's side of pairing (ADR-0068). `start`,
`stop` and `status` for the hub itself live in `hub_engine.py` and are registered below.

These commands talk to the hub `vibey serve` is running, as the host: they read where it
listens from `<state_dir>/serving.json` and present the host token beside it. `pair`
asks for a 6-digit offer of the scopes named (at least one; deny by default) and shows
it as a QR code the device scans, with the code and the URI in text beneath. `devices`
lists who is paired; `revoke` refuses a device from its next request.

Over a declared LAN the hub serves its own certificate, and these commands trust exactly
that certificate (the file in the state directory) and nothing else.

The host token is the most powerful credential the hub has, so where it goes is never decided by
a file a project could have written (SP-ACP Task 11a): `[hub]` -- the state folder holding the
token and the runtime record -- comes from the person's own `vibey.toml`, in their configuration
folder, never the folder the command runs in. The token goes only to this computer's loopback,
by the fixed literal `HUB_TARGETS.loopback_address` gives the record's host, unless the person
names a private-network address literal with `--host` (a hub bound to a LAN address with
`vibey serve --host 192.168.x.y` listens only there). A LAN address is used only when the
person's own record says the hub is bound there (or binds every address and this computer holds
that one) and the hub serves its own certificate: the request is https, verified against that
certificate alone, and never follows a redirect. Every check comes before the token is read;
anything else is refused before anything is sent.
"""

import ssl
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any, Final

import httpx
import typer

from vibey.application.acp.doctor_checks import DoctorChecks
from vibey.cli.hub_engine import start, status, stop
from vibey.cli.interfaces.hub_pair_interface import HubPairCommandInterface
from vibey.domain.config import ConfigError
from vibey.domain.hub_scope import HubScope
from vibey.domain.hub_target import HUB_TARGETS
from vibey.infrastructure.hub.interfaces.server_interface import LocalNamesInterface
from vibey.infrastructure.hub.interfaces.settings_interface import HubSettingsLoaderInterface
from vibey.infrastructure.hub.local_token import LocalTokenStore, ServingRecord
from vibey.infrastructure.hub.serve_lock import ServeLock
from vibey.infrastructure.hub.server import LOCAL_NAMES
from vibey.infrastructure.hub.settings import HUB_SETTINGS
from vibey.infrastructure.hub.tls import CERT_FILE, HubCertificate
from vibey.infrastructure.user_config_folder import UserConfigFolder

EXIT_NOT_RUNNING: Final = 3
"""The exit code when no hub is running to talk to."""

WILDCARDS: Final = frozenset({"0.0.0.0", "::"})  # nosec B104 - compared, never bound

type Transport = Callable[..., httpx.Client]

HOST_HELP: Final = (
    "The hub's address on your network, for a hub `vibey serve --host` bound to one: a "
    "private-network address literal (10/8, 172.16/12, 192.168/16, 100.64/10, fc00::/7). "
    "Without it the host token goes only to this computer's loopback."
)


def own_config() -> Path:
    """The person's own `vibey.toml`, in their configuration folder.

    Module-level by design: the default of `HubPairCommand`'s `config_path` seam, kept here so
    the test suite can stand another in for the developer's own file."""
    return UserConfigFolder().vibey_toml()


def _render_qr(uri: str) -> str | None:
    """The QR code for `uri`, as terminal text, or `None` without `segno` (the `hub`
    extra). Module-level by design: the default of `HubPairCommand`'s `qr` seam."""
    try:
        import segno
    except ImportError:
        return None
    lines: list[str] = []
    for row in segno.make(uri, error="m").matrix_iter(scale=1, border=2):
        lines.append("".join("██" if cell else "  " for cell in row))
    return "\n".join(lines)


class HubPairCommand:
    """Pairs, lists and revokes devices through the running hub, as the host.

    Declared by `interfaces/hub_pair_interface.py::HubPairCommandInterface`."""

    def __init__(
        self,
        *,
        settings: HubSettingsLoaderInterface = HUB_SETTINGS,
        config_path: Callable[[], Path] = lambda: own_config(),
        client: Transport = httpx.Client,
        qr: Callable[[str], str | None] = _render_qr,
        local_names: LocalNamesInterface = LOCAL_NAMES,
        holder: Callable[[Path], int | None] = lambda state: ServeLock(state).held_by(),
    ) -> None:
        self._local_names = local_names
        self._holder = holder
        self._settings = settings
        self._config_path = config_path
        self._client = client
        self._qr = qr

    def pair(self, scopes: list[str], host: str | None = None) -> None:
        """Offers a pairing of `scopes` and shows it."""
        if not scopes:
            typer.echo("name at least one --scope: a pairing grants nothing by default", err=True)
            raise typer.Exit(2)
        try:
            parsed = sorted({HubScope(value).value for value in scopes})
        except ValueError as exc:
            typer.echo(f"unknown scope: {exc}", err=True)
            raise typer.Exit(2) from exc
        offer = self._call("POST", "/pairing/offers", {"scopes": parsed}, host)
        qr = self._qr(str(offer["uri"]))
        if qr is not None:
            typer.echo(qr)
        typer.echo(f"code: {offer['code']}  (valid for two minutes, once)")
        typer.echo(f"scopes: {', '.join(offer['scopes'])}")
        typer.echo(f"uri: {offer['uri']}")
        if offer.get("fingerprint"):
            typer.echo(f"certificate fingerprint (sha256): {offer['fingerprint']}")

    def devices(self, host: str | None = None) -> None:
        """Lists the paired devices."""
        listed = self._call("GET", "/devices", None, host)
        if not listed:
            typer.echo("no paired devices")
        for device in listed:
            typer.echo(f"{device['device_id']}  {device['name']}  {', '.join(device['scopes'])}")

    def revoke(self, device_id: str, host: str | None = None) -> None:
        """Revokes a device; refused from its next request."""
        self._call("DELETE", f"/devices/{device_id}", None, host)
        typer.echo(f"revoked {device_id}")

    def _call(self, method: str, route: str, body: dict[str, Any] | None, named: str | None) -> Any:
        target = None if named is None else HUB_TARGETS.lan_address(named)
        if named is not None and target is None:
            typer.echo(
                "--host must be this computer's loopback or an address literal on a private "
                "network (10/8, 172.16/12, 192.168/16, 100.64/10, fc00::/7), not a name",
                err=True,
            )
            raise typer.Exit(2)
        try:
            settings = self._settings.load(self._config_path())
        except ConfigError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(2) from exc
        store = LocalTokenStore(settings.state_dir)
        try:
            record = store.serving()
        except (OSError, ValueError) as exc:
            # A malformed record of your own (pid <= 1, a port out of range, not JSON): one
            # line, as `vibey hub status` says it, never a traceback (SP-ACP Task 11b, N2-4).
            said = DoctorChecks.cleaned(str(exc))
            typer.echo(f"hub record unreadable: {said}", err=True)
            raise typer.Exit(2) from exc
        if record is None:
            typer.echo("no hub is running here: start one with `vibey serve`", err=True)
            raise typer.Exit(EXIT_NOT_RUNNING)
        if self._holder(settings.state_dir) != record.pid:
            # A record whose process does not hold the hub's lock is stale, and its port may be
            # another account's (SP-ACP Task 11a). A live hub's record names a port it already
            # holds: see the module docstring of `hub_gateway.py` (point 7).
            typer.echo(
                "no hub holds the lock its runtime record names, so the record is stale and "
                "nothing was sent: start one with `vibey hub start`",
                err=True,
            )
            raise typer.Exit(EXIT_NOT_RUNNING)
        cert = settings.state_dir / CERT_FILE
        problem, host = self._where(record, target, cert)
        if host is None:
            # Every check comes before the token is read: nothing, not the token, is sent.
            typer.echo(f"{problem}; nothing was sent", err=True)
            raise typer.Exit(2)
        shown = f"[{host}]" if ":" in host else host
        scheme = "https" if record.tls else "http"
        try:
            # The hub's own certificate, and only it, when it serves one: a context whose only
            # authority it is (never the system's store, never no verification; Task 11b).
            verify: ssl.SSLContext | bool = (
                HubCertificate(settings.state_dir).client_context() if record.tls else True
            )
            token = store.token()
            opened = self._client(
                base_url=f"{scheme}://{shown}:{record.port}/api/v1",
                headers={"authorization": f"Bearer {token}"},
                verify=verify,
                timeout=10.0,
                follow_redirects=False,
            )
        except (OSError, ValueError) as exc:
            # The token's or the certificate's file: one line, never a traceback (Task 11a N-5).
            said = DoctorChecks.cleaned(f"{type(exc).__name__}: {exc}")
            typer.echo(f"the hub's token or certificate could not be read: {said}", err=True)
            raise typer.Exit(2) from exc
        with opened as client:
            try:
                response = client.request(method, route, json=body)
            except httpx.HTTPError as exc:
                typer.echo(f"the hub did not answer ({type(exc).__name__})", err=True)
                raise typer.Exit(EXIT_NOT_RUNNING) from exc
        if 300 <= response.status_code < 400:
            # The token never follows a redirect, wherever it points.
            typer.echo(
                f"the hub answered with a redirect ({response.status_code}); it is not followed",
                err=True,
            )
            raise typer.Exit(1)
        if response.status_code >= 400:
            typer.echo(f"refused ({response.status_code}): {response.text}", err=True)
            raise typer.Exit(1)
        return response.json()

    def _where(
        self, record: ServingRecord, named: str | None, cert: Path
    ) -> tuple[str, str | None]:
        """The address the host token may go to, or why it may go nowhere.

        Without `--host`: the fixed loopback literal the record's host maps to. With a loopback
        `--host`: that literal, when the record's hub is on the loopback too. With a LAN address:
        only when the person's own record says the hub is bound there -- the same address, or a
        wildcard bind and an address this computer holds -- and the hub serves its own
        certificate (the token never crosses a network in the clear)."""
        on_loopback = HUB_TARGETS.loopback_address(record.host)
        if named is None:
            if on_loopback is None:
                return (
                    "the hub's runtime record names an address off this computer's loopback; if "
                    "your hub listens on a LAN address, name it with --host",
                    None,
                )
            return "", on_loopback
        if HUB_TARGETS.loopback_address(named) is not None:
            if on_loopback is None:
                return "--host names the loopback, but the hub is not listening there", None
            return "", named
        bound = record.host in WILDCARDS and named in self._local_names.names(record.host)
        if not bound and HUB_TARGETS.lan_address(record.host) != named:
            return "--host is not the address the running hub is bound to", None
        if not record.tls or not cert.is_file():
            return (
                "the hub on that LAN address does not serve its own certificate, so the host "
                "token would cross the network in the clear; declare `[hub] lan = true` and "
                "restart it with `vibey serve --host <address>` so it serves one",
                None,
            )
        return "", named


HUB_PAIR: Final[HubPairCommandInterface] = HubPairCommand()

hub_app = typer.Typer(
    help="Start, stop and ask about the hub; pair devices with it, list them, revoke them "
    "(ADR-0068).",
    no_args_is_help=True,
)
hub_app.command("status")(status)
hub_app.command("start")(start)
hub_app.command("stop")(stop)


@hub_app.command("pair")
def pair(
    scope: Annotated[
        list[str],
        typer.Option(
            "--scope",
            help="A scope to grant: view, answer, spend, run or bump. Repeat for more; "
            "at least one.",
        ),
    ],
    host: Annotated[str | None, typer.Option("--host", help=HOST_HELP)] = None,
) -> None:
    """Show a QR code and a 6-digit code a device claims within two minutes."""
    HUB_PAIR.pair(scope, host)


@hub_app.command("devices")
def devices(
    host: Annotated[str | None, typer.Option("--host", help=HOST_HELP)] = None,
) -> None:
    """List the paired devices."""
    HUB_PAIR.devices(host)


@hub_app.command("revoke")
def revoke(
    device_id: Annotated[str, typer.Argument(help="The device to revoke.")],
    host: Annotated[str | None, typer.Option("--host", help=HOST_HELP)] = None,
) -> None:
    """Revoke a device: refused from its next request."""
    HUB_PAIR.revoke(device_id, host)
