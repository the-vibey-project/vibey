# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A marketplace that is not what its lock says (Review Focus 3): its files changed after it was
locked, it changed while the run copied it, or the lock pins another source. The run refuses and
names the command that locks what is there now -- after the person has looked at the change."""

from vibey_runners.common.capabilities.capability_resolution_error import (
    CapabilityResolutionError,
)

CHANGED = "its files changed after it was locked"


class LockMismatchError(CapabilityResolutionError):
    def __init__(self, name: str, detail: str = CHANGED) -> None:
        self.name = name
        self.detail = detail
        super().__init__(
            f"the marketplace {name} does not match its lock ({detail}): check the change, then "
            f"run `vibey loops marketplace update {name}` to lock what is there now"
        )
