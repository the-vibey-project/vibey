# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A lock file, or a marketplace tree, that cannot be trusted as written: nothing of it is used."""


class LockError(ValueError):
    """Raised by `CapabilityLock`; the message names the file and what is wrong with it."""
