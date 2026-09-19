# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for one schema-constrained exchange with a local model.

Mirrors `vibey/infrastructure/engines/ollama_chat.py` (ADR-0016). Interfaces declare;
they never consume.
"""

from collections.abc import Mapping
from typing import Protocol, runtime_checkable


@runtime_checkable
class OllamaTransportInterface(Protocol):
    """Sends one JSON body to one URL and hands back the decoded JSON object."""

    async def post_json(
        self, url: str, payload: Mapping[str, object], *, timeout: int
    ) -> dict[str, object]:
        """Raises ValueError for a non-HTTP(S) URL or a body that is not a JSON object."""
        ...


@runtime_checkable
class OllamaChatClientInterface(Protocol):
    """Asks the local model one question whose answer is constrained to a JSON schema."""

    @property
    def base_url(self) -> str: ...

    @property
    def model(self) -> str: ...

    def context_window(self, prompt_chars: int) -> int:
        """The `num_ctx` a prompt of this many characters is sent with."""
        ...

    async def ask(self, system: str, user: str, schema: Mapping[str, object]) -> dict[str, object]:
        """The model's answer as a JSON object, or ValueError when it is not one."""
        ...
