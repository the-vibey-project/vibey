"""Corpus construction for the large-diff sovereign review study.

Research code, not shipping code: it lives under research/ and is never imported by the
package. Every case is rebuilt from git objects named in the manifest, so the corpus can be
reconstructed byte for byte from a full clone (see corpus/MANIFEST.md).

Run:  PYTHONPATH=src/vibey_tools/gh python3 research/large-diff-review/experiments/harness/corpus.py <command>
"""

from __future__ import annotations

import dataclasses
import fnmatch
import hashlib
import json
import random
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
EXP = ROOT / "research" / "large-diff-review" / "experiments"
CORPUS = EXP / "corpus"
PR_LIST = CORPUS / "raw" / "merged-prs-2026-09-25..2026-10-01.json"
SPLIT_SEED = 20261001
DOC_PATHS = ("README.md", "docs/index.md")

sys.path.insert(0, str(ROOT / "src" / "vibey_tools" / "gh"))


class Git:
    """Thin, read-only git access against the repository root."""

    def __init__(self, root: Path = ROOT) -> None:
        self.root = root

    def run(self, *args: str) -> str:
        done = subprocess.run(
            ["git", "-C", str(self.root), *args], capture_output=True, text=True, check=False
        )
        if done.returncode:
            raise RuntimeError(f"git {' '.join(args)}: {done.stderr.strip()[:300]}")
        return done.stdout

    def has(self, rev: str) -> bool:
        done = subprocess.run(
            ["git", "-C", str(self.root), "cat-file", "-t", rev], capture_output=True, text=True
        )
        return done.stdout.strip() == "commit"

    def diff(self, commit: str) -> str:
        return self.run("diff", "-M", "--no-color", "--no-ext-diff", f"{commit}^", commit)

    def show(self, commit: str, path: str) -> str | None:
        done = subprocess.run(
            ["git", "-C", str(self.root), "show", f"{commit}:{path}"],
            capture_output=True,
            check=False,
        )
        if done.returncode:
            return None
        return done.stdout.decode("utf-8", errors="replace")


@dataclasses.dataclass
class Section:
    """One file's section of a unified diff."""

    header: str  # the `diff --git` line
    text: str  # the whole section, header included
    path: str  # post-change path ('' for a deletion: then the pre-change path)
    category: str = ""

    @property
    def added(self) -> int:
        return sum(
            1 for ln in self.text.splitlines() if ln.startswith("+") and not ln.startswith("+++")
        )

    @property
    def removed(self) -> int:
        return sum(
            1 for ln in self.text.splitlines() if ln.startswith("-") and not ln.startswith("---")
        )


class DiffSections:
    """Splits a unified diff into per-file sections."""

    HEADER = re.compile(r"^diff --git a/(.+?) b/(.+)$", re.M)

    def split(self, diff: str) -> list[Section]:
        starts = [m.start() for m in self.HEADER.finditer(diff)]
        out: list[Section] = []
        for i, s in enumerate(starts):
            e = starts[i + 1] if i + 1 < len(starts) else len(diff)
            text = diff[s:e]
            m = self.HEADER.match(text)
            assert m
            a, b = m.group(1), m.group(2)
            deleted = "\ndeleted file mode" in text[:400]
            out.append(Section(text.splitlines()[0], text, a if deleted else b))
        return out

    def join(self, sections: list[Section]) -> str:
        return "".join(s.text for s in sections)


