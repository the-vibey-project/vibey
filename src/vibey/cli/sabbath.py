# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey sabbath`, and the Sabbath at the command line (sub-doctrine 8.i; ADR-0070).

From sundown Friday to sundown Saturday a command that would set vibey writing code
declines: it says why and when it resumes, and exits 75 (EX_TEMPFAIL, "try again later")
-- paused, not failed (10.f). Reading commands (`status`, `projects`, `gates`, `doctor`,
this one) are never held.
"""

import os
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Final

import typer

from vibey.cli.interfaces.sabbath_interface import SabbathCommandInterface
from vibey.infrastructure.interfaces.sabbath_interface import HostSabbathGateInterface
from vibey.infrastructure.sabbath import HostSabbathGate

EXIT_RESTING: Final = 75


class SabbathCommand(SabbathCommandInterface):
    """Reads the host's Sabbath from `./vibey.toml` and answers for the command line."""

    def __init__(
        self,
        gate_factory: Callable[[], HostSabbathGateInterface] | None = None,
        *,
        root: Path | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> None:
        self._factory = gate_factory
        self._root = root
        self._environ = environ

    def gate(self) -> HostSabbathGateInterface:
        if self._factory is not None:
            return self._factory()
        root = self._root if self._root is not None else Path.cwd()
        return HostSabbathGate.from_toml(
            root / "vibey.toml",
            home=Path.home(),
            environ=os.environ if self._environ is None else self._environ,
        )

    def decline_if_resting(self, command: str) -> None:
        """Exit 75 with the reason when 8.i holds; return when the command may run."""
        held = self.gate().hold()
        if held is None:
            return
        typer.echo(
            f"vibey {command}: resting for the Sabbath (sub-doctrine 8.i) until"
            f" {held.resumes.isoformat()} ({held.basis}). Nothing was changed; run it again"
            " after the window closes."
        )
        raise typer.Exit(EXIT_RESTING)

    def status(self) -> list[str]:
        return self.gate().describe()

    def doctor_lines(self) -> tuple[list[str], bool]:
        """What `vibey doctor` prints, and whether the host's location was resolved. An
        unresolved host is a loud failure, never a silent pass: the window then runs on
        the declared fallback times."""
        gate = self.gate()
        lines = [f"sabbath  {line}" for line in gate.describe()]
        if gate.location_resolved():
            return lines, True
        lines.append(
            "sabbath  FAIL: no location source answered -- set [sabbath] latitude/longitude"
            " in this machine's vibey.toml (never committed), or install CoreLocationCLI"
            " (macOS) / GeoClue (Linux)"
        )
        return lines, False


SABBATH: Final = SabbathCommand()
