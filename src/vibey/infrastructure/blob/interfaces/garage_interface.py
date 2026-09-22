# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The Garage blob seam.

Mirrors `vibey/infrastructure/blob/garage.py` (ADR-0016). Interfaces declare;
they never consume.
"""

from typing import Protocol, runtime_checkable

from vibey.application.interfaces.blob import BlobPort


@runtime_checkable
class GarageBlobAdapterInterface(BlobPort, Protocol):
    """The self-hosted Garage implementation of the Blob port."""
