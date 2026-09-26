# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The hourly backlog loop: survey every open issue, apply only what changed.

Sub-doctrine 12.e: the toil of re-reading the whole backlog is automated, and the
`--check` mode is the check that says out loud when triage coverage drops. Status is
evidence-bounded (10.f): every verdict names its object, source and cutoff, and a
verdict is never completion evidence by itself -- a close needs its probes to hold.

    python scripts/backlog_cleanup.py --survey            # verdict table, read-only
    python scripts/backlog_cleanup.py --apply             # act on changes only
    python scripts/backlog_cleanup.py --check             # exit 1 on triage debt

How it stays safe to run hourly:

- Whole-state survey, cursor-free: every run recomputes every verdict from the
  expectations file plus the live checkout and forge, so a cancelled run leaves no
  gap -- the next one derives the same answer (the delivery-estimate 12.g pattern).
- Marker-guarded comments: every status comment ends with
  `<!-- vibey-backlog-cleanup verdict:<sha> -->`. An issue is touched only when its
  freshly computed verdict hash differs from the marker's, or when it has no marker.
- Capped and paced: at most ``MAX_ACTIONS`` forge mutations per run, ``PAUSE_SECONDS``
  apart. A throttle response stops the run cleanly (exit 0); retries never help.
- QwenStorm lanes are survey-only: issues carrying ``qwenstorm`` without an explicit
  expectations entry get a verdict row but never a comment -- their standing reports
  already exist and per-hour lane spam helps nobody.
- Operator-hold issues (``never_act``) are never closed or commented by the loop.

The expectations file (``scripts/backlog_expectations.json``) is the declared state:
per-issue probes plus each issue's last applied verdict. The workflow commits it when
it changes, exactly like the delivery-estimate ledger.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

from interfaces.backlog_cleanup_interface import BacklogCleanupInterface, ProbeInterface

REPO = Path(__file__).resolve().parents[1]
DEFAULT_EXPECTATIONS = "scripts/backlog_expectations.json"
MARKER_PREFIX = "<!-- vibey-backlog-cleanup verdict:"
MAX_ACTIONS = 8
PAUSE_SECONDS = 90
CUTOFF_NOTE = "cutoff origin/develop"


class Gh:
    """The forge through its CLI. Reads raise; mutations return False on throttle."""

    def __init__(self, repo: str | None = None) -> None:
        self.repo = repo

    def _run(self, *args: str, mutation: bool = False) -> subprocess.CompletedProcess[str]:
        cmd = ["gh", *args]
        if self.repo:
            cmd += ["--repo", self.repo]
        return subprocess.run(cmd, capture_output=True, text=True, check=False)

    def open_issues(self) -> list[dict[str, object]]:
        proc = self._run(
            "issue", "list", "--limit", "1000", "--state", "open", "--json", "number,title,labels"
        )
        proc.check_returncode()
        return json.loads(proc.stdout or "[]")

    def issue_state(self, number: int) -> str:
        proc = self._run("issue", "view", str(number), "--json", "state", "--jq", ".state")
        proc.check_returncode()
        return proc.stdout.strip()

    def comments(self, number: int) -> str:
        proc = self._run(
            "issue",
            "view",
            str(number),
            "--json",
            "comments",
            "--jq",
            '[.comments[].body] | join("\\n")',
        )
        proc.check_returncode()
        return proc.stdout

    def comment(self, number: int, body: str) -> bool:
        proc = self._run("issue", "comment", str(number), "--body", body, mutation=True)
        if proc.returncode != 0 and "too quickly" in proc.stderr:
            print("throttled; stopping cleanly", flush=True)
            raise _ThrottleStop
        proc.check_returncode()
        return True

    def close(self, number: int, body: str) -> bool:
        proc = self._run("issue", "close", str(number), "--comment", body, mutation=True)
        if proc.returncode != 0 and "too quickly" in proc.stderr:
            print("throttled; stopping cleanly", flush=True)
            raise _ThrottleStop
        proc.check_returncode()
        return True

    def label_open_count(self, label: str) -> int:
        proc = self._run(
            "issue",
            "list",
            "--limit",
            "1000",
            "--state",
            "open",
            "--label",
            label,
            "--json",
            "number",
            "--jq",
            "length",
        )
        proc.check_returncode()
        return int(proc.stdout.strip() or "0")


