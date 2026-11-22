# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Seams the web search declares. Interfaces declare; they never consume."""

from vibey.infrastructure.web.interfaces.backup_notice_interface import BackupNoticeInterface
from vibey.infrastructure.web.interfaces.guarded_opener_interface import GuardedOpenerInterface
from vibey.infrastructure.web.interfaces.local_first_search_interface import (
    LocalFirstSearchInterface,
)
from vibey.infrastructure.web.interfaces.search_backend_interface import SearchBackendInterface

__all__ = [
    "BackupNoticeInterface",
    "GuardedOpenerInterface",
    "LocalFirstSearchInterface",
    "SearchBackendInterface",
]
