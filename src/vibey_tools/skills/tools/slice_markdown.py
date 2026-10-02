#!/usr/bin/env python3
# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Deterministically convert a Markdown surface into linked microslices."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class Slice:
    id: str
    purpose: str
    source: str
    output: str
    requires: tuple[str, ...]
    links: tuple[str, ...]


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "slice"


def _id(source: Path, heading: str, ordinal: int) -> str:
    digest = hashlib.sha256(f"{source.as_posix()}\0{heading}\0{ordinal}".encode()).hexdigest()[:10]
    return f"{_slug(source.stem)}-{_slug(heading)}-{digest}"


# A fenced code block by CommonMark 0.31's rule (section 4.5): an opener is a run of three
# or more backticks or tildes indented at most three columns, and a backtick opener's info
# string holds no backtick; only a line holding nothing but a run of the SAME character, at
# least as long, indented at most three columns, closes it.
_FENCE_OPEN = re.compile(r" {0,3}(?P<run>`{3,}|~{3,})(?P<info>.*)$")
_FENCE_CLOSE = re.compile(r" {0,3}(?P<run>`{3,}|~{3,}) *$")


def _headings(text: str, level: int) -> list[tuple[int, str]]:
    """(offset, title) of each level-`level` ATX heading at the start of a line, outside
    fenced code.

    The split used to be a bare regex over the whole text, so a `## ` line inside a fence
    -- a SKILL.md showing the skeleton of another SKILL.md -- cut the fence in two, and eight
    generated slices opened a code block they never closed (the documentation deep scan
    found them, 2026-10-02). This applies the same CommonMark fence rule as
    `vibey_gh.markdown_fences`, which it cannot import: vibey-skills declares no
    dependencies, its CI job installs it alone, and the converter runs as a bare
    `python3` script. Containers are not followed, and need not be for a heading that
    starts its line: column 0 ends any block quote or list item, and a fence with it.

    Module-level for the same reason as the rest of this script (vibey ADR-0016): it is a
    standalone tool, loaded by path, whose functions its tests call by name.
    """
    heading = re.compile(rf"({'#' * level})[ \t]+(.+?)\s*$")
    found: list[tuple[int, str]] = []
    fence: str | None = None
    offset = 0
    for line in text.splitlines(keepends=True):
        bare = line.rstrip("\r\n").expandtabs(4)
        if fence is not None:
            close = _FENCE_CLOSE.match(bare)
            if close and close["run"][0] == fence[0] and len(close["run"]) >= len(fence):
                fence = None
        else:
            opener = _FENCE_OPEN.match(bare)
            if opener and not (opener["run"][0] == "`" and "`" in opener["info"]):
                fence = opener["run"]
            else:
                match = heading.match(line.rstrip("\r\n"))
                if match:
                    found.append((offset, match.group(2)))
        offset += len(line)
    return found


def slice_markdown(source: Path, destination: Path, level: int = 2) -> list[Slice]:
    text = source.read_text(encoding="utf-8")
    matches = _headings(text, level)
    if not matches:
        raise ValueError(f"no level-{level} headings found in {source}")
    chunks = []
    for index, (start, title) in enumerate(matches):
        end = matches[index + 1][0] if index + 1 < len(matches) else len(text)
        chunks.append((title, text[start:end].strip() + "\n"))
    records: list[Slice] = []
    for index, (heading, body) in enumerate(chunks):
        slice_id = _id(source, heading, index)
        previous = records[-1].id if records else None
        following = (
            _id(source, chunks[index + 1][0], index + 1) if index + 1 < len(chunks) else None
        )
        requires = (previous,) if previous else ()
        links = (following,) if following else ()
        output = destination / f"{index + 1:03d}-{_slug(heading)}.md"
        output.parent.mkdir(parents=True, exist_ok=True)
        header = (
            "---\n"
            f"id: {slice_id}\n"
            f"purpose: {_slug(heading).replace('-', ' ')}\n"
            f"source: {source.as_posix()}\n"
            f"requires: {json.dumps(list(requires))}\n"
            f"links: {json.dumps(list(links))}\n"
            "---\n\n"
        )
        output.write_text(header + body, encoding="utf-8")
        records.append(
            Slice(
                slice_id,
                _slug(heading).replace("-", " "),
                source.as_posix(),
                output.as_posix(),
                requires,
                links,
            )
        )
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "index.json").write_text(
        json.dumps([asdict(record) for record in records], indent=2) + "\n", encoding="utf-8"
    )
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, nargs="?")
    parser.add_argument("destination", type=Path, nargs="?")
    parser.add_argument(
        "--all-root", type=Path, help="recursively convert every SKILL.md below this root"
    )
    parser.add_argument("--all-output", type=Path, help="output root for --all-root")
    parser.add_argument("--level", type=int, choices=(1, 2, 3), default=2)
    args = parser.parse_args()
    if bool(args.all_root) != bool(args.all_output):
        parser.error("--all-root and --all-output must be provided together")
    if args.all_root:
        manifest: list[dict[str, object]] = []
        for source in sorted(args.all_root.glob("*/skills/*/SKILL.md")):
            relative = source.relative_to(args.all_root).parent
            destination = args.all_output / relative
            records = slice_markdown(source, destination, args.level)
            manifest.append(
                {
                    "source": source.as_posix(),
                    "output": destination.as_posix(),
                    "count": len(records),
                }
            )
        args.all_output.mkdir(parents=True, exist_ok=True)
        (args.all_output / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        print(f"wrote {len(manifest)} skill manifests")
        return 0
    if not args.source or not args.destination:
        parser.error("source and destination are required unless --all-root is used")
    print(f"wrote {len(slice_markdown(args.source, args.destination, args.level))} microslices")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