class _ThrottleStop(Exception):
    """The forge asked us to slow down: stop the run, keep exit 0."""


class PathExistsProbe:
    """A path exists in the checkout."""

    def __init__(self, path: str) -> None:
        self.path = path

    def name(self) -> str:
        return f"path_exists:{self.path}"

    def holds(self, context: dict[str, object]) -> bool:
        try:
            root = context["root"]
            assert isinstance(root, Path)
            return (root / self.path).exists()
        except Exception:
            return False


class GrepHitProbe:
    """A pattern hits under the given paths in the checkout."""

    SKIP_DIRS = frozenset(
        {
            "node_modules",
            ".git",
            "__pycache__",
            ".venv",
            ".venv-vibey-2.0.0",
            "build",
            "dist",
            "coverage",
            ".mypy_cache",
            ".ruff_cache",
            ".pytest_cache",
            ".hypothesis",
        }
    )

    def __init__(self, pattern: str, paths: list[str]) -> None:
        self.pattern = pattern
        self.paths = paths

    def name(self) -> str:
        return f"grep_hit:{self.pattern}:{','.join(self.paths)}"

    def holds(self, context: dict[str, object]) -> bool:
        try:
            root = context["root"]
            assert isinstance(root, Path)
            rx = re.compile(self.pattern)
            for rel in self.paths:
                target = root / rel
                if target.is_file():
                    if rx.search(target.read_text(errors="replace")):
                        return True
                elif target.is_dir():
                    for path in target.rglob("*"):
                        if not path.is_file() or path.is_symlink():
                            continue
                        if any(part in self.SKIP_DIRS for part in path.parts):
                            continue
                        try:
                            if rx.search(path.read_text(errors="replace")):
                                return True
                        except OSError:
                            continue
            return False
        except Exception:
            return False


class LabelDrainedProbe:
    """No open issue still carries the label (for wave epics)."""

    def __init__(self, label: str, gh: Gh) -> None:
        self.label = label
        self.gh = gh

    def name(self) -> str:
        return f"label_drained:{self.label}"

    def holds(self, context: dict[str, object]) -> bool:
        try:
            return self.gh.label_open_count(self.label) == 0
        except Exception:
            return False


def build_probes(spec: dict[str, object], gh: Gh) -> list[ProbeInterface]:
    """Compile one issue's probe specs. Unknown specs raise: the check says so."""
    probes: list[ProbeInterface] = []
    raw = spec.get("probes", [])
    assert isinstance(raw, list)
    for item in raw:
        assert isinstance(item, dict)
        if "path_exists" in item:
            path = item["path_exists"]
            assert isinstance(path, str)
            probes.append(PathExistsProbe(path))
        elif "grep_hit" in item:
            spec_hit = item["grep_hit"]
            assert isinstance(spec_hit, dict)
            pattern = spec_hit["pattern"]
            paths = spec_hit["paths"]
            assert isinstance(pattern, str) and isinstance(paths, list)
            probes.append(GrepHitProbe(pattern, [str(p) for p in paths]))
        elif "label_drained" in item:
            label = item["label_drained"]
            assert isinstance(label, str)
            probes.append(LabelDrainedProbe(label, gh))
        else:
            raise ValueError(f"unknown probe: {sorted(item)}")
    return probes


def verdict_hash(verdict: str, evidence: str) -> str:
    """The marker's short hash: verdict plus evidence, nothing else."""
    return hashlib.sha256(f"{verdict}\n{evidence}".encode()).hexdigest()[:12]


def marker_for(verdict: str, evidence: str) -> str:
    """The idempotency marker closing every status comment."""
    return f"{MARKER_PREFIX}{verdict_hash(verdict, evidence)}-->"


