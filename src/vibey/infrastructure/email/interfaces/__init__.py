# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Seams the email adapters declare. Interfaces declare; they never consume."""

from vibey.infrastructure.email.interfaces.forward_email_interface import (
    ForwardEmailAdapterInterface,
)
from vibey.infrastructure.email.interfaces.in_memory_interface import InMemoryEmailInterface

__all__ = [
    "ForwardEmailAdapterInterface",
    "InMemoryEmailInterface",
]
