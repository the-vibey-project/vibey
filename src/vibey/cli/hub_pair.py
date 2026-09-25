# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey hub pair | devices | revoke`: the host's side of pairing (ADR-0068).

These commands talk to the hub `vibey serve` is running, as the host: they read where it
listens from `<state_dir>/serving.json` and present the host token beside it. `pair`
asks for a 6-digit offer of the scopes named (at least one; deny by default) and shows
it as a QR code the device scans, with the code and the URI in text beneath. `devices`
lists who is paired; `revoke` refuses a device from its next request.

Over a declared LAN the hub serves its own certificate, and these commands trust exactly
that certificate (the file in the state directory) and nothing else.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any, Final

import httpx
import typer

from vibey.cli.interfaces.hub_pair_interface import HubPairCommandInterface
from vibey.domain.config import ConfigError
from vibey.domain.hub_scope import HubScope
from vibey.infrastructure.hub.interfaces.settings_interface import HubSettingsLoaderInterface
from vibey.infrastructure.hub.local_token import LocalTokenStore
from vibey.infrastructure.hub.settings import HUB_SETTINGS
from vibey.infrastructure.hub.tls import CERT_FILE

EXIT_NOT_RUNNING: Final = 3
"""The exit code when no hub is running to talk to."""

WILDCARDS: Final = frozenset({"0.0.0.0", "::"})  # nosec B104 - compared, never bound

type Transport = Callable[..., httpx.Client]


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
        config_path: Callable[[], Path] = lambda: Path.cwd() / "vibey.toml",
        client: Transport = httpx.Client,
        qr: Callable[[str], str | None] = _render_qr,
    ) -> None:
        self._settings = settings
        self._config_path = config_path
        self._client = client
        self._qr = qr

    def pair(self, scopes: list[str]) -> None:
        """Offers a pairing of `scopes` and shows it."""
        if not scopes:
            typer.echo("name at least one --scope: a pairing grants nothing by default", err=True)
            raise typer.Exit(2)
        try:
            parsed = sorted({HubScope(value).value for value in scopes})
        except ValueError as exc:
            typer.echo(f"unknown scope: {exc}", err=True)
            raise typer.Exit(2) from exc
        offer = self._call("POST", "/pairing/offers", {"scopes": parsed})
        qr = self._qr(str(offer["uri"]))
        if qr is not None:
            typer.echo(qr)
        typer.echo(f"code: {offer['code']}  (valid for two minutes, once)")
        typer.echo(f"scopes: {', '.join(offer['scopes'])}")
        typer.echo(f"uri: {offer['uri']}")
        if offer.get("fingerprint"):
            typer.echo(f"certificate fingerprint (sha256): {offer['fingerprint']}")

    def devices(self) -> None:
        """Lists the paired devices."""
        listed = self._call("GET", "/devices", None)
        if not listed:
            typer.echo("no paired devices")
        for device in listed:
            typer.echo(f"{device['device_id']}  {device['name']}  {', '.join(device['scopes'])}")

    def revoke(self, device_id: str) -> None:
        """Revokes a device; refused from its next request."""
        self._call("DELETE", f"/devices/{device_id}", None)
        typer.echo(f"revoked {device_id}")

    def _call(self, method: str, route: str, body: dict[str, Any] | None) -> Any:
        try:
            settings = self._settings.load(self._config_path())
        except ConfigError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(2) from exc
        store = LocalTokenStore(settings.state_dir)
        record = store.serving()
        if record is None:
            typer.echo("no hub is running here: start one with `vibey serve`", err=True)
            raise typer.Exit(EXIT_NOT_RUNNING)
        host = "127.0.0.1" if record.host in WILDCARDS else record.host
        shown = f"[{host}]" if ":" in host else host
        scheme = "https" if record.tls else "http"
        # The hub's own certificate, and only it, when it serves one.
        verify: str | bool = str(settings.state_dir / CERT_FILE) if record.tls else True
        with self._client(
            base_url=f"{scheme}://{shown}:{record.port}/api/v1",
            headers={"authorization": f"Bearer {store.token()}"},
            verify=verify,
            timeout=10.0,
        ) as client:
            try:
                response = client.request(method, route, json=body)
            except httpx.HTTPError as exc:
                typer.echo(f"the hub did not answer: {exc}", err=True)
                raise typer.Exit(EXIT_NOT_RUNNING) from exc
        if response.status_code >= 400:
            typer.echo(f"refused ({response.status_code}): {response.text}", err=True)
            raise typer.Exit(1)
        return response.json()


HUB_PAIR: Final[HubPairCommandInterface] = HubPairCommand()

hub_app = typer.Typer(
    help="Pair devices with the running hub, list them, revoke them (ADR-0068).",
    no_args_is_help=True,
)


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
) -> None:
    """Show a QR code and a 6-digit code a device claims within two minutes."""
    HUB_PAIR.pair(scope)


@hub_app.command("devices")
def devices() -> None:
    """List the paired devices."""
    HUB_PAIR.devices()


@hub_app.command("revoke")
def revoke(device_id: Annotated[str, typer.Argument(help="The device to revoke.")]) -> None:
    """Revoke a device: refused from its next request."""
    HUB_PAIR.revoke(device_id)
