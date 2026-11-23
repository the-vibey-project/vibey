# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A file longer than the cap its reader was given; nothing of it is returned."""

from pathlib import Path


class FileTooLargeError(ValueError):
    def __init__(self, path: Path, limit: int) -> None:
        self.path = path
        self.limit = limit
        super().__init__(f"{path} is larger than {limit} bytes")
