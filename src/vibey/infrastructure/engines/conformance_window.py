# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""How long `vibey doctor --conformance` waits for an engine's run directory.

A hosted engine writes its run directory within seconds. A local model (gptossloop on
Ollama, qwenloop) loads weights and answers a first turn far more slowly on ordinary
hardware, and a window that is too short fails `run_dir_shape`, `snapshot_schema`,
`done_marker` and `structured_verdict` for a reason that is the host's speed, not the
engine's conformance. `VIBEY_CONFORMANCE_POLL_SECONDS` lets the operator say how long this
host needs, without editing the installed package.
"""

import math
from collections.abc import Mapping
from typing import Final

CONFORMANCE_POLL_ENV: Final[str] = "VIBEY_CONFORMANCE_POLL_SECONDS"


def conformance_poll_seconds(environ: Mapping[str, str]) -> float | None:
    """The run-directory wait the operator declared, or `None` for the built-in default.

    Unset or blank is `None`. A value that is not a finite number above zero raises
    `ValueError` naming the variable: an infinite wait would hang the check, and a silent
    fallback would hide a typo behind the very failure the setting exists to fix.
    """
    raw = environ.get(CONFORMANCE_POLL_ENV, "").strip()
    if not raw:
        return None
    try:
        seconds = float(raw)
    except ValueError:
        raise ValueError(f"{CONFORMANCE_POLL_ENV} must be a number of seconds") from None
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError(f"{CONFORMANCE_POLL_ENV} must be a finite number of seconds above zero")
    return seconds