class Triage:
    """The preregistered deterministic pre-filter (PREREGISTRATION.md, arm TRI).

    Categories, first match wins:
      binary      -- 'Binary files ... differ' with no hunks
      rename      -- a pure rename/copy (similarity 100%, no hunks)
      deletion    -- every changed line is a removal (a file deleted or emptied)
      generated   -- lockfiles, minified/sourcemaps, coverage output, dist/build output,
                     vendored trees, files whose first added lines declare themselves generated
      docs        -- prose: *.md, *.mdx, *.rst, *.txt, docs/** that is not code
      code        -- everything else, including workflows, shell, config and data
    Only `code` goes to the defect review; `docs` goes to the documentation-contract
    request; the rest are summarised in one line each and checked deterministically.
    """

    GENERATED_GLOBS = (
        "*.lock",
        "uv.lock",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "poetry.lock",
        "Cargo.lock",
        "go.sum",
        "*.min.js",
        "*.min.css",
        "*.map",
        "*/coverage/*",
        "coverage/*",
        "htmlcov/*",
        "*/htmlcov/*",
        "*/dist/*",
        "dist/*",
        "*/build/*",
        "*/vendor/*",
        "vendor/*",
        "*/node_modules/*",
        "*.snap",
        "*.pb.go",
        "*_pb2.py",
        "*.svg",
        "*.png",
        "*.jpg",
        "*.ico",
        "*.pdf",
        "*.woff",
        "*.woff2",
        "*.ttf",
    )
    DOC_GLOBS = ("*.md", "*.mdx", "*.rst", "*.txt", "docs/*.html")
    GENERATED_MARKERS = (
        "@generated",
        "DO NOT EDIT",
        "do not edit",
        "autogenerated",
        "auto-generated",
    )

    def category(self, s: Section) -> str:
        t = s.text
        if "\nBinary files " in t and "\n@@" not in t:
            return "binary"
        if ("\nsimilarity index 100%" in t or "\ncopy from" in t) and "\n@@" not in t:
            return "rename"
        if "\n@@" not in t:
            return "rename"  # mode change only, or empty
        if s.added == 0 and s.removed > 0:
            return "deletion"
        p = s.path
        if any(fnmatch.fnmatch(p, g) for g in self.GENERATED_GLOBS):
            return "generated"
        head = "\n".join(ln for ln in t.splitlines()[:40] if ln.startswith("+"))
        if any(m in head for m in self.GENERATED_MARKERS):
            return "generated"
        if any(fnmatch.fnmatch(p, g) for g in self.DOC_GLOBS):
            return "docs"
        return "code"

    def label(self, sections: list[Section]) -> list[Section]:
        for s in sections:
            s.category = self.category(s)
        return sections


def production_settings() -> dict:
    from vibey_gh.config import load_config
    from vibey_gh.review_canary import ReviewCanary

    return ReviewCanary.settings(load_config())


def production_room(documents: dict[str, str], settings: dict) -> int:
    """Characters of diff ONE production request can carry beside the documents."""
    from vibey_gh import local_review as lr
    from vibey_gh.fit import ContextSizer

    sizer = ContextSizer(
        ceiling_tokens=settings["context_window"],
        reserve_tokens=settings["reasoning_reserve_tokens"],
        chars_per_token=settings["chars_per_token"],
    )
    review = lr.SovereignReview(
        "http://x",
        settings["model"],
        settings["max_diff_chars"],
        settings["timeout_seconds"],
        sizer,
        max_chunks=settings["max_chunks"],
        whole=lr.WHOLE_REVIEW,
        documents=documents,
        max_document_chars=settings["max_document_chars"],
    )
    declared, _cut, _dropped = lr.WHOLE_REVIEW.trim(documents, settings["max_document_chars"])
    return review.room(declared, part=False)


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class HostCorpus:
    """Large real diffs ('hosts'): every develop PR in the window whose diff the production
    review cannot take in one request, minus release merges, split dev/holdout by seed."""

    def __init__(self) -> None:
        self.git = Git()
        self.sections = DiffSections()
        self.triage = Triage()

    def build(self) -> dict:
        prs = json.loads(PR_LIST.read_text())
        settings = production_settings()
        rows = []
        for pr in sorted(prs, key=lambda x: x["number"]):
            row = {"number": pr["number"], "title": pr["title"], "base": pr["baseRefName"]}
            merge = (pr.get("mergeCommit") or {}).get("oid", "")
            row["merge_commit"] = merge
            if pr["baseRefName"] != "develop":
                row["excluded"] = "base is not develop (a promotion to main)"
                rows.append(row)
                continue
            if re.match(r"chore\(release\)", pr["title"]):
                row["excluded"] = "release merge"
                rows.append(row)
                continue
            if not merge or not self.git.has(merge):
                row["excluded"] = "merge commit not in the local clone"
                rows.append(row)
                continue
            diff = self.git.diff(merge)
            docs = {p: t for p in DOC_PATHS if (t := self.git.show(merge, p)) is not None}
            room = production_room(docs, settings)
            secs = self.triage.label(self.sections.split(diff))
            cats: dict[str, int] = {}
            for s in secs:
                cats[s.category] = cats.get(s.category, 0) + len(s.text)
            row.update(
                chars=len(diff),
                room=room,
                files=len(secs),
                diff_sha256=sha(diff),
                doc_chars=sum(len(t) for t in docs.values()),
                category_chars=cats,
                large=len(diff) > room,
            )
            if len(diff) <= room:
                row["excluded"] = "fits one production request (not large)"
            rows.append(row)
        eligible = [r for r in rows if not r.get("excluded")]
        rng = random.Random(SPLIT_SEED)
        order = sorted(r["number"] for r in eligible)
        rng.shuffle(order)
        n_hold = (len(order) + 1) // 2
        holdout = set(order[:n_hold])
        for r in eligible:
            r["split"] = "holdout" if r["number"] in holdout else "dev"
        out = {
            "schema": "large-diff-review/hosts/1",
            "window": "merged 2026-09-25..2026-10-01",
            "split_seed": SPLIT_SEED,
            "production_settings": settings,
            "rows": rows,
        }
        (CORPUS / "hosts.json").write_text(json.dumps(out, indent=1) + "\n")
        return out


