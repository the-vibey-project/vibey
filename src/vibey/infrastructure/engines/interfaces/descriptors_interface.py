# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for building a descriptor from the operator's configuration.

Mirrors `vibey/infrastructure/engines/descriptors.py` (ADR-0016). Interfaces declare;
they never consume.
"""

from typing import Protocol, runtime_checkable

from vibey.domain.config import ClaudeloopLocalConfig
from vibey.domain.engine import EngineDescriptor


@runtime_checkable
class ClaudeloopLocalDescriptorsInterface(Protocol):
    """Builds the claudeloop-local descriptor for one configured backend profile."""

    def build(self, config: ClaudeloopLocalConfig | None = None) -> EngineDescriptor:
        """The descriptor for `config`, or for the defaults (profile `local`) when None."""
        ...