def marker_in(text: str) -> str | None:
    """The verdict hash a text already carries, if any."""
    match = re.search(r"<!-- vibey-backlog-cleanup verdict:([0-9a-f]{12})-->", text)
    return match.group(1) if match else None


class BacklogCleanup(BacklogCleanupInterface):
    """The loop. Reads expectations, surveys the forge, applies only changes."""

    def __init__(self, gh: Gh, expectations: dict[str, object], cutoff: str) -> None:
        self.gh = gh
        self.expectations = expectations
        self.cutoff = cutoff
        issues = expectations.get("issues", {})
        assert isinstance(issues, dict)
        self.entries: dict[str, dict[str, object]] = {
            str(k): v for k, v in issues.items() if isinstance(v, dict)
        }

    def _labels(self, issue: dict[str, object]) -> list[str]:
        labels = issue.get("labels", [])
        if not isinstance(labels, list):
            return []
        return [str(label.get("name")) for label in labels if isinstance(label, dict)]

    def _row(self, number: int, title: str, labels: list[str]) -> dict[str, object]:
        entry = self.entries.get(str(number))
        context: dict[str, object] = {"root": REPO}
        if entry is None:
            if "qwenstorm" in labels:
                return {
                    "number": number,
                    "title": title,
                    "verdict": "TRACKED-LANE",
                    "evidence": "storm lane; standing report exists",
                    "missing": "",
                    "next": "",
                    "act": False,
                    "entry": False,
                }
            return {
                "number": number,
                "title": title,
                "verdict": "NEEDS-TRIAGE",
                "evidence": "no expectations entry and no cleanup marker",
                "missing": "an expectations entry with probes",
                "next": "triage against the tree, then add probes",
                "act": True,
                "entry": False,
            }
        if entry.get("never_act"):
            return {
                "number": number,
                "title": title,
                "verdict": "OPERATOR-HOLD",
                "evidence": str(entry.get("hold_reason", "operator action owed")),
                "missing": "",
                "next": "",
                "act": False,
                "entry": True,
            }
        probes = build_probes(entry, self.gh)
        held = [p.name() for p in probes if p.holds(context)]
        missing = [p.name() for p in probes if p.name() not in held]
        if not probes:
            verdict = "OPEN"
        elif not missing:
            verdict = "DONE"
        elif held:
            verdict = "PARTIAL"
        else:
            verdict = "OPEN"
        return {
            "number": number,
            "title": title,
            "verdict": verdict,
            "evidence": "; ".join(held) or "no probe holds",
            "missing": "; ".join(missing),
            "next": str(entry.get("next", "")),
            "act": True,
            "entry": True,
            "close_when_done": bool(entry.get("close_when_done", False)),
        }

    def survey(self) -> list[dict[str, object]]:
        """One verdict row per open issue. Read-only: no forge mutations."""
        rows = []
        for issue in self.gh.open_issues():
            number = issue.get("number")
            title = issue.get("title", "")
            assert isinstance(number, int) and isinstance(title, str)
            rows.append(self._row(number, title, self._labels(issue)))
        return rows

    def _body(self, row: dict[str, object]) -> str:
        evidence = (
            f"object = #{row['number']} {row['title']}; "
            f"source = tree read + forge state; {CUTOFF_NOTE} {self.cutoff}. "
            f"evidence: {row['evidence']}. "
            + (f"missing: {row['missing']}. " if row["missing"] else "")
            + (f"next: {row['next']}. " if row["next"] else "")
        )
        return (
            f"## Status report — evidence-bounded (backlog loop)\n\n"
            f"**Verdict: {row['verdict']}.** {evidence}\n\n"
            f"{marker_for(str(row['verdict']), str(row['evidence']))}"
        )

    def apply(self, rows: list[dict[str, object]]) -> dict[str, int]:
        """Comment or close only changed rows. Capped, paced, throttle-clean."""
        counts = {"commented": 0, "closed": 0, "unchanged": 0, "skipped": 0}
        actions = 0
        for row in rows:
            number = row["number"]
            assert isinstance(number, int)
            if not row.get("act"):
                counts["skipped"] += 1
                continue
            if actions >= MAX_ACTIONS:
                counts["skipped"] += 1
                continue
            if self.gh.issue_state(number) != "OPEN":
                counts["skipped"] += 1
                continue
            key = str(number)
            entry = self.entries.get(key)
            if entry is not None and entry.get("last_verdict") == row["verdict"]:
                counts["unchanged"] += 1
                continue
            want = verdict_hash(str(row["verdict"]), str(row["evidence"]))
            try:
                if marker_in(self.gh.comments(number)) == want:
                    counts["unchanged"] += 1
                    if key in self.entries:
                        self.entries[key]["last_verdict"] = row["verdict"]
                    continue
            except subprocess.CalledProcessError:
                counts["skipped"] += 1
                continue
            if actions > 0:
                time.sleep(PAUSE_SECONDS)
            try:
                if row["verdict"] == "DONE" and row.get("close_when_done"):
                    self.gh.close(number, self._body(row))
                    counts["closed"] += 1
                elif row["verdict"] == "NEEDS-TRIAGE":
                    self.gh.comment(number, self._body(row))
                    counts["commented"] += 1
                else:
                    self.gh.comment(number, self._body(row))
                    counts["commented"] += 1
            except _ThrottleStop:
                break
            actions += 1
            if key in self.entries:
                self.entries[key]["last_verdict"] = row["verdict"]
            else:
                self.entries[key] = {
                    "kind": "triaged",
                    "probes": [],
                    "close_when_done": False,
                    "next": "add explicit probes",
                    "last_verdict": row["verdict"],
                }
        return counts

    def coverage_gaps(self, rows: list[dict[str, object]]) -> list[int]:
        """Open non-storm issues with no entry and no marker: triage debt."""
        return [
            int(r["number"])
            for r in rows
            if r.get("verdict") == "NEEDS-TRIAGE" and not r.get("entry")
        ]


