# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A `[loops]` table that cannot be read as a bundle, named by the key path that is wrong."""


class BundleError(ValueError):
    """Raised by `BundleSpec.from_mapping`; `path` is the key path, e.g.
    `loops.mcp_servers[0].url`, so the person can find the line without guessing."""

    def __init__(self, path: str, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"{path}: {reason}")
