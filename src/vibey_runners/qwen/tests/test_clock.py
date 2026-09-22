# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from datetime import UTC, timedelta

from qwenloop.application.interfaces import ClockInterface
from qwenloop.infrastructure.clock import SystemClock


def test_system_clock_reads_utc_wall_time_and_a_forward_only_clock() -> None:
    clock = SystemClock()
    assert isinstance(clock, ClockInterface)
    moment = clock.now()
    assert moment.tzinfo is UTC
    assert moment.utcoffset() == timedelta(0)
    first = clock.monotonic()
    assert clock.monotonic() >= first
