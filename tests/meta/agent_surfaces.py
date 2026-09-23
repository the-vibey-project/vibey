# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Test data for agent surface trees.

This module declares the layout and expected contents for the agent surface
trees used by :mod:`tests.meta.test_agent_tree_parity`.  It is a plain data
module – no executable code other than type declarations – so that the
corresponding test functions can import it without side effects.

The definitions are intentionally concise and documented so that the test
logic can remain focused on the parity checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

__all__ = [
    "TreeLayout",
    "SkillTree",
    "SOURCE_TREE",
    "AGENT_SURFACE_TREES",
    "SD01_RULE_STEM",
    "STANDING_RULE_STEMS",
]


class TreeLayout(StrEnum):
    """Enumerates the structural layout of a skill tree.

    ``SKILL_DIRECTORIES`` refers to a directory per skill; the file
    ``SKILL.md`` inside that directory contains the skill content.

    ``RULE_FILES`` refers to a single file per skill (or rule) located in a
    root directory; the file name ends with the supplied ``suffix``.
    """

    SKILL_DIRECTORIES = "skill-directories"
    RULE_FILES = "rule-files"


@dataclass(frozen=True, slots=True)
class SkillTree:
    """Defines the layout and metadata of a skill or rule tree.

    Parameters
    ----------
    root:
        Repository‑relative directory for the tree.
    layout:
        :class:`TreeLayout` describing the directory/file structure.
    suffix:
        File suffix for ``RULE_FILES`` trees or the literal ``"SKILL.md"`` for
        ``SKILL_DIRECTORIES`` trees.
    front_matter:
        ``True`` if files contain a YAML front‑matter block.
    mirror_line:
        If present, the first line of the body must equal
        ``mirror_line.format(name=<skill name>)``.  The line is discarded when
        comparing bodies.
    always_apply:
        Optional front‑matter directive that is only relevant for
        :class:`RuleFiles` trees used by :mod:`gap-sd01-carriage`.
    """

    root: str
    layout: TreeLayout
    suffix: str
    front_matter: bool
    mirror_line: str | None
    always_apply: str | None = None


# ---------- Concrete tree definitions ----------------------------------

CURSOR_MIRROR = (
    "> **Cursor rule mirror** of `.claude/skills/{name}/SKILL.md`. "
    "When this guidance changes, update Claude, Cursor, Codex, and Antigravity in the same PR."
)

SOURCE_TREE: Final[SkillTree] = SkillTree(
    root=".claude/skills",
    layout=TreeLayout.SKILL_DIRECTORIES,
    suffix="SKILL.md",
    front_matter=True,
    mirror_line=None,
)

AGENT_SURFACE_TREES: Final[tuple[SkillTree, ...]] = (
    SOURCE_TREE,
    SkillTree(
        root=".agents/skills",
        layout=TreeLayout.SKILL_DIRECTORIES,
        suffix="SKILL.md",
        front_matter=True,
        mirror_line=None,
    ),
    SkillTree(
        root=".cursor/rules",
        layout=TreeLayout.RULE_FILES,
        suffix=".mdc",
        front_matter=True,
        mirror_line=CURSOR_MIRROR,
        always_apply="alwaysApply: true",
    ),
    SkillTree(
        root=".agent/rules",
        layout=TreeLayout.RULE_FILES,
        suffix=".md",
        front_matter=False,
        mirror_line="# {name} (Antigravity mirror of `.claude/skills/{name}/SKILL.md`)",
    ),
)

# SD‑01 rule that is treated as a standing rule.
SD01_RULE_STEM: Final[str] = "sd-01-counterparties-trust-verification"
STANDING_RULE_STEMS: Final[frozenset[str]] = frozenset({SD01_RULE_STEM})
"""
End of module ``tests.meta.agent_surfaces``.
"""
