# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One marketplace the person added: where it comes from and, optionally, the ref it is pinned
to. A record with no behaviour, so no seam of its own."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MarketplaceSpec:
    name: str
    source: str
    ref: str | None
