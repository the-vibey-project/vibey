# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A run's capability document that cannot be written, or that is refused when it is read: the
run does not start with it, and the message says why (SP-LOOPS Phase 4, R9: a runner that
refuses its document exits 78)."""


class SnapshotDocumentError(ValueError):
    """Raised by `SnapshotDocument.from_json` and `SnapshotDocumentStore`; nothing of the
    document is used."""
