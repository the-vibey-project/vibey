# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Meta tests for agent surface parity.

This file contains a set of lightweight tests that verify the four
agent‑surface trees defined in :mod:`tests.meta.agent_surfaces` are in
perfect sync with the source tree.  The tests are intentionally very
simple – they read the files from disk, extract the body (optionally
ignoring any YAML front‑matter) and perform byte‑by‑byte comparisons.

The goal is to keep the test logic in one place and to avoid relying on
external libraries for parsing.  The implementation follows the
specification from issue #492.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from .agent_surfaces import AGENT_SURFACE_TREES, SkillTree, TreeLayout

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]


def _list_source_skills() -> list[str]:
    path = REPO_ROOT / ".claude/skills"
    return sorted([p.name for p in path.iterdir() if (p / "SKILL.md").is_file()])


def _read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_body(text: str, has_front_matter: bool) -> str:
    if not has_front_matter:
        return text.lstrip("\n")
    # Split on the first closing "---"
    parts = text.split("\n---\n", 1)
    if len(parts) == 1:
        # No closing marker found – treat body as entire file
        return parts[0].lstrip("\n")
    body = parts[1]
    return body.lstrip("\n")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_source_tree_first():
    tree = AGENT_SURFACE_TREES[0]
    assert tree.root == ".claude/skills"
    assert _list_source_skills()


@pytest.mark.parametrize("tree", AGENT_SURFACE_TREES[1:], ids=lambda t: t.root)
def test_each_tree_has_exactly_source_skills(tree: SkillTree):
    source = set(_list_source_skills())
    path = REPO_ROOT / tree.root
    if tree.layout is TreeLayout.SKILL_DIRECTORIES:
        tree_names = {p.name for p in path.iterdir() if (p / "SKILL.md").is_file()}
    else:
        # rule files – ignore standing rule stems
        stems = {p.stem for p in path.iterdir() if p.is_file() and p.suffix == tree.suffix}
        tree_names = {s for s in stems if s not in {"sd-01-counterparties-trust-verification"}}
    assert tree_names == source, f"{tree.root} differs from source"


@pytest.mark.parametrize(
    "tree,skill", [(t, s) for t in AGENT_SURFACE_TREES[1:] for s in _list_source_skills()]
)
def test_body_parity(tree: SkillTree, skill: str):
    src_path = REPO_ROOT / ".claude/skills" / skill / "SKILL.md"
    src_text = _read_file(src_path)
    src_body = _extract_body(src_text, True)

    # locate mirror
    if tree.layout is TreeLayout.SKILL_DIRECTORIES:
        mir_path = REPO_ROOT / tree.root / skill / "SKILL.md"
    else:
        mir_path = REPO_ROOT / tree.root / f"{skill}{tree.suffix}"
    mir_text = _read_file(mir_path)
    mir_body = _extract_body(mir_text, tree.front_matter)

    if tree.mirror_line:
        # remove first line
        line, *rest = mir_body.splitlines(True)
        expected = tree.mirror_line.format(name=skill)
        assert line.rstrip("\n") == expected
        mir_body = "".join(rest).lstrip("\n")

    assert src_body == mir_body, f"Body mismatch for {skill} in {tree.root}"


@pytest.mark.parametrize("tree", [t for t in AGENT_SURFACE_TREES[1:] if t.front_matter])
def test_description_parity(tree: SkillTree):
    for skill in _list_source_skills():
        src_path = REPO_ROOT / ".claude/skills" / skill / "SKILL.md"
        src_text = _read_file(src_path)
        src_desc = _parse_front(src_text).get("description")

        if tree.layout is TreeLayout.SKILL_DIRECTORIES:
            mir_path = REPO_ROOT / tree.root / skill / "SKILL.md"
        else:
            mir_path = REPO_ROOT / tree.root / f"{skill}{tree.suffix}"
        mir_text = _read_file(mir_path)
        mir_desc = _parse_front(mir_text).get("description")
        assert src_desc == mir_desc, f"Desc mismatch for {skill} in {tree.root}"


def _parse_front(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or not lines[0].startswith("---"):
        return {}
    front = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line:
            k, v = line.split(":", 1)
            front[k.strip()] = v.strip()
    return front


"""End of meta tests"""
