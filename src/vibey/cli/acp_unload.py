# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey acp unload`: stop the units `vibey acp` loaded, for good (ADR-0101).

`launchctl bootout` alone lasts until the next login, when launchd loads every plist in
`~/Library/LaunchAgents` again; `systemctl --user disable --now` lasts. So for each label vibey
recorded writing (`<[hub] state_dir>/acp-units.json`), this unloads it in the user's own domain
(`launchctl bootout gui/<uid>/<label>`, or `systemctl --user disable --now <label>.service`,
through the same argv allowlist as the bootstrap) and deletes the unit file only while it is
exactly what vibey wrote. A unit the operator edited is unloaded and left in place, and said so.
Run again, it finds nothing left. Everything is read from the user's own `vibey.toml`, never the
folder it runs in. It does not change `[acp] auto_services`: a `vibey acp` that runs later loads
them again unless that is set to false in the user's own `vibey.toml`.

Declared by `interfaces/acp_unload_interface.py`.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Final

import typer

from vibey.bootstrap import AcpMachine, acp_machine, acp_user_config
from vibey.infrastructure.acp.acp_settings_loader import AcpSettingsLoader
from vibey.infrastructure.acp.interfaces.acp_settings_loader_interface import (
    AcpSettingsLoaderInterface,
)

_SAID: Final = {
    "unloaded": "unloaded",
    "not-loaded": "was not loaded",
    "removed": "unit file removed",
    "absent": "unit file already gone",
}


class AcpUnloadCommand:
    """Declared by `AcpUnloadCommandInterface`."""

    def __init__(
        self,
        *,
        machine: Callable[..., AcpMachine] = acp_machine,
        settings: AcpSettingsLoaderInterface | None = None,
        user_config: Callable[[], Path] = acp_user_config,
        echo: Callable[[str], object] = typer.echo,
    ) -> None:
        self._machine = machine
        self._settings = settings if settings is not None else AcpSettingsLoader()
        self._user_config = user_config
        self._echo = echo

    def run(self) -> int:
        user_config = self._user_config()
        parts = self._machine(self._settings.load(user_config), user_config=user_config)
        units, loader = parts.units, parts.loader
        if units is None or loader is None:
            self._echo("vibey acp keeps no services on this computer; nothing to unload")
            return 0
        refused = loader.refused()
        if refused:
            self._echo(f"vibey acp unload: {refused}")
            return 1
        labels = units.recorded()
        if not labels:
            self._echo("vibey acp loaded no service here; nothing to unload")
            return 0
        failed = False
        for label in labels:
            unloaded = loader.unload(label)
            if unloaded.action == "failed":
                failed = True
                self._echo(f"{label}: not unloaded ({unloaded.detail}); its unit file is kept")
                continue
            removed = units.remove(label)
            if removed.action == "kept-differing":
                self._echo(
                    f"{label}: {_SAID[unloaded.action]}; {removed.path} is kept because "
                    f"{removed.detail} -- remove it yourself, or it loads again at your next login"
                )
            elif removed.action == "failed":
                failed = True
                self._echo(f"{label}: {_SAID[unloaded.action]}; {removed.path}: {removed.detail}")
            else:
                self._echo(f"{label}: {_SAID[unloaded.action]}; {_SAID[removed.action]}")
        forgotten = loader.forget_unit_files()
        if forgotten.action == "failed":
            failed = True
            self._echo(f"the service manager did not reload its units: {forgotten.detail}")
        self._echo(
            "vibey acp loads them again when an editor starts it, unless `[acp] auto_services = "
            f"false` is set in {user_config}"
        )
        return 1 if failed else 0


ACP_UNLOAD: Final = AcpUnloadCommand()
