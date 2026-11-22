# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""At most one `vibey hub start` per window, never in the caller's way (SP-ACP).

`HubGateway` calls its `starter` whenever a read finds no hub: no `serving.json`, or a hub that
does not answer. `vibey mcp` makes one call at a time, so waiting for the start there is right.
`vibey acp` reads the hub from many places at once -- the live feed's polls, the session
journal's flushes, each prompt's turn -- and with the plain starter each failed read ran
`vibey hub start` where it stood, up to 15 s each, inside a prompt turn too.

`BoundedHubStarter` is the starter `vibey acp` gives its gateway instead:

- **One attempt per window** (`[acp] hub_start_seconds`). The window runs from when the last
  attempt ended, whatever its outcome, so a failed start is remembered until it passes, and a
  start that worked is not repeated while the hub comes up.
- **Off the caller's thread.** The attempt runs on a thread of its own; the caller never waits
  for it.
- **Away at once.** Every call raises `HubGatewayError` ("the hub is away ...") straight away,
  so the read that found no hub fails now, as it would have after the wait, and the next read
  after the hub came up succeeds.

Declared by `interfaces/hub_start_policy_interface.py`.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from typing import Final

from vibey.infrastructure.mcp.hub_gateway import HubGatewayError, HubStarter, default_hub_starter

type Launch = Callable[[Callable[[], None]], None]
"""Run the attempt somewhere other than the caller: a daemon thread, or inline in a test."""

_LOG: Final = logging.getLogger(__name__)


def _thread(work: Callable[[], None]) -> None:
    """Start `work` on a daemon thread. Module-level by design: the default of
    `BoundedHubStarter`'s `launch` seam, which holds no state of its own."""
    threading.Thread(target=work, name="vibey-hub-start", daemon=True).start()


class BoundedHubStarter:
    """Declared by `interfaces/hub_start_policy_interface.py::BoundedHubStarterInterface`."""

    def __init__(
        self,
        starter: HubStarter = default_hub_starter,
        *,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
        launch: Launch = _thread,
    ) -> None:
        self._starter = starter
        self._window = window_seconds
        self._clock = clock
        self._launch = launch
        self._lock = threading.Lock()
        self._running = False
        self._ended: float | None = None
        self._worked = False
        self._idle = threading.Event()
        self._idle.set()

    def __call__(self) -> bool:
        with self._lock:
            if self._running:
                raise HubGatewayError(
                    "the hub is away; vibey is still starting it (`vibey hub start`)"
                )
            now = self._clock()
            if self._ended is not None and now - self._ended < self._window:
                raise HubGatewayError(self._recent(now - self._ended))
            self._running = True
            self._idle.clear()
        try:
            self._launch(self._attempt)
        except Exception as exc:
            # No thread could start: nothing is running, and the window still counts.
            with self._lock:
                self._running = False
                self._ended = self._clock()
                self._worked = False
            self._idle.set()
            raise HubGatewayError(f"the hub is away; vibey could not start it ({exc})") from exc
        raise HubGatewayError(
            "the hub is away; vibey is starting it in the background with `vibey hub start` "
            "-- try again in a moment"
        )

    def join(self, timeout: float) -> None:
        self._idle.wait(timeout)

    def _attempt(self) -> None:
        worked = False
        try:
            worked = self._starter()
        except Exception:
            _LOG.exception("`vibey hub start` could not be run")
        finally:
            with self._lock:
                self._running = False
                self._ended = self._clock()
                self._worked = worked
            self._idle.set()

    def _recent(self, ago: float) -> str:
        if self._worked:
            return (
                f"the hub is away although `vibey hub start` worked {ago:.0f} s ago; vibey "
                f"starts it at most once every {self._window:g} s (`[acp] hub_start_seconds`)"
            )
        return (
            f"the hub is away: `vibey hub start` failed {ago:.0f} s ago and vibey tries it at "
            f"most once every {self._window:g} s (`[acp] hub_start_seconds`); run it yourself "
            "to see why"
        )
