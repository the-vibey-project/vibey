# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seams of scripts/typescript_artifacts.py: declared here, consumed there (ADR-0016)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class ArtifactInterface(Protocol):
    """One TypeScript source and every place its compiled JavaScript is committed."""

    @property
    def source(self) -> str: ...

    @property
    def module(self) -> str: ...

    @property
    def targets(self) -> tuple[str, ...]: ...


class TypeScriptCompilerInterface(Protocol):
    """Turns one TypeScript source into the JavaScript text it compiles to."""

    def compile(self, artifact: ArtifactInterface) -> str: ...


class TypeScriptArtifactsInterface(Protocol):
    """The committed JavaScript the repository still needs, and the means to check it."""

    def outputs(self) -> dict[Path, bytes]: ...

    def stale(self) -> list[Path]: ...

    def write(self) -> list[Path]: ...
