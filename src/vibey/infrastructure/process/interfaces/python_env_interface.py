# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for locating the orchestrator's own Python environment.

Mirrors `vibey/infrastructure/process/python_env.py` (ADR-0016). Interfaces declare;
they never consume.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class OrchestratorPythonEnvInterface(Protocol):
    """Where vibey's own Python environment lives, which a spawned child must not inherit."""

    def interpreter_venv(self) -> str | None:
        """The running interpreter's prefix when that interpreter is a venv, else None."""
        ...

    def venv_prefixes(self) -> tuple[str | None, ...]:
        """The directories whose PATH entries belong to vibey's Python environment:
        the active `VIRTUAL_ENV` and `interpreter_venv()`. An entry is None when absent."""
        ...
