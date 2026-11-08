# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Seams the notification adapters declare. Interfaces declare; they never consume."""

from vibey.infrastructure.notify.interfaces.desktop_interface import DesktopNotifierInterface
from vibey.infrastructure.notify.interfaces.service_interface import (
    NotificationServiceInterface,
)

__all__ = ["DesktopNotifierInterface", "NotificationServiceInterface"]
