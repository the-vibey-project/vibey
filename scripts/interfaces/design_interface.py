# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts `scripts/design/` implements. Interfaces declare; they never consume.

`design/tokens/*.tokens.json` (DTCG 2025.10) is the one source of every colour, face, space,
radius, shadow, curve and sound cue a vibey surface uses. A token set reads it; emitters turn it
into each platform's form; a contrast audit proves the colour pairs legible; the generator writes
or checks every output.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class Token:
    """One resolved design token: its dotted path, DTCG type and value with references followed."""

    path: str
    type: str
    value: Any
    description: str = ""


@dataclass(frozen=True, slots=True)
class ContrastResult:
    """One foreground/background pair measured in one theme."""

    theme: str
    rule: str
    foreground: str
    background: str
    foreground_hex: str
    background_hex: str
    ratio: float
    minimum: float

    @property
    def passes(self) -> bool:
        """Whether the pair reaches the rule's WCAG 2.2 minimum."""
        return self.ratio >= self.minimum


class TokenSetInterface(Protocol):
    """Every token in the source files, references resolved."""

    def tokens(self) -> tuple[Token, ...]:
        """All tokens, in file and document order."""
        ...

    def get(self, path: str) -> Token:
        """One token by dotted path; KeyError names the path when it does not exist."""
        ...

    def hex(self, path: str) -> str:
        """A colour token as lower-case `#rrggbb` (or `#rrggbbaa` when not opaque)."""
        ...

    def group(self, prefix: str) -> tuple[Token, ...]:
        """Every token whose path starts with `prefix.`, in order."""
        ...


class ContrastAuditInterface(Protocol):
    """Measures every pair `design/contrast.json` declares, in every theme it names."""

    def results(self) -> tuple[ContrastResult, ...]:
        """One result per theme, rule, foreground and background."""
        ...


class EmitterInterface(Protocol):
    """Turns the token set into files for one platform."""

    def outputs(self) -> dict[Path, bytes]:
        """Repository-relative path to the exact bytes that belong there."""
        ...


class DesignGeneratorInterface(Protocol):
    """Writes every emitter's outputs, or reports where the tree has drifted from them."""

    def write(self) -> list[Path]:
        """Write every output whose bytes differ; return the paths written."""
        ...

    def check(self) -> list[str]:
        """One human-readable problem per missing or stale output; empty when in sync."""
        ...
