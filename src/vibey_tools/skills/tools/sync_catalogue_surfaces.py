#!/usr/bin/env python3
# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Synchronize machine-derived plugin and skill counts across catalogue surfaces.

The marketplace tree is the source of truth.  Overview pages, documentation
configuration, packaging metadata, and the root plugin table are derived
surfaces; keeping their counts and plugin rows current by hand is exactly the
kind of release toil that caused the catalogue to drift.

Run with ``--check`` in CI to detect drift, or ``--write`` after adding or
removing a plugin/skill to update the declared surfaces.  Historical research
counts are left alone when a line marks itself with ``counts:historical``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGINS = ROOT / "plugins"
MANIFEST = ROOT / ".claude-plugin" / "marketplace.json"
HISTORICAL = "counts:historical"

# These are the surfaces that make present-tense claims about the marketplace.
# The research paper and explorer fixtures deliberately describe historical
# measurements and are not generated from the live catalogue.
SURFACES = (
    "README.md",
    "CLAUDE.md",
    "AGENTS.md",
    "CONTRIBUTING.md",
    "pyproject.toml",
    "mkdocs.yml",
    "properdocs.yml",
    "docs/index.md",
    "docs/usage.md",
    "docs/rag-context-engine-plan.md",
    ".claude/skills/README.md",
    ".agents/skills/README.md",
    ".claude-plugin/marketplace.json",
)

COUNT_PLUGIN = re.compile(r"(?<![\d])\d{2,4}(?=\s+plugins\b)", re.IGNORECASE)
COUNT_SKILL = re.compile(
    r"(?<![\d])\d{2,4}(?=\s+(?:Agent |long-form |evidence-grounded practitioner )?[Ss]kills?\b|\s+SKILL\.md\b|\s+pages\b|\s+evidence-grounded practitioner\b)",
    re.IGNORECASE,
)

# One row of the root README plugin table.  The row's URL and prose remain
# human-authored; version and skill count come from the manifest and tree.
README_ROW = re.compile(
    r"^(?P<before>\| \[([a-z0-9-]+)\]\([^)]+\) \| )"
    r"(?P<version>[^|]+?)(?P<middle>\s+\|\s+[^|]+?\s+\|\s+)"
    r"(?P<count>\d+)(?P<after>\s+\|.*)$"
)


def _counts() -> tuple[int, int, dict[str, dict[str, object]], dict[str, int]]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries = {item["name"]: item for item in manifest["plugins"]}
    actual: dict[str, int] = {}
    for plugin_dir in sorted(PLUGINS.iterdir()):
        if not plugin_dir.is_dir() or plugin_dir.name.startswith("."):
            continue
        actual[plugin_dir.name] = sum(1 for path in (plugin_dir / "skills").glob("*/SKILL.md"))
    missing = sorted(set(actual) - set(entries))
    absent = sorted(set(entries) - set(actual))
    if missing or absent:
        raise ValueError(
            f"marketplace/tree mismatch: unlisted={missing or 'none'}, missing={absent or 'none'}"
        )
    return len(entries), sum(actual.values()), entries, actual


def _sync_counts(text: str, plugin_count: int, skill_count: int) -> str:
    lines: list[str] = []
    for line in text.splitlines(keepends=True):
        if HISTORICAL not in line:
            line = COUNT_PLUGIN.sub(str(plugin_count), line)
            line = COUNT_SKILL.sub(str(skill_count), line)
        lines.append(line)
    return "".join(lines)


def _sync_readme_table(
    text: str, entries: dict[str, dict[str, object]], actual: dict[str, int]
) -> str:
    lines: list[str] = []
    for line in text.splitlines(keepends=True):
        match = README_ROW.match(line.rstrip("\r\n"))
        if not match:
            lines.append(line)
            continue
        name = match.group(2)
        if name not in entries:
            lines.append(line)
            continue
        entry = entries[name]
        version = str(entry.get("version", ""))
        count = str(actual[name])
        body = line.rstrip("\r\n")
        newline = line[len(body) :]
        updated = (
            body[: match.start("version")]
            + version
            + body[match.end("version") : match.start("count")]
            + count
            + body[match.end("count") :]
        )
        lines.append(updated + newline)
    return "".join(lines)


def desired_files() -> list[Path]:
    return [ROOT / relative for relative in SURFACES]


def plan() -> tuple[int, int, list[tuple[Path, str, str]]]:
    plugin_count, skill_count, entries, actual = _counts()
    changes: list[tuple[Path, str, str]] = []
    for path in desired_files():
        if not path.exists():
            continue
        original = path.read_text(encoding="utf-8")
        updated = _sync_counts(original, plugin_count, skill_count)
        if path.name == "README.md" and path.parent == ROOT:
            updated = _sync_readme_table(updated, entries, actual)
        if updated != original:
            changes.append((path, original, updated))
    return plugin_count, skill_count, changes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="fail when derived surfaces are stale")
    mode.add_argument("--write", action="store_true", help="update stale derived surfaces")
    args = parser.parse_args(argv)
    try:
        plugin_count, skill_count, changes = plan()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"catalogue synchronization failed: {exc}", file=sys.stderr)
        return 1

    print(f"catalogue: {plugin_count} plugins, {skill_count} skills")
    if not changes:
        print("catalogue surfaces are synchronized")
        return 0
    for path, _, _ in changes:
        print(f"stale: {path.relative_to(ROOT)}")
    if args.write:
        for path, _, updated in changes:
            path.write_text(updated, encoding="utf-8")
        print(f"updated {len(changes)} catalogue surface(s)")
        return 0
    print("run this command with --write to update them", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