CANARY_CORPUS = ROOT / "docs" / "architecture" / "evidence" / "review-canary" / "corpus.toml"
POSITIONS = (("early", 0.05), ("middle", 0.50), ("late", 0.95))


class Selection:
    """Every seeded draw the preregistration names, made once and written down."""

    def build(self) -> dict:
        import tomllib

        hosts = json.loads((CORPUS / "hosts.json").read_text())["rows"]
        eligible = [r for r in hosts if not r.get("excluded")]
        dev = sorted(r["number"] for r in eligible if r["split"] == "dev")
        hold = sorted(r["number"] for r in eligible if r["split"] == "holdout")
        size = {r["number"]: r["chars"] for r in eligible}
        rng = random.Random(SPLIT_SEED + 1)
        pool = [n for n in dev if size[n] <= 260_000]
        rng.shuffle(pool)
        s1, s2_extra = sorted(pool[:4]), sorted(pool[4:6])
        rng2 = random.Random(SPLIT_SEED + 2)
        hold_order = list(hold)
        rng2.shuffle(hold_order)
        confirm = sorted(hold_order[:12])
        canary = tomllib.loads(CANARY_CORPUS.read_text())
        classes = list(canary["classes"])
        by_class: dict[str, list[str]] = {c: [] for c in classes}
        for case in canary["cases"]:
            if case["kind"] == "defect":
                by_class[case["class"]].append(case["id"])
        rng3 = random.Random(SPLIT_SEED + 3)
        dev_needles, hold_needles = [], []
        for c in classes:
            ids = sorted(by_class[c])
            pick = rng3.choice(ids)
            dev_needles.append(pick)
            hold_needles += [i for i in ids if i != pick]
        return {
            "schema": "large-diff-review/selection/1",
            "seeds": {
                "split": SPLIT_SEED,
                "screen_hosts": SPLIT_SEED + 1,
                "confirm_hosts": SPLIT_SEED + 2,
                "needles": SPLIT_SEED + 3,
            },
            "screen_hosts_s1": s1,
            "halving_hosts_s2": sorted(s1 + s2_extra),
            "confirm_hosts": confirm,
            "dev_needles": dev_needles,
            "holdout_needles": hold_needles,
            "positions": dict(POSITIONS),
        }


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "hosts"
    if cmd == "select":
        out = Selection().build()
        (CORPUS / "selection.json").write_text(json.dumps(out, indent=1) + "\n")
        print(json.dumps(out, indent=1))
        return 0
    if cmd == "hosts":
        out = HostCorpus().build()
        el = [r for r in out["rows"] if not r.get("excluded")]
        for r in el:
            print(r["split"], r["number"], r["chars"], r["room"], r["files"], r["category_chars"])
        print("eligible", len(el), "dev", sum(r["split"] == "dev" for r in el))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
