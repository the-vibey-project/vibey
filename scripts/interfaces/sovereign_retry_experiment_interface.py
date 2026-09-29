# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts `scripts/sovereign_retry_experiment.py` implements.

Interfaces declare; they never consume (ADR-0016).
"""

from typing import Any, Protocol


class ExchangeRecorderInterface(Protocol):
    """Remembers every HTTP exchange the real Ollama client made during one run."""

    def reset(self) -> None:
        """Forget the exchanges of the previous run."""
        ...

    def exchanges(self) -> list[dict[str, Any]]:
        """One row per request: the budget it asked for and what came back."""
        ...


class SovereignRetryExperimentInterface(Protocol):
    """Replays representative DESIGN and DECOMPOSE requests through the real producers."""

    async def run(self) -> dict[str, Any]:
        """Every run's outcome plus a per-workload summary table."""
        ...
