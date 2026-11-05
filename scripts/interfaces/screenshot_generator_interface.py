# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for the krypton screenshot automation.

Declared per ADR-0016 and sub-doctrine 9.b (code lives in classes with interfaces).
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path


class ScreenshotGeneratorInterface(ABC):
    """Generates comprehensive visual screenshots for all krypton client surfaces."""

    @abstractmethod
    def generate_all(self, output_dir: Path) -> Sequence[Path]:
        """Generate screenshots for every screen of every krypton app."""
        ...

    @abstractmethod
    def generate_screen(self, app_id: str, screen_id: str, output_path: Path) -> Path:
        """Generate a single screen screenshot for a specific application."""
        ...
