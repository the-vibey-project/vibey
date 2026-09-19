# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Pure configuration values for ledger storage tiers (#114)."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TierConfig:
    """How many recent records remain raw and compressed before archival."""

    standard_n: int
    mid_tier_n: int
    archival_enabled: bool = True

    def __post_init__(self) -> None:
        if self.standard_n < 0 or self.mid_tier_n < 0:
            raise ValueError("ledger tier retention counts cannot be negative")
