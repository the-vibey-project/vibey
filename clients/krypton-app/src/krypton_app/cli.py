"""The `krypton` command."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from importlib.metadata import PackageNotFoundError, version

from krypton_app.launcher import KryptonLauncher


def _version() -> str:
    # A module-level function because it is a one-line lookup with no state (ADR-0016).
    try:
        return version("krypton-app")
    except PackageNotFoundError:  # pragma: no cover - only in an uninstalled tree
        return "0+unknown"


def main(argv: Sequence[str] | None = None) -> int:
    # A module-level function because a console-script entry point must be one (ADR-0016);
    # everything it does is KryptonLauncher's.
    parser = argparse.ArgumentParser(
        prog="krypton",
        description=(
            "krypton, the apps of vibey. Starts the local vibey hub (`vibey serve`) and "
            "opens it in your browser; if the installed vibey cannot serve it yet, says so "
            "and lists what is available instead."
        ),
    )
    parser.add_argument("--version", action="version", version=f"krypton {_version()}")
    parser.add_argument(
        "--host", default="127.0.0.1", help="address to serve on (default: 127.0.0.1)"
    )
    parser.add_argument("--port", type=int, default=8765, help="port to serve on (default: 8765)")
    parser.add_argument(
        "--no-browser", action="store_true", help="start the hub without opening it"
    )
    parser.add_argument(
        "--vibey", default=None, help="the vibey program to use (default: vibey on PATH)"
    )
    args = parser.parse_args(argv)
    launcher = KryptonLauncher(out=sys.stdout, vibey=args.vibey)
    return launcher.launch(args.host, args.port, open_browser=not args.no_browser)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
