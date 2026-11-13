# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for the two-line version report `vibey --version` and `vibey -v` print."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class VersionReportInterface(Protocol):
    """Says which engine and which app are installed."""

    def lines(self) -> tuple[str, str]:
        """`vibey-engine <version>`, then `krypton-app <version>` or `krypton-app not installed`."""
        ...
