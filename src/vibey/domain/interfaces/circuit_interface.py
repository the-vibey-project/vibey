# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for when engine failures open an engine's circuit.

``FailureClass.ENGINE`` (``domain/job.py``) is the engine's own fault -- a
crashed, killed or hung runner -- as opposed to ``WORK`` (the code under
construction is wrong) or ``CAPACITY`` (the vendor said no). One such failure
is noise; several in a row mean the engine should leave rotation for a while.
This seam names how many, and how long "a while" is.
"""

from datetime import datetime, timedelta
from typing import Protocol, runtime_checkable


@runtime_checkable
class EngineFailurePolicyInterface(Protocol):
    """When consecutive ENGINE-class failures open a circuit, and when the
    opened circuit is probed again."""

    @property
    def threshold(self) -> int:
        """The consecutive-failure count at which the circuit opens."""
        ...

    @property
    def probe_base(self) -> timedelta:
        """The probe delay the first time the threshold is reached."""
        ...

    @property
    def probe_cap(self) -> timedelta:
        """The longest the probe delay ever grows to."""
        ...

    def trips(self, consecutive_failures: int) -> bool:
        """True once ``consecutive_failures`` has reached the threshold."""
        ...

    def probe_at(self, *, now: datetime, consecutive_failures: int) -> datetime:
        """When a circuit opened at ``now`` becomes selectable again, as a
        half-open probe. Grows with each failure past the threshold, so an
        engine that keeps failing its probes waits longer each time."""
        ...
