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


def slice_markdown(source: Path, destination: Path, level: int = 2) -> list[Slice]:
    text = source.read_text(encoding="utf-8")
    matches = list(re.finditer(rf"^({'#' * level})\s+(.+?)\s*$", text, re.MULTILINE))
    if not matches:
        raise ValueError(f"no level-{level} headings found in {source}")
    chunks = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        chunks.append((match.group(2), text[match.start() : end].strip() + "\n"))
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
