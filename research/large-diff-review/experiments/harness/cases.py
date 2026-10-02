"""Review cases: a host diff (large, real), a needle case (host + one canary defect), and
the canary's own small cases -- each with the documents and reference sources production
would hand the review.
"""

from __future__ import annotations

import functools
import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from corpus import CANARY_CORPUS, CORPUS, DOC_PATHS, ROOT, DiffSections, Git, Section, Triage

MAX_SOURCE_FILE_BYTES = 1_000_000


@dataclass
class Case:
    case_id: str
    kind: str  # host | needle | canary-defect | canary-control
    diff: str
    documents: dict[str, str]
    sources: dict[str, str]
    host: int | None = None
    needle: str = ""
    position: str = ""
    insert_at: int = -1  # section index the needle was inserted before (host order)
    built: Any = None  # the canary BuiltCase, for the matcher
    keywords: tuple[str, ...] = ()
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def is_defect(self) -> bool:
        return self.kind in ("needle", "canary-defect")


class CaseBook:
    """Builds every case the study reviews, from git objects only."""

    def __init__(self) -> None:
        self.git = Git()
        self.sections = DiffSections()
        self.triage = Triage()
        self.hosts = {
            r["number"]: r for r in json.loads((CORPUS / "hosts.json").read_text())["rows"]
        }
        self.selection = json.loads((CORPUS / "selection.json").read_text())
        from vibey_gh.review_canary import CorpusLoader

        self.loader = CorpusLoader(ROOT)
        self.canary = self.loader.load(CANARY_CORPUS)
        self.canary_raw = tomllib.loads(CANARY_CORPUS.read_text())

    @functools.lru_cache(maxsize=64)  # noqa: B019 - one book per run
    def host(self, number: int) -> Case:
        row = self.hosts[number]
        merge = row["merge_commit"]
        diff = self.git.diff(merge)
        documents = {p: t for p in DOC_PATHS if (t := self.git.show(merge, p)) is not None}
        sources: dict[str, str] = {}
        for section in self.sections.split(diff):
            if "\ndeleted file mode" in section.text[:400]:
                continue
            text = self.git.show(merge, section.path)
            if text is None or len(text.encode()) > MAX_SOURCE_FILE_BYTES or "\x00" in text:
                continue
            sources[section.path] = text
        return Case(
            f"host-{number}",
            "host",
            diff,
            documents,
            sources,
            host=number,
            meta={"merge": merge, "chars": len(diff)},
        )

    def canary_case(self, case_id: str) -> Case:
        case = next(c for c in self.canary.cases if c.id == case_id)
        built = self.loader.build(self.canary, case)
        keywords = self.canary.classes[case.defect_class].keywords if case.is_defect else ()
        # The canary's documents: the same two declared pages, at the canary's pin.
        documents = {
            p: t for p in DOC_PATHS if (t := self.git.show(self.canary.pin, p)) is not None
        }
        return Case(
            case_id,
            "canary-defect" if case.is_defect else "canary-control",
            built.diff,
            documents,
            {case.path: built.after},
            built=built,
            keywords=tuple(keywords),
            meta={"class": case.defect_class, "path": case.path},
        )

    def insertion_index(self, sections: list[Section], fraction: float) -> int:
        total = sum(len(s.text) for s in sections)
        offset = 0
        for index, section in enumerate(sections):
            if offset >= fraction * total:
                return index
            offset += len(section.text)
        return len(sections)

    def needle_case(self, number: int, needle_id: str, position: str) -> Case | None:
        host = self.host(number)
        needle = self.canary_case(needle_id)
        sections = self.sections.split(host.diff)
        if any(s.path == needle.meta["path"] for s in sections):
            return None  # the host already changes the needle's file
        fraction = dict(self.selection["positions"].items())[position]
        at = self.insertion_index(sections, fraction)
        needle_section = needle.diff if needle.diff.endswith("\n") else needle.diff + "\n"
        diff = (
            "".join(s.text for s in sections[:at])
            + needle_section
            + "".join(s.text for s in sections[at:])
        )
        sources = dict(host.sources)
        sources.update(needle.sources)
        return Case(
            f"needle-{number}-{needle_id}-{position}",
            "needle",
            diff,
            host.documents,
            sources,
            host=number,
            needle=needle_id,
            position=position,
            insert_at=at,
            built=needle.built,
            keywords=needle.keywords,
            meta={
                "class": needle.meta["class"],
                "path": needle.meta["path"],
                "needle_section": needle_section,
            },
        )

    def needle_plan(
        self, hosts: list[int], needles: list[str], positions=("early", "middle", "late")
    ) -> list[tuple[int, str, str]]:
        """Round-robin needles over (host, position) slots, skipping a needle whose file the
        host already changes (the next needle in order is used)."""
        plan, i = [], 0
        for number in hosts:
            for position in positions:
                for _ in range(len(needles)):
                    needle = needles[i % len(needles)]
                    i += 1
                    if self.needle_case(number, needle, position) is not None:
                        plan.append((number, needle, position))
                        break
        return plan


def as_json(case: Case) -> dict[str, Any]:
    return {
        "case_id": case.case_id,
        "kind": case.kind,
        "host": case.host,
        "needle": case.needle,
        "position": case.position,
        "chars": len(case.diff),
        "insert_at": case.insert_at,
    }


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(ROOT / "src" / "vibey_tools" / "gh"))
    book = CaseBook()
    h = book.host(1131)
    print(h.case_id, len(h.diff), len(h.sources), sum(map(len, h.sources.values())))
    plan = book.needle_plan(
        book.selection["halving_hosts_s2"],
        book.selection["dev_needles"],
        positions=("early", "late"),
    )
    print(plan)
    print(Path(__file__).name, "ok")
