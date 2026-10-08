# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Publish every project's public ledger to the explorer, scrubbed by the publication policy.

    uv run python scripts/explorer_publish.py                 # write docs/explorer/data/
    uv run python scripts/explorer_publish.py --out DIR       # write somewhere else, to review

For each project in the database this runs the same path `vibey ledger export` and `vibey
ledger site` take: the default-deny publication policy (sub-doctrine 7.a) keeps the decisions,
questions, answers, findings and phase changes, withholds engine chatter, spend and anything
from outside, strips local paths, email addresses and credentials, and counts all of it; the
static site builder then writes `manifest.json`, `index.json` and one document per record. The
registry (`projects.json`) lists every published project with its counts, so the explorer can
offer a chooser, and it keeps the entries this script does not own (the labelled sample and the
sealed private copy).

Nothing here decrypts anything. The sensitive remainder stays in the sealed copy `vibey state
sync` keeps on the `vibey-state` branch, and the explorer opens it, in the browser, only for
someone who holds the key. Re-running is idempotent: the same database and policy write the same
bytes, and a project that no longer has public records leaves the site.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import shutil
import sys
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from vibey.application.ledger_publication import LedgerExporter, LedgerSiteBuilder  # noqa: E402
from vibey.bootstrap import build_app  # noqa: E402
from vibey.cli.ledger_publication import PUBLIC_POLICY, SHARD_STORE, SITE_WRITER  # noqa: E402
from vibey.domain.ledger_chain import LEDGER_CHAIN  # noqa: E402

DEFAULT_OUT = REPO / "docs" / "explorer" / "data"
CONFIG = REPO / "scripts" / "explorer_publish.toml"
REGISTRY = "projects.json"


@dataclass(frozen=True, slots=True)
class PublishedProject:
    slug: str
    name: str
    project_id: str
    phase: str
    updated: str
    events: int
    records: int
    withheld: int


class Slugs:
    """A stable, URL-safe name for each project: its own name, or the name and the id's head."""

    _UNSAFE = re.compile(r"[^a-z0-9]+")

    def __init__(self) -> None:
        self._taken: set[str] = set()

    def of(self, name: str, project_id: str) -> str:
        base = self._UNSAFE.sub("-", name.lower()).strip("-") or "project"
        slug = base if base not in self._taken else f"{base}-{project_id[:8]}"
        self._taken.add(slug)
        return slug


class ExplorerPublisher:
    """Exports every project through the policy and writes the explorer's data and registry."""

    def __init__(
        self, *, builder: LedgerSiteBuilder | None = None, exclude: Sequence[str] | None = None
    ) -> None:
        self._builder = builder or LedgerSiteBuilder(store=SHARD_STORE, writer=SITE_WRITER)
        declared = tomllib.loads(CONFIG.read_text(encoding="utf-8"))["explorer_publish"]
        self._exclude = [
            re.compile(rx) for rx in (declared["exclude_names"] if exclude is None else exclude)
        ]

    async def publish(self, out: Path) -> Sequence[PublishedProject]:
        out.mkdir(parents=True, exist_ok=True)
        published: list[PublishedProject] = []
        slugs = Slugs()
        async with build_app() as resources:
            exporter = LedgerExporter(
                ledger=resources.ledger, store=SHARD_STORE, policy=PUBLIC_POLICY, chain=LEDGER_CHAIN
            )
            for project in sorted(await resources.projects.list_all(), key=lambda p: p.name):
                if any(rx.search(project.name) for rx in self._exclude):
                    continue
                slug = slugs.of(project.name, str(project.project_id))
                target = out / slug
                target.mkdir(parents=True, exist_ok=True)
                shard_path = target / "shard.jsonl"
                shard = await exporter.export(project.project_id, project.name, shard_path)
                if shard.header.published_count == 0:
                    shutil.rmtree(target)  # nothing public: it leaves the site, as the policy says
                    continue
                self._builder.build(shard_path, target)
                published.append(
                    PublishedProject(
                        slug=slug,
                        name=project.name,
                        project_id=str(project.project_id),
                        phase=project.phase.value
                        if hasattr(project.phase, "value")
                        else str(project.phase),
                        updated=project.updated_at.isoformat(),
                        events=shard.header.ledger_event_count,
                        records=shard.header.published_count,
                        withheld=shard.header.events_withheld,
                    )
                )
        self._forget_unpublished(out, {p.slug for p in published})
        self._write_registry(out, published)
        return published

    @staticmethod
    def _forget_unpublished(out: Path, keep: set[str]) -> None:
        registry = out / REGISTRY
        if not registry.exists():
            return
        for entry in json.loads(registry.read_text(encoding="utf-8")).get("projects", []):
            if "project_id" in entry and entry["id"] not in keep and (out / entry["id"]).is_dir():
                shutil.rmtree(out / entry["id"])

    @staticmethod
    def _write_registry(out: Path, published: Sequence[PublishedProject]) -> None:
        registry = out / REGISTRY
        existing = (
            json.loads(registry.read_text(encoding="utf-8"))
            if registry.exists()
            else {"projects": []}
        )
        # What this script does not own: the labelled sample and the sealed private copy.
        others = [e for e in existing.get("projects", []) if "project_id" not in e]
        mine = [
            {
                "id": p.slug,
                "label": p.name,
                "project_id": p.project_id,
                "stats": {
                    "phase": p.phase,
                    "updated": p.updated,
                    "events": p.events,
                    "records": p.records,
                    "withheld": p.withheld,
                },
            }
            for p in sorted(published, key=lambda p: p.updated, reverse=True)
        ]
        document = {"projects": mine + others}
        registry.write_text(
            json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )


# A bare function because it is this script's `__main__` entry point (ADR-0016).
def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="where to write (default: the explorer's data)",
    )
    args = parser.parse_args(argv)
    published = asyncio.run(ExplorerPublisher().publish(args.out))
    total = sum(p.records for p in published)
    hidden = sum(p.withheld for p in published)
    print(
        f"published {len(published)} project(s): {total} public record(s); {hidden} event(s) withheld by policy -> {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
