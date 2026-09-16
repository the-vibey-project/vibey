# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Catch SIGTERM before the process is ready to handle it properly.

Kubernetes sends SIGTERM and waits. Linux treats PID 1 specially: a signal whose
disposition is still ``SIG_DFL`` is **discarded**, not queued -- so a container whose
process has not yet installed a handler does not receive that signal late, it never
receives it at all. The pod then runs until ``terminationGracePeriodSeconds`` expires,
which for a vibey worker is two hours.

The worker already registers its drain handler as the first statement inside the event
loop, before any I/O, and that is still the right place for the *real* handler. It is not
early enough to win this race: everything before it -- interpreter start, importing the
CLI and its dependencies, argument parsing, starting the loop -- is time during which the
signal is thrown away. Measured against a scale-in that deleted a pod 0.2s after its
container started, that window is the whole story.

So this module installs a deliberately tiny handler at import time, whose only job is to
remember. Whatever starts afterwards asks whether SIGTERM already arrived and acts on it
instead of waiting for one that will never come again.
"""

from __future__ import annotations

import signal
import types
from collections.abc import Callable


class SigtermLatch:
    """A one-bit memory for a SIGTERM that arrived too early to act on."""

    def __init__(self) -> None:
        self._fired = False
        self._armed = False
        # The exact object handed to `signal.signal`, kept so `release` can ask whether it
        # is still installed. `self._remember` cannot answer that: it is a bound method,
        # and every attribute access builds a NEW one, so an identity check against it is
        # false even when this latch's handler is the one in place.
        self._installed: Callable[[int, types.FrameType | None], None] | None = None

    @property
    def fired(self) -> bool:
        return self._fired

    def arm(self) -> bool:
        """Install the handler, returning whether it took.

        ``signal.signal`` only works on the main thread. Importing this module from a
        worker thread is legitimate -- a test runner, an embedding host -- and must not
        raise, so a refusal is reported rather than thrown. A process that cannot arm the
        latch simply keeps the old behaviour.
        """
        if self._armed:
            return True
        handler = self._remember
        try:
            signal.signal(signal.SIGTERM, handler)
        except ValueError:
            return False
        self._installed = handler
        self._armed = True
        return True

    def release(self) -> None:
        """Give SIGTERM back to the default disposition -- but only while this latch's own
        handler is still the one installed.

        The guard is the whole point, and its absence was a live defect. `release()` is
        called once the real handler is installed, and the real handler goes in FIRST: the
        worker calls `loop.add_signal_handler(SIGTERM, ...)` and releases the latch
        afterwards. An unconditional `signal.signal(SIGTERM, SIG_DFL)` here therefore did
        not tidy THIS handler away -- it destroyed THAT one, and left the process on the
        default disposition. A pod sent SIGTERM then died where it stood instead of
        draining: the exact scale-in failure the latch exists to make survivable, caused
        by the line meant to clean up after it.

        Handing the signal back is only ever correct while nobody else has claimed it. A
        latch that outlives its purpose is a handler nobody is looking at; a latch that
        outlives somebody else's handler is worse.
        """
        if not self._armed:
            return
        self._armed = False
        if signal.getsignal(signal.SIGTERM) is self._installed:
            signal.signal(signal.SIGTERM, signal.SIG_DFL)
        self._installed = None

    def _remember(self, _signum: int, _frame: types.FrameType | None) -> None:
        # Deliberately only this. A signal handler runs between bytecodes, on whatever
        # stack happens to be executing; doing anything that can block or allocate
        # meaningfully here is how a drain turns into a hang.
        self._fired = True


#: Armed on import, which is the earliest point the CLI controls.
SIGTERM_LATCH = SigtermLatch()
