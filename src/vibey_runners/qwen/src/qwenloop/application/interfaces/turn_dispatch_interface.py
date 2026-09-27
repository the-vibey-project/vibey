# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam between a run and the model turn scheduler."""

from collections.abc import AsyncIterator, Sequence
from typing import Protocol

from qwenloop.domain.interfaces import ChatChunkInterface
from qwenloop.domain.model import ChatMessage, ServerInfo


class TurnDispatcherInterface(Protocol):
    """Dispatch one complete model request while preserving chunk order."""

    def dispatch(
        self,
        server: object,
        info: ServerInfo,
        messages: Sequence[ChatMessage],
    ) -> AsyncIterator[ChatChunkInterface]: ...
