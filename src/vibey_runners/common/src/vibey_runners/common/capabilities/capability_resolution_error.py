# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A bundle that cannot be turned into a run snapshot: the run does not start, and the message
says why. `UnlockedMarketplaceError` and `LockMismatchError` are the two a person fixes by locking
a marketplace."""


class CapabilityResolutionError(ValueError):
    """Raised by `CapabilityResolver` and `SnapshotCopier`; nothing of the snapshot is used."""
