# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A preflight that cannot hang the conductor.

`<engine> doctor` shells out to a vendor CLI, and a CLI waiting on a login prompt, a locked
keychain or an unreachable server never answers. The startup preflight ran every probe at once
and waited for all of them, so one stuck probe kept a worker from starting for as long as the
CLI cared to wait (13 minutes was seen). A probe that does not answer in time is reported as
an engine that could not be checked, and the others carry on.
"""

import asyncio
from typing import Final

from vibey.application.dto import PreflightResult
from vibey.application.interfaces.engines import EngineAdapter

DEFAULT_PREFLIGHT_TIMEOUT_SECONDS: Final[float] = 180.0
"""Long enough for a local model to load and answer a tool call (claudeloop-local's check)."""


async def bounded_preflight(
    adapter: EngineAdapter, *, timeout: float = DEFAULT_PREFLIGHT_TIMEOUT_SECONDS
) -> PreflightResult:
    """`adapter.preflight()`, or an unchecked result naming the wait when it takes too long."""
    try:
        return await asyncio.wait_for(adapter.preflight(), timeout)
    except TimeoutError:
        return PreflightResult(
            installed=False,
            version=None,
            auth_ok=False,
            detail=(
                f"the health check did not answer in {timeout:g}s, so this engine was not "
                "checked; run `vibey doctor` for it, or leave it out with --engines"
            ),
        )
