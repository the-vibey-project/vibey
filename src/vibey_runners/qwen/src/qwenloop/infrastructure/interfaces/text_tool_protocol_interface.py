# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for carrying tool calls as text."""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from qwenloop.domain.model import ChatMessage


@runtime_checkable
class TextToolProtocolInterface(Protocol):
    def manual(self) -> str:
        """How to write a call, and a signature per tool."""
        ...

    def messages(self, history: Sequence[ChatMessage]) -> list[dict[str, str]]:
        """The history as plain chat a model with no tool role can follow."""
        ...
