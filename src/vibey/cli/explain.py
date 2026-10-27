# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey explain CODE`: the cause of an error and what to do about it (#1691).

Reads only the shipped catalog. It opens no database connection and needs no configuration, so
it works for the very first error a new user meets (an unset `VIBEY_PG_URL`).
"""

from __future__ import annotations

import difflib

from vibey.cli.error_catalog import ErrorCatalog
from vibey.cli.interfaces.error_catalog_interface import ErrorCatalogInterface, ErrorEntry
from vibey.cli.interfaces.explainer_interface import ErrorExplainerInterface

EXIT_USAGE = 2
PAGE = "https://the-vibey-project.github.io/vibey/main/reference/errors/"


class ErrorExplainer(ErrorExplainerInterface):
    """Implements `ErrorExplainerInterface` over an error catalog."""

    def __init__(self, catalog: ErrorCatalogInterface | None = None) -> None:
        self._catalog = catalog

    @property
    def catalog(self) -> ErrorCatalogInterface:
        return self._catalog or ErrorCatalog.shipped()

    def _coded(self) -> list[ErrorEntry]:
        return [entry for entry in self.catalog.entries() if entry.code]

    def explain(self, code: str) -> tuple[int, str]:
        entry = self.catalog.by_code(code)
        if entry is None or entry.code is None:
            known = [e.code for e in self._coded() if e.code]
            close = difflib.get_close_matches(code.strip().upper(), known, n=3, cutoff=0.5)
            hint = f" Did you mean {', '.join(close)}?" if close else ""
            return (
                EXIT_USAGE,
                f"Error: no error has the code {code!r}.{hint} `vibey explain --list` shows them all.",
            )
        retired = " (retired: vibey no longer raises it)" if entry.retired else ""
        return (
            0,
            "\n".join(
                [
                    f"{entry.code}  {entry.title}{retired}",
                    f"Raised as {entry.qualname}",
                    "",
                    "Cause",
                    self._indent(entry.cause),
                    "",
                    "What to do",
                    self._indent(entry.fix),
                    "",
                    f"All error codes: {PAGE}#{entry.code.lower()}",
                ]
            ),
        )

    def listing(self) -> str:
        return "\n".join(f"{entry.code}  {entry.title}" for entry in self._coded())

    @staticmethod
    def _indent(text: str) -> str:
        return "\n".join(f"  {line}" if line else "" for line in text.strip().splitlines())
