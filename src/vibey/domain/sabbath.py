# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The Sabbath window (sub-doctrine 8.i; ADR-0070), as the domain sees it.

There is one implementation in the family and it lives in `vibey_gh.sabbath`: the NOAA
sunset computation and the Friday-sundown-to-Saturday-sundown window, both pure -- no
clock, no file, no network, no time-zone database; the caller passes the instant and a
`tzinfo`. `vibey-gh` declares no dependencies, which is what lets the domain import it
(CLAUDE.md: "`domain/` stays pure"), so this module re-exports it rather than keeping a
second copy (dogfood the family, ADR-0017).
"""

from vibey_gh.interfaces.sabbath_window_interface import (
    RestWindowInterface,
    SabbathWindowInterface,
    SunsetCalculatorInterface,
)
from vibey_gh.sabbath import OFFICIAL_ZENITH, RestWindow, SabbathWindow, SunsetCalculator

__all__ = [
    "OFFICIAL_ZENITH",
    "RestWindow",
    "RestWindowInterface",
    "SabbathWindow",
    "SabbathWindowInterface",
    "SunsetCalculator",
    "SunsetCalculatorInterface",
]
