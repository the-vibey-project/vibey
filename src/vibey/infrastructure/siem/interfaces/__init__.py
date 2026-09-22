# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Seams the SIEM adapters declare. Interfaces declare; they never consume."""

from vibey.infrastructure.siem.interfaces.in_memory_interface import InMemorySiemInterface
from vibey.infrastructure.siem.interfaces.wazuh_interface import WazuhSiemAdapterInterface

__all__ = [
    "InMemorySiemInterface",
    "WazuhSiemAdapterInterface",
]
