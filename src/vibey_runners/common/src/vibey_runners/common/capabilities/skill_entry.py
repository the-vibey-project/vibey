# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One skill: the plugin that holds it, its frontmatter name and description, and its SKILL.md
(resolved, inside its plugin). The body is not read here -- design Decision 10 loads names and
descriptions up front and bodies on demand. A record with no behaviour, so no seam of its own."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SkillEntry:
    plugin: str
    name: str
    description: str
    path: Path
