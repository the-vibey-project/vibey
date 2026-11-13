# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey --version` and `vibey -v`: the engine and the app, one line each.

The two ship as separate distributions (`vibey-engine` and `krypton-app`, ADR-0069) that are
versioned apart, so one number would hide which half of a pair a bug report is about. The app
is an optional install: when it is absent the line says so rather than failing, because a
version flag that raises is worse than no flag.
"""

import importlib.metadata as metadata
from typing import Final

from vibey import __version__
from vibey.cli.interfaces.version_report_interface import VersionReportInterface

APP_DISTRIBUTION: Final = "krypton-app"


class VersionReport(VersionReportInterface):
    """Reads the engine's own version and the app's installed metadata."""

    def lines(self) -> tuple[str, str]:
        try:
            app = f"{APP_DISTRIBUTION} {metadata.version(APP_DISTRIBUTION)}"
        except metadata.PackageNotFoundError:
            app = f"{APP_DISTRIBUTION} not installed"
        return (f"vibey-engine {__version__}", app)


VERSION_REPORT: Final[VersionReportInterface] = VersionReport()
