# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A path that opened but is not a regular file (a FIFO, a folder, a device): never read."""

from pathlib import Path


class NotRegularFileError(OSError):
    def __init__(self, path: Path) -> None:
        super().__init__(f"{path} is not a regular file")
        self.path = path
