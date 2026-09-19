# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for turning layered settings into a validated qwenloop configuration."""

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from qwenloop.domain.config import QwenConfig


@runtime_checkable
class QwenConfigParserInterface(Protocol):
    """Validates one flat settings mapping. Unknown keys and invalid values are refused."""

    def parse(self, data: Mapping[str, Any]) -> QwenConfig:
        """The validated configuration, or ValueError naming what is wrong."""
        ...
