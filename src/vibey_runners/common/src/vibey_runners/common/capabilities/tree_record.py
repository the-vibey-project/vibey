# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One entry of a marketplace tree as the lock's digest sees it (`CapabilityLock.tree_records`).

`path` is relative to the tree's root, `/`-separated. `kind` is `D` (a folder), `F` (a file),
`X` (a file its owner may execute) or `L` (a symlink, never followed). `payload` is the hex sha256
of a file's content or of a symlink's target text, and empty for a folder. The digest is the
sha256 over every record, sorted; the run snapshot compares its copy record by record against the
records that produced the locked digest. A record with no behaviour, so no seam of its own.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TreeRecord:
    path: str
    kind: str
    payload: str
