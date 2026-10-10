# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for one schema-constrained exchange with a local model.

Mirrors `vibey/infrastructure/engines/ollama_chat.py` (ADR-0016). Interfaces declare;
they never consume.
"""

from collections.abc import AsyncGenerator, Mapping
from typing import Protocol, runtime_checkable


@runtime_checkable
class OllamaStreamTransportInterface(Protocol):
    """Sends one JSON body to one URL and yields each JSON line of the streamed reply."""

    def stream_json(
        self, url: str, payload: Mapping[str, object], *, timeout: int
    ) -> AsyncGenerator[dict[str, object], None]:
        """Yields objects as they arrive. `timeout` is how long one read may wait, not the
        whole answer. Raises ValueError for a non-HTTP(S) URL or a line that is not a JSON
        object."""
        ...


@runtime_checkable
class WireLogInterface(Protocol):
    """Records the lowest-level exchange with the model for an operator to follow live.

    One `call` is one `ask`; `attempt` counts the requests it needed (the budget retry
    and the empty-message retry are further attempts of the same call)."""

    def request(self, call: str, attempt: int, url: str, payload: Mapping[str, object]) -> None: ...

    def chunk(self, call: str, attempt: int, *, content: str, thinking: str) -> None:
        """A streamed fragment of the answer (`content`) and/or of the reasoning
        (`thinking`), as it arrived."""
        ...

    def response(
        self, call: str, attempt: int, body: Mapping[str, object], elapsed_seconds: float
    ) -> None: ...

    def error(
        self, call: str, attempt: int, error: BaseException, elapsed_seconds: float
    ) -> None: ...


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

    async def ask(
        self, system: str, user: str, schema: Mapping[str, object] | str
    ) -> dict[str, object]:
        """The model's answer as a JSON object, or ValueError when it is not one."""
        ...
