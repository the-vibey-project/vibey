# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Seams the SMS adapters declare. Interfaces declare; they never consume."""

from vibey.infrastructure.sms.interfaces.fossify_interface import FossifySmsAdapterInterface
from vibey.infrastructure.sms.interfaces.in_memory_interface import InMemorySmsInterface

__all__ = [
    "FossifySmsAdapterInterface",
    "InMemorySmsInterface",
]
