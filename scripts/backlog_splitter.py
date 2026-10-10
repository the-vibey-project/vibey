# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The backlog splitter: cut an issue too large for an agent into slices it can finish (ADR-0083).

    python scripts/backlog_splitter.py plan    # what would be filed, read-only
    python scripts/backlog_splitter.py split   # file it

The backlog killer only picks issues that are labelled for the agent and short
(`[backlog_killer] agent_labels`, `max_issue_chars`), so a large issue is never worked. This
lane makes it workable by cutting it along the structure it already has, in this order: its
unchecked task items, its numbered steps, its `##` sections. Each slice becomes a sub-issue of
the original, labelled `split_label`, with the parent named in a marker the picker reads.

Scripted-first, no model: an issue with no such structure is reported and left for a person,
because inventing a decomposition is judgement, and judgement is not toil (12.e). Declared in
`scripts/daily_lanes.toml` `[backlog_splitter]`. It writes issues and one comment, never code,
and never closes, merges or deletes anything (12.d).

Why a child is trusted, though a bot filed it: the picker accepts it only when its author is
`split_authors` (not forgeable), it carries `split_label` (only someone with triage rights can
apply a label), and its marker names an open parent a trusted person wrote (ADR-0083).

Idempotent under replay: each child's key is a hash of its title, and a slice whose key is
already filed under that parent, open or closed, is not filed again, so a run that died midway
is simply run again. The parent is labelled last, so it stays a candidate until all is filed.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from scripts import backlog_killer as bk
    from scripts.interfaces.backlog_splitter_interface import (
        BacklogSplitterInterface,
        SplitSinkInterface,
    )
except ModuleNotFoundError:  # Direct execution keeps the script directory on sys.path.
    import backlog_killer as bk  # type: ignore[no-redef]
    from interfaces.backlog_splitter_interface import (  # type: ignore[import-not-found,no-redef]
        BacklogSplitterInterface,
        SplitSinkInterface,
    )

REPO = Path(__file__).resolve().parents[1]
# What GitHub does not render as text: fenced code (an unclosed fence runs to the end) and HTML
# comments. The outline must not read what a person looking at the issue cannot see.
FENCE = re.compile(r"(```|~~~).*?(?:\1|\Z)", re.S)
HIDDEN = re.compile(r"<!--.*?(?:-->|\Z)", re.S)
TASK = re.compile(r"^ {0,3}[-*+]\s+\[ \]\s+(\S.*)$")
NUMBERED = re.compile(r"^ {0,3}\d{1,2}[.)]\s+(\S.*)$")
HEADING = re.compile(r"^#{2,3}\s+(\S.*?)\s*#*\s*$")
# Headings that describe the issue rather than name a piece of the work.
CONTEXT_HEADINGS = {
    "acceptance criteria",
    "background",
    "context",
    "description",
    "motivation",
    "non-goals",
    "notes",
    "open questions",
    "out of scope",
    "overview",
    "references",
    "summary",
    "why",
}
TITLE_CHARS = 100
DETAIL_CHARS = 1500


class GhSplitSink(SplitSinkInterface):
    """The forge through its CLI. A failed write raises, so the workflow run fails visibly."""

    @staticmethod
    def _gh(*args: str, stdin: str | None = None) -> str:
        proc = subprocess.run(
            ["gh", *args], input=stdin, capture_output=True, text=True, check=False
        )
        if proc.returncode:
            raise RuntimeError(f"gh {' '.join(args[:3])} failed: {proc.stderr.strip()}")
        return proc.stdout

    def split_children(self, label: str) -> list[dict[str, Any]]:
        out = self._gh(
            "api", "-X", "GET", "repos/{owner}/{repo}/issues", "-f", "state=all",
            "-f", f"labels={label}", "-f", "per_page=100", "--paginate",
            "--jq", ".[] | select(.pull_request | not) | {number, body} | @json",
        )  # fmt: skip
        return [json.loads(line) for line in out.splitlines() if line.strip()]

    def ensure_label(self, name: str, color: str, description: str) -> None:
        self._gh("label", "create", name, "--color", color, "--description", description, "--force")

    def create_issue(self, title: str, body: str, labels: list[str]) -> dict[str, Any]:
        args = ["api", "-X", "POST", "repos/{owner}/{repo}/issues", "-f", f"title={title}"]
        args += ["-f", f"body={body}", "--jq", "{id, number} | @json"]
        for label in labels:
            args += ["-f", f"labels[]={label}"]
        return dict(json.loads(self._gh(*args)))

    def link_sub_issue(self, parent: int, child_id: int) -> bool:
        try:
            self._gh(
                "api", "-X", "POST", f"repos/{{owner}}/{{repo}}/issues/{parent}/sub_issues",
                "-F", f"sub_issue_id={child_id}",
            )  # fmt: skip
        except RuntimeError:
            return False
        return True

    def mark_parent(self, parent: int, label: str, comment: str) -> None:
        self._gh("issue", "comment", str(parent), "--body-file", "-", stdin=comment)
        self._gh("issue", "edit", str(parent), "--add-label", label)