def load_expectations(path: Path) -> dict[str, object]:
    """The declared state. Missing file is an error the check reports, not a default."""
    data = json.loads(path.read_text())
    assert isinstance(data, dict)
    return data


def save_expectations(
    path: Path, expectations: dict[str, object], entries: dict[str, dict[str, object]]
) -> bool:
    """Write back last-applied verdicts. True when the file changed."""
    expectations["issues"] = entries
    text = json.dumps(expectations, indent=2, sort_keys=True) + "\n"
    if path.exists() and path.read_text() == text:
        return False
    path.write_text(text)
    return True


def main(argv: list[str]) -> int:
    """Entry point: --survey, --apply, or --check."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--survey", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--expectations", default=DEFAULT_EXPECTATIONS)
    parser.add_argument("--repo", default=None)
    parser.add_argument("--cutoff", default="develop")
    args = parser.parse_args(argv)
    if sum([args.survey, args.apply, args.check]) != 1:
        parser.error("exactly one of --survey, --apply, --check")
    expectations = load_expectations(REPO / args.expectations)
    gh = Gh(args.repo)
    loop = BacklogCleanup(gh, expectations, args.cutoff)
    rows = loop.survey()
    if args.survey:
        for row in rows:
            print(f"#{row['number']} [{row['verdict']}] {row['title']}")
            print(
                f"    evidence: {row['evidence']}"
                + (f" | missing: {row['missing']}" if row["missing"] else "")
            )
        return 0
    if args.check:
        gaps = loop.coverage_gaps(rows)
        if gaps:
            print(
                f"triage debt: {len(gaps)} open issues without entries: "
                + ", ".join(f"#{n}" for n in sorted(gaps)[:20])
            )
            return 1
        print(f"coverage holds: {len(rows)} open issues, no triage debt")
        return 0
    counts = loop.apply(rows)
    changed = save_expectations(REPO / args.expectations, expectations, loop.entries)
    print(json.dumps({**counts, "expectations_changed": changed}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
