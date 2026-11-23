# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam over a SKILL.md's frontmatter (SP-LOOPS Task 4)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable


@runtime_checkable
class SkillFrontmatterInterface(Protocol):
    def parse(self, text: str) -> Mapping[str, str]:
        """The top-level keys of the `---`-fenced block that opens `text`, each as a string.
        Raises `FrontmatterError` with a reason for anything it cannot read."""
        ...
