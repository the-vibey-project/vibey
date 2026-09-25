# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind `RunArgvTemplate` in `vibey/infrastructure/engines/argv.py`.

Interfaces declare; they never consume. The descriptor is imported under TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.engine import EngineDescriptor


@runtime_checkable
class RunArgvTemplateInterface(Protocol):
    """`build_argv`'s `run` command line with every per-run value left as a placeholder."""

    def template(self, descriptor: EngineDescriptor) -> tuple[str, ...]:
        """Filled with one run's values, equal to what `build_argv` builds for that run."""
        ...
