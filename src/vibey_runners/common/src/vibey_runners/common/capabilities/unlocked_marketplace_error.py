# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A person-added marketplace the bundle uses has no lock entry (design Decision 1): a run never
fetches or locks one itself, so it says which command does."""

from vibey_runners.common.capabilities.capability_resolution_error import (
    CapabilityResolutionError,
)


class UnlockedMarketplaceError(CapabilityResolutionError):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(
            f"the marketplace {name} is not locked yet: run "
            f"`vibey loops marketplace update {name}` to fetch and lock it"
        )
