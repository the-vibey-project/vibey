# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One locked marketplace: where it came from, the ref it was pinned at, and the digest of its
tree (`CapabilityLock.digest_tree`) when it was locked. A record with no behaviour, so no seam of
its own."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LockEntry:
    marketplace: str
    source: str
    ref: str | None
    digest: str