class BacklogSplitter(BacklogSplitterInterface):
    """Finds the issues too large to hand an agent and files the slices their structure names."""

    def __init__(
        self,
        source: bk.BacklogSourceInterface,
        sink: SplitSinkInterface,
        killer: dict[str, Any],
        settings: dict[str, Any],
        expectations: dict[str, Any],
    ) -> None:
        self._source = source
        self._sink = sink
        self._enabled = bool(settings.get("enabled", False))
        self._min = max(2, int(settings.get("min_children", 2)))
        self._max = max(self._min, int(settings.get("max_children", 8)))
        self._max_parents = max(1, int(settings.get("max_parents_per_run", 3)))
        # The operator's opt-in: only an issue already labelled for the agent is cut, so the
        # lane never widens what the agent may touch (12.d).
        self._agent_labels = {str(x) for x in killer.get("agent_labels", [])}
        self._parent_label = str(settings.get("parent_label", "vibey-gh:split"))
        self._child_label = str(killer.get("split_label", "vibey-gh:split-child"))
        self._limit = int(killer.get("max_issue_chars", 0))
        # Whose words may be cut, and what is never touched, are the killer's own rules.
        self._trusted = {
            str(x) for x in killer.get("trusted_associations", ["OWNER", "MEMBER", "COLLABORATOR"])
        }
        self._skip_authors = {str(x) for x in killer.get("skip_authors", [])}
        allowed = {str(x) for x in killer.get("split_parent_allow_labels", [])}
        self._skip_labels = {str(x) for x in killer.get("skip_labels", [])} - allowed
        entries = expectations.get("issues", {})
        self._held = {
            int(number)
            for number, entry in (entries.items() if isinstance(entries, dict) else ())
            if isinstance(entry, dict) and entry.get("never_act")
        }

    # --- reading the structure --------------------------------------------------------------

    @staticmethod
    def _plain(text: str) -> str:
        text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
        # No comment opener or closer survives into a slice, so no marker can be quoted into one.
        text = text.replace("<!--", "").replace("-->", "")
        return re.sub(r"[*_]{1,3}", "", text).strip()

    @staticmethod
    def _list_items(lines: list[str], start: re.Pattern[str]) -> list[tuple[str, str]]:
        """Items that begin at `start`; indented lines and blank ones belong to the item above."""
        items: list[tuple[str, list[str]]] = []
        for line in lines:
            if hit := start.match(line):
                items.append((hit.group(1).strip(), []))
            elif items and (not line.strip() or line.startswith("  ")):
                items[-1][1].append(line.strip())
            elif items and not line.startswith((" ", "\t")):
                items[-1][1].append("\0")  # a flush-left line ends the item
        done = []
        for title, rest in items:
            kept = rest[: rest.index("\0")] if "\0" in rest else rest
            done.append((title, "\n".join(kept).strip()))
        return done

    @staticmethod
    def _sections(lines: list[str]) -> list[tuple[str, str]]:
        sections: list[tuple[str, list[str]]] = []
        for line in lines:
            if hit := HEADING.match(line):
                sections.append((hit.group(1).strip(), []))
            elif sections:
                sections[-1][1].append(line)
        return [
            (title, "\n".join(body).strip())
            for title, body in sections
            if title.lower().rstrip(":") not in CONTEXT_HEADINGS
        ]

    @classmethod
    def _slice(cls, title: str, detail: str) -> tuple[str, str]:
        """A wrapped list item is one sentence over several lines: its title is the first
        paragraph of it, whole, and the detail is all of it."""
        first, _, rest = detail.partition("\n\n")
        return cls._plain(f"{title} {first.replace(chr(10), ' ')}".strip()), rest.strip()

    def outline(self, body: str) -> list[tuple[str, str]]:
        lines = HIDDEN.sub("", FENCE.sub("", body)).splitlines()
        sections = [(self._plain(t), d) for t, d in self._sections(lines) if t.strip()]
        for found in (
            [self._slice(t, d) for t, d in self._list_items(lines, TASK) if t.strip()],
            [self._slice(t, d) for t, d in self._list_items(lines, NUMBERED) if t.strip()],
            sections,
        ):
            if len(found) >= self._min:
                return found
        return []

    # --- choosing what to cut ---------------------------------------------------------------

    def parents(self) -> list[dict[str, Any]]:
        found = []
        for issue in self._source.open_issues():
            labels = bk.BacklogKiller._labels(issue)
            body = str(issue.get("body") or "")
            author = str((issue.get("author") or {}).get("login", ""))
            if (
                int(issue["number"]) in self._held
                or author in self._skip_authors
                or str(issue.get("authorAssociation", "")) not in self._trusted
                or self._skip_labels.intersection(labels)
                or self._parent_label in labels
                or self._child_label in labels
                or bk.SPLIT_CHILD.search(body)
            ):
                continue
            opted_in = not self._agent_labels or bool(self._agent_labels.intersection(labels))
            if opted_in and bool(self._limit) and len(body) > self._limit:
                found.append(issue)
        return sorted(found, key=lambda i: (str(i.get("createdAt", "")), int(i["number"])))

    # --- planning and filing ----------------------------------------------------------------

    @staticmethod
    def _key(title: str) -> str:
        return hashlib.sha256(" ".join(title.lower().split()).encode()).hexdigest()[:12]

    def _child(self, parent: dict[str, Any], title: str, detail: str, key: str) -> tuple[str, str]:
        number = int(parent["number"])
        head = title if len(title) <= TITLE_CHARS else title[: TITLE_CHARS - 1].rstrip() + "…"
        body = (
            f"Part of #{number} — {parent.get('title', '')}\n\n"
            f"**This slice:** {title}\n\n{self._plain(detail)[:DETAIL_CHARS]}\n\n"
            f"Land only this slice, with a test that fails without it, and leave the rest of "
            f"#{number} alone.\n\n"
            f"<!-- vibey-gh:split-child parent={number} key={key} -->"
        )
        return f"{head} (part of #{number})", body

    def _filed(self) -> dict[tuple[int, str], int]:
        filed = {}
        for child in self._sink.split_children(self._child_label):
            for parent, key in bk.SPLIT_CHILD.findall(str(child.get("body") or "")):
                filed[(int(parent), key)] = int(child["number"])
        return filed

    def run(self, *, apply: bool) -> list[str]:
        if not self._enabled:
            return ["The backlog splitter is switched off (`[backlog_splitter] enabled = false`)."]
        filed = self._filed()
        report: list[str] = []
        worked = 0
        for parent in self.parents():
            number = int(parent["number"])
            slices = self.outline(str(parent.get("body") or ""))
            if not slices:
                report.append(
                    f"#{number}: too large, but no task list, steps or sections to cut on"
                )
                continue
            if worked >= self._max_parents:
                report.append(f"#{number}: waits for a later run ({self._max_parents} per run)")
                continue
            worked += 1
            kept, rest = slices[: self._max], len(slices[self._max :])
            report.append(
                f"#{number}: {len(kept)} slice(s)" + (f", {rest} left on it" if rest else "")
            )
            listing = []
            seen: set[str] = set()
            for title, detail in kept:
                key = self._key(title)
                if key in seen:
                    continue
                seen.add(key)
                child_title, child_body = self._child(parent, title, detail, key)
                existing = filed.get((number, key))
                if existing is not None:
                    listing.append(f"- #{existing} {title}")
                    report.append(f"  #{existing} exists: {title}")
                    continue
                if not apply:
                    report.append(f"  would file: {child_title}")
                    continue
                self._sink.ensure_label(self._child_label, "0e8a16", "A slice of a larger issue")
                made = self._sink.create_issue(child_title, child_body, [self._child_label])
                linked = self._sink.link_sub_issue(number, int(made["id"]))
                listing.append(f"- #{made['number']} {title}")
                report.append(
                    f"  filed #{made['number']}: {title}"
                    + ("" if linked else " (not linked as a sub-issue; the marker still names it)")
                )
            if apply:
                self._sink.ensure_label(self._parent_label, "5319e7", "Cut into smaller issues")
                note = [
                    f"Cut into {len(listing)} smaller issue(s) an agent can finish one at a time:"
                ]
                note += ["", *listing]
                if rest:
                    note += ["", f"{rest} more slice(s) stay on this issue."]
                self._sink.mark_parent(number, self._parent_label, "\n".join(note))
        return report or ["No open issue is too large to hand an agent."]


def main(argv: list[str]) -> int:
    """Entry point: `plan` or `split`. Module-level as every script's is."""
    if argv not in (["plan"], ["split"]):
        print(__doc__, file=sys.stderr)
        return 2
    killer, expectations = bk.load(REPO)
    import tomllib

    settings = tomllib.loads((REPO / bk.CONFIG).read_text(encoding="utf-8")).get(
        "backlog_splitter", {}
    )
    splitter = BacklogSplitter(bk.GhBacklogSource(), GhSplitSink(), killer, settings, expectations)
    for line in splitter.run(apply=argv == ["split"]):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
