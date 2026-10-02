"""Fetch the diff each sovereign review judged and compute its size and content mix.

The workflow reviews `gh pr diff` at the evaluated head (falling back to a local merge-base
diff past ~300 files). Re-fetching `gh pr diff` today returns the PR's *current* head, so this
fetches GitHub's compare view `<pr.base.sha>...<head_sha>`: the three-dot (merge-base) diff of
the exact reviewed head against the PR's recorded base. Comparing against today's `develop`
is wrong here: develop's history was rewritten during the span (PR 1238's base.sha is not an
ancestor of origin/develop), which inflated such a diff to thousands of files; a first pass
that did so was discarded. Validation: where the job log itself states the diff's size (a
chunk-budget refusal names its characters), parse_reviews compares the two (diff_chars_logged).
Diffs are stored gzipped under raw/gh/diffs/.

Content classes (by path, per changed line): test, docs, code, config_ci, generated_data.
"""

from __future__ import annotations

import gzip
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
EVIDENCE = HERE.parent
OUT = EVIDENCE / "raw" / "gh" / "diffs"
REPO = "the-vibey-project/vibey"
CODE = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".c",
    ".h",
    ".go",
    ".rs",
    ".sh",
    ".java",
    ".kt",
    ".swift",
    ".sql",
    ".vue",
    ".css",
    ".scss",
    ".html",
    ".tex",
    ".mmd",
}
DOCS = {".md", ".mdx", ".mdc", ".rst", ".txt", ".adoc"}
CONFIG = {
    ".yml",
    ".yaml",
    ".toml",
    ".json",
    ".cfg",
    ".ini",
    ".lock",
    ".cff",
    ".xml",
    ".plist",
    ".spec",
}
GENERATED = re.compile(
    r"(coverage|golden/|corpus-index\.json|minimum-specs\.json|\.lock$|uv\.lock|package-lock|"
    r"evidence/.*\.json$|\.min\.|snapshots?/)"
)


def klass(path: str) -> str:
    low = path.lower()
    name = low.rsplit("/", 1)[-1]
    ext = "." + name.rsplit(".", 1)[-1] if "." in name else ""
    if GENERATED.search(low):
        return "generated_data"
    if (
        "/test/" in low
        or "/tests/" in low
        or low.startswith(("test/", "tests/"))
        or name.startswith("test_")
        or re.search(r"(_test|\.test|\.spec)\.\w+$", name)
    ):
        return "test"
    if ext in DOCS:
        return "docs"
    if ext in CODE:
        return "code"
    if ext in CONFIG or low.startswith(".github/") or name in ("dockerfile", "makefile"):
        return "config_ci"
    return "docs" if low.startswith("docs/") else "other"


def stats(text: str) -> dict:
    files = []
    current = None
    for line in text.splitlines():
        if line.startswith("diff --git "):
            m = re.match(r"diff --git a/(.*) b/(.*)$", line)
            current = {
                "path": m.group(2) if m else line,
                "added": 0,
                "removed": 0,
                "chars": 0,
                "rename": False,
                "binary": False,
                "new": False,
                "deleted": False,
            }
            files.append(current)
            continue
        if current is None:
            continue
        current["chars"] += len(line) + 1
        if line.startswith("rename from"):
            current["rename"] = True
        elif line.startswith("new file mode"):
            current["new"] = True
        elif line.startswith("deleted file mode"):
            current["deleted"] = True
        elif line.startswith("Binary files"):
            current["binary"] = True
        elif line.startswith("+") and not line.startswith("+++"):
            current["added"] += 1
        elif line.startswith("-") and not line.startswith("---"):
            current["removed"] += 1
    mix: dict[str, int] = {}
    for f in files:
        f["class"] = klass(f["path"])
        mix[f["class"]] = mix.get(f["class"], 0) + f["added"] + f["removed"]
    changed = sum(mix.values()) or 1
    largest = max(files, key=lambda f: f["chars"]) if files else None
    return {
        "chars": len(text),
        "lines": text.count("\n"),
        "files": len(files),
        "added": sum(f["added"] for f in files),
        "removed": sum(f["removed"] for f in files),
        "renames": sum(f["rename"] for f in files),
        "pure_renames": sum(1 for f in files if f["rename"] and f["added"] + f["removed"] == 0),
        "new_files": sum(f["new"] for f in files),
        "deleted_files": sum(f["deleted"] for f in files),
        "binary_files": sum(f["binary"] for f in files),
        "added_only_share": round(sum(f["added"] for f in files if f["removed"] == 0) / changed, 4),
        "mix_changed_lines": mix,
        "mix_share": {k: round(v / changed, 4) for k, v in mix.items()},
        "dominant_class": max(mix, key=mix.get) if mix else None,
        "largest_file": {"path": largest["path"], "chars": largest["chars"]} if largest else None,
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    pairs = set()
    for line in (EVIDENCE / "dataset-reviews.jsonl").read_text().splitlines():
        r = json.loads(line)
        if r["pr"] and r["head_sha"]:
            pairs.add((r["pr"], r["head_sha"]))
    bases: dict[int, str] = {}
    for pr in sorted({p for p, _ in pairs}):
        got = subprocess.run(
            ["gh", "api", f"repos/{REPO}/pulls/{pr}", "--jq", ".base.sha"], capture_output=True
        )
        bases[pr] = got.stdout.decode().strip()

    def one(pair):
        pr, sha = pair
        target = OUT / f"{pr}-{sha}.diff.gz"
        base = bases.get(pr)
        if not target.exists():
            got = subprocess.run(
                [
                    "gh",
                    "api",
                    "-H",
                    "Accept: application/vnd.github.diff",
                    f"repos/{REPO}/compare/{base}...{sha}",
                ],
                capture_output=True,
            )
            if got.returncode != 0:
                return {"pr": pr, "sha": sha, "base": base, "error": got.stderr.decode()[:200]}
            target.write_bytes(gzip.compress(got.stdout))
        text = gzip.decompress(target.read_bytes()).decode("utf-8", errors="replace")
        s = stats(text)
        s.update(
            {
                "pr": pr,
                "head_sha": sha,
                "base_sha": base,
                "source": f"github compare {base}...{sha} (pr.base.sha...reviewed head; fetched 2026-10-01)",
            }
        )
        (OUT / f"{pr}-{sha}.stats.json").write_text(json.dumps(s, indent=1) + "\n")
        return None

    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(8) as pool:
        failures = [f for f in pool.map(one, sorted(pairs)) if f]
    (OUT / "FAILURES.json").write_text(json.dumps(failures, indent=1) + "\n")
    print(len(pairs), "pairs;", len(failures), "failed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
