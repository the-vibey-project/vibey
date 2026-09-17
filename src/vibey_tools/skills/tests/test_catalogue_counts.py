# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The catalogue counts this repository states about itself must be true.

Every doc surface here advertises how many plugins and how many skills the marketplace
holds. Those numbers are written by hand in a dozen places and are wrong the moment a
plugin lands, so they drift silently and in generations: before this test existed the tree
simultaneously claimed 127/644 (mkdocs, properdocs, the agent-surface READMEs, the docs
site), 130/665 (README, CLAUDE.md, AGENTS.md, CONTRIBUTING.md, pyproject) and 131/672
(reality). A reader cannot tell which generation they are looking at, and a marketplace
whose own front page miscounts its contents undermines every other claim on the page.

The fix is not to remember harder. It is to make the build fail.

`docs/paper.md` is deliberately excluded: it reports `n = 644 skill documents` as the
corpus size of a specific retrieval evaluation, which is a dated research measurement
rather than a claim about the marketplace as it stands today. Changing it would falsify
the paper, not correct it.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# A line may state a count that was true at some past moment — the 2.0.0 rename note, for
# instance, records that 18 plugins and 71 skills carried over from vibe-engineering-skills.
# Marking it is better than widening the patterns, because the marker says out loud that the
# number is history and must NOT be updated when the catalogue grows.
HISTORICAL = "counts:historical"

# Surfaces that state a count about the marketplace *as it is now*.
SURFACES = (
    "README.md",
    "CLAUDE.md",
    "AGENTS.md",
    "CONTRIBUTING.md",
    "pyproject.toml",
    ".vibey-gh.toml",
    ".github/workflows/repository-profile.yml",
    "mkdocs.yml",
    "properdocs.yml",
    "docs/index.md",
    "docs/usage.md",
    "docs/rag-context-engine-plan.md",
    ".claude/skills/README.md",
    ".agents/skills/README.md",
)

# A number immediately followed by a noun that can only mean "plugins in this marketplace".
PLUGIN_CLAIMS = (
    re.compile(r"(\d{2,4})\s+(?:Claude Code\s+|Codex\s+)?plugins\b"),
    re.compile(r"across\s+(\d{2,4})\b"),
)

# A number immediately followed by a noun that can only mean "skills in this marketplace".
SKILL_CLAIMS = (
    re.compile(r"(\d{2,4})\s+(?:Agent |long-form |evidence-grounded practitioner )?[Ss]kills?\b"),
    re.compile(r"(\d{2,4})\s+evidence-grounded practitioner\b"),
    re.compile(r"(\d{2,4})\s+SKILL\.md\b"),
    re.compile(r"(\d{2,4})\s+pages\b"),
    re.compile(r"(\d{2,4})-document skill corpus\b"),
)


def _true_counts() -> tuple[int, int]:
    manifest = json.loads(
        (ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
    )
    plugins = len(manifest["plugins"])
    skills = len(list(ROOT.glob("plugins/*/skills/*/SKILL.md")))
    return plugins, skills


class CatalogueCountTests(unittest.TestCase):
    def test_the_manifest_lists_every_plugin_directory(self) -> None:
        manifest = json.loads(
            (ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
        )
        listed = {p["name"] for p in manifest["plugins"]}
        on_disk = {p.parent.parent.name for p in ROOT.glob("plugins/*/.claude-plugin/plugin.json")}
        self.assertEqual(
            listed,
            on_disk,
            "marketplace.json and plugins/ disagree about which plugins exist",
        )

    def test_every_stated_plugin_count_is_true(self) -> None:
        plugins, _ = _true_counts()
        wrong: list[str] = []
        for name in SURFACES:
            path = ROOT / name
            if not path.exists():
                continue
            for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if HISTORICAL in line:
                    continue
                for pattern in PLUGIN_CLAIMS:
                    for claim in pattern.findall(line):
                        if int(claim) != plugins:
                            wrong.append(f"{name}:{line_no} says {claim} plugins, not {plugins}")
        self.assertEqual(wrong, [], "stale plugin counts:\n  " + "\n  ".join(wrong))

    def test_every_stated_skill_count_is_true(self) -> None:
        _, skills = _true_counts()
        wrong: list[str] = []
        for name in SURFACES:
            path = ROOT / name
            if not path.exists():
                continue
            for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if HISTORICAL in line:
                    continue
                for pattern in SKILL_CLAIMS:
                    for claim in pattern.findall(line):
                        if int(claim) != skills:
                            wrong.append(f"{name}:{line_no} says {claim} skills, not {skills}")
        self.assertEqual(wrong, [], "stale skill counts:\n  " + "\n  ".join(wrong))

    def test_the_readme_table_lists_every_plugin_accurately(self) -> None:
        """CONTRIBUTING.md step 3 for a new plugin: add a row to the root README table.

        Nothing enforced that, so the table drifted exactly as the counts did — it carried
        127 rows against 131 plugins, missing every pack added after the table was last
        rebuilt by hand. The row also states version, category and skill count, and
        CONTRIBUTING requires those to stay accurate, so all three are checked here rather
        than only membership.
        """
        manifest = json.loads(
            (ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
        )
        entries = {p["name"]: p for p in manifest["plugins"]}
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        row = re.compile(r"^\| \[([a-z0-9-]+)\]\([^)]+\) \| ([^|]+?) \| ([^|]+?) \| (\d+) \|", re.M)
        rows = {
            m.group(1): (m.group(2).strip(), m.group(3).strip(), int(m.group(4)))
            for m in row.finditer(readme)
        }

        self.assertEqual(
            sorted(set(entries) - set(rows)),
            [],
            "plugins missing a row in the README table (CONTRIBUTING.md step 3)",
        )
        self.assertEqual(
            sorted(set(rows) - set(entries)),
            [],
            "README table lists plugins that are not in the marketplace",
        )

        wrong: list[str] = []
        for name, (version, category, skill_count) in sorted(rows.items()):
            entry = entries[name]
            actual = len(list(ROOT.glob(f"plugins/{name}/skills/*/SKILL.md")))
            if version != entry["version"]:
                wrong.append(f"{name}: table says v{version}, manifest says v{entry['version']}")
            if category != entry.get("category"):
                wrong.append(
                    f"{name}: table says {category}, manifest says {entry.get('category')}"
                )
            if skill_count != actual:
                wrong.append(f"{name}: table says {skill_count} skills, tree has {actual}")
        self.assertEqual(
            wrong, [], "README table disagrees with the tree:\n  " + "\n  ".join(wrong)
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
