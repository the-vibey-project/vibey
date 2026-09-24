# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey-gh announce`: what a docs deploy tells the community, in a few lines.

A published channel says what changed, concisely: one line per merged change, grouped
Breaking / Added / Fixed / Other, capped, with the rest counted and linked, and the
published surfaces after it. Configured by `[announce]` (`vibey_gh.config.AnnounceConfig`).

Three rules it holds and does not let configuration loosen:

- **The range is a position, never a time (sub-doctrine 10.g).** The integration channel
  announces the commits since the release commit the previous accepted announcement
  covered. That commit is read back from the Actions API: every run of the release-surfaces
  workflow is titled `<name> · <branch> · <release commit or release run id>`
  (`RUN_TITLE`), and only a run whose `ANNOUNCED_STEP` succeeded counts: the step runs
  only when the webhook accepted the post AND the position was not `unknown`. A history
  that could not be READ makes the announcement `unknown`, which is never recorded, so the
  next one covers the span again; a history that was read and holds no usable position
  (the first announcement, a force-push, an exhausted window) re-anchors, is recorded, and
  says so. A commit already announced for its branch is not posted again. A release
  announces its own notes, the version's section of the changelog, with the tag range when
  one resolves.
- **Commit subjects are data.** Every one passes through `ChangelogComposer.escape`, and the
  payload carries `allowed_mentions: {"parse": []}`, so a subject cannot ping anyone, open a
  link, or format the message.
- **A deploy is never failed by its announcement (12.e).** No webhook: said and passed. A
  webhook that fails: a `::warning::`. The URL is never printed.

Why not `?branch=` on the runs endpoint, the obvious query: a `workflow_run` run is
attributed to the repository's DEFAULT branch whatever branch released, so filtering by
branch finds nothing for the release branch, and a run's own `head_sha` is the default
branch's head when the run started, which can be a commit newer than the one it published.
Taking either as the position would skip commits. The run title carries the branch and the
commit the run actually published.
"""

from __future__ import annotations

import argparse
import dataclasses
import http.client
import json
import os
import re
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from vibey_gh import fingerprints
from vibey_gh.announce_records import (
    HEX_SHA,
    REANCHORED,
    UNKNOWN,
    Announcement,
    AnnounceRequest,
    Change,
    ChangeSet,
    CommitRange,
    CommitRecord,
    Position,
    ReleaseNotes,
    Surface,
)
from vibey_gh.config import AnnounceConfig, GhConfig, load_config
from vibey_gh.flatten import Flattener
from vibey_gh.gh_transport import GhTransport
from vibey_gh.interfaces.announce_interface import (
    AnnouncerInterface,
    ChangelogComposerInterface,
    ReleaseHistoryInterface,
    WebhookPosterInterface,
)
from vibey_gh.interfaces.gh_transport_interface import GhTransportInterface
from vibey_gh.versioning import read_version

__all__ = [
    "ANNOUNCED_STEP",
    "RUN_TITLE",
    "WEBHOOK_ENV",
    "AnnounceRequest",
    "Announcement",
    "Announcer",
    "Change",
    "ChangeSet",
    "ChangelogComposer",
    "CommitRange",
    "CommitRecord",
    "DiscordWebhook",
    "Position",
    "ReleaseHistory",
    "ReleaseNotes",
    "Surface",
]

# The workflow step that runs only when the webhook accepted the post. Its success in a run's
# jobs is the durable record that the run's release commit WAS announced; the release-surfaces
# template names it exactly this, and test_announce.py holds the two together.
ANNOUNCED_STEP = "Record the announced position"

# `<workflow name> · <branch> · <40-hex release commit | release run id>`: the `run-name` the
# release-surfaces template gives every run, parsed back here. A `workflow_dispatch` run is
# titled with the release RUN id it republishes, which is resolved to that run's commit.
RUN_TITLE = re.compile(r" · (?P<branch>[^\s·]+) · (?P<ref>[0-9a-f]{40}|\d+)$")

# The environment variable the workflow step exposes the webhook secret as. The secret's own
# name is `[announce] webhook_secret`; this is what the step calls it once it is inside.
WEBHOOK_ENV = "DISCORD_WEBHOOK_URL"

# Discord's message `flags` bit that suppresses link previews.
_SUPPRESS_EMBEDS = 1 << 2

_SHA = HEX_SHA

# The Actions API serves a status-filtered run listing only up to its 1000th result: pages
# past the tenth come back empty, however many runs there are. `max_history_pages` is capped
# at this, so an empty tenth page is never mistaken for the end of the history.
API_RUN_WINDOW = 1000

_SUBJECT = re.compile(
    r"^(?P<type>[a-z][a-z0-9-]*)(?:\((?P<scope>[^)]*)\))?(?P<bang>!)?: (?P<description>.+)$"
)
# ASCII digits only: `(#١٢٣)` is Arabic-Indic text, not a pull request, and must not be linked.
_TRAILING_PR = re.compile(r"\s*\(#(?P<number>[0-9]+)\)\s*$", re.ASCII)
_PR_REFERENCE = re.compile(r"(?<![\w/&])#(?P<number>[0-9]+)\b", re.ASCII)

# Characters that draw nothing but can hide, reorder or pad text, removed outright on top of
# every Unicode control (Cc, which becomes a space) and format character (Cf: zero-width
# joiners, bidirectional marks and overrides, U+061C, the soft hyphen, the tag characters):
# the Hangul fillers, which render as blank, and the variation selectors.
_BLANK = frozenset(
    [0x115F, 0x1160, 0x3164, 0xFFA0, *range(0xFE00, 0xFE10), *range(0xE0100, 0xE01F0)]
)
# Every character Discord's markdown, mention or link syntax is built from. `:` breaks both a
# bare `https://` link and a custom emoji; `@` and `<` break every mention form.
_MARKDOWN = re.compile(r"([\\*_~`|>\[\]()#<:@])")

# A changelog heading, as `conventional-changelog` and Keep a Changelog each spell it, read as
# the commit type its entries would have carried.
_HEADING_TYPES = {
    "features": "feat",
    "added": "feat",
    "bug fixes": "fix",
    "fixed": "fix",
    "fixes": "fix",
    "documentation": "docs",
    "performance improvements": "perf",
    "code refactoring": "refactor",
    "changed": "refactor",
    "tests": "test",
    "build system": "build",
    "continuous integration": "ci",
    "miscellaneous chores": "chore",
    "reverts": "revert",
}
_BREAKING_HEADINGS = {"breaking changes", "breaking change", "breaking"}
_VERSION_HEADING = re.compile(r"^## \[?(?P<version>[^\]\s(]+)\]?")
_ENTRY_SCOPE = re.compile(r"^\*\*(?P<scope>[^*]+?):\*\*\s*")
_MARKDOWN_LINK = re.compile(r"\[(?P<text>[^\]]*)\]\([^)]*\)")
_SENTENCE_END = re.compile(r"(?<=[\w)`'\"])[.;](?=\s+[A-Z`(*\[]|\s*$)")

# The surfaces a deploy may have produced, in the order the message lists them.
_SURFACES = (
    ("paper.pdf", "paper PDF"),
    ("paper.docx", "paper DOCX"),
    ("paper/index.html", "paper HTML"),
    ("book.pdf", "book PDF"),
    ("book.epub", "book EPUB"),
    ("book-print.html", "book print"),
)


def _units(text: str) -> int:
    """`text`'s length as Discord counts it: UTF-16 code units, so an emoji costs two.

    Module-level because it is arithmetic on a string that every class here needs, with no
    state to hold; a class around it would be a namespace, not an object.
    """
    return len(text.encode("utf-16-le")) // 2


def _plural(count: int, noun: str) -> str:
    """`1 change`, `2 changes`. Module-level for the reason `_units` is."""
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


class ReleaseHistory(ReleaseHistoryInterface):
    """Implements `ReleaseHistoryInterface` over the GitHub REST API through `gh api`.

    A position is either KNOWN, or not known for one of two reasons, and they are kept apart
    because they call for opposite things (10.g). A source that could not be READ (the API
    erred, answered something malformed, a run's jobs or its commit could not be listed)
    leaves the watermark where it was: nothing this run does may be recorded. A history that
    was read and holds no usable position (no earlier accepted announcement, none within the
    API's window, more unaccepted runs than `candidates` in a row) is structural: this run
    re-anchors on its own commit and says so, since reading again would find the same thing.
    """

    def __init__(
        self,
        repository: str,
        run_id: str,
        *,
        transport: GhTransportInterface | None = None,
        pages: int = 10,
        candidates: int = 20,
    ) -> None:
        self._repository = repository
        self._run_id = run_id
        self._transport = transport or GhTransport()
        self._pages = min(pages, API_RUN_WINDOW // 100)
        self._candidates = candidates

    def _api(self, path: str) -> tuple[Any, str]:
        return self._transport.survey(["api", f"repos/{self._repository}/{path}"])

    @staticmethod
    def _unread(reason: str) -> Position:
        return Position(None, reason, structural=False)

    def previous_position(self, branch: str, head: str) -> Position:
        if not self._run_id.isdigit():
            return self._unread("this run's id is unknown, so its workflow cannot be asked")
        run, problem = self._api(f"actions/runs/{self._run_id}")
        workflow = run.get("workflow_id") if isinstance(run, dict) else None
        if problem or not isinstance(workflow, int):
            return self._unread(
                f"the Actions API did not name this workflow ({problem or 'no id'})"
            )
        unaccepted = 0
        for page in range(1, self._pages + 1):
            data, problem = self._api(
                f"actions/workflows/{workflow}/runs?status=success&per_page=100&page={page}"
            )
            runs = data.get("workflow_runs") if isinstance(data, dict) else None
            if problem or not isinstance(runs, list):
                return self._unread(
                    f"the Actions API did not list earlier runs ({problem or 'malformed'})"
                )
            for candidate in runs:
                match = RUN_TITLE.search(str(candidate.get("display_title", "")))
                if match is None or match["branch"] != branch:
                    continue
                announced, why = self._announced(candidate.get("id"))
                if why:
                    return self._unread(why)
                if announced:
                    return self._resolve(match["ref"])
                unaccepted += 1
                if unaccepted >= self._candidates:
                    return Position(
                        None,
                        f"{unaccepted} runs for {branch} since the last accepted announcement",
                        structural=True,
                    )
            if len(runs) < 100:
                return Position(
                    None, f"no earlier announcement is recorded for {branch}", structural=True
                )
        window = self._pages * 100
        beyond = " (the API's window)" if window == API_RUN_WINDOW else ""
        return Position(
            None,
            f"no accepted announcement for {branch} in the last {window} runs{beyond}",
            structural=True,
        )

    def _announced(self, run_id: object) -> tuple[bool, str]:
        """Whether run `run_id`'s announcement was accepted, or why that cannot be read."""
        data, problem = self._api(f"actions/runs/{run_id}/jobs?per_page=100")
        jobs = data.get("jobs") if isinstance(data, dict) else None
        if problem or not isinstance(jobs, list):
            return False, (
                f"the Actions API did not list run {run_id}'s jobs ({problem or 'malformed'})"
            )
        accepted = any(
            step.get("name") == ANNOUNCED_STEP and step.get("conclusion") == "success"
            for job in jobs
            for step in job.get("steps") or []
        )
        return accepted, ""

    def _resolve(self, ref: str) -> Position:
        """A run title's reference as a commit: a commit already, or a release run's."""
        if len(ref) == 40 and not ref.isdigit():
            return Position(ref)
        run, problem = self._api(f"actions/runs/{ref}")
        sha = run.get("head_sha") if isinstance(run, dict) else None
        if problem or not isinstance(sha, str) or not _SHA.fullmatch(sha):
            return self._unread(f"release run {ref} names no commit ({problem or 'no head_sha'})")
        return Position(sha)

    def compare(self, base: str, head: str) -> tuple[CommitRange | None, str]:
        if not (AnnounceRequest.refname(base) and AnnounceRequest.refname(head)):
            return None, f"{base!r}...{head!r} is not a range of git references"
        # A branch or tag may hold `/`; encoded, it stays one path segment of the API's URL.
        spec = f"{urllib.parse.quote(base, safe='')}...{urllib.parse.quote(head, safe='')}"
        status, total, html_url = "", 0, ""
        commits: list[CommitRecord] = []
        for page in range(1, self._pages + 1):
            data, problem = self._api(f"compare/{spec}?per_page=100&page={page}")
            if problem or not isinstance(data, dict):
                return None, f"the compare API did not answer for {base}...{head} ({problem})"
            if page == 1:
                status = str(data.get("status", ""))
                total = int(data.get("total_commits", 0))
                html_url = str(data.get("html_url", ""))
            batch = data.get("commits") or []
            commits.extend(
                CommitRecord(
                    str(item.get("sha", "")), str((item.get("commit") or {}).get("message", ""))
                )
                for item in batch
            )
            if not batch or len(commits) >= total:
                break
        return CommitRange(status, total, tuple(commits), html_url), ""

    def commit(self, sha: str) -> tuple[CommitRecord | None, str]:
        data, problem = self._api(f"commits/{sha}")
        if problem or not isinstance(data, dict):
            return None, f"the commits API did not answer for {sha[:12]} ({problem})"
        return CommitRecord(sha, str((data.get("commit") or {}).get("message", ""))), ""


class ChangelogComposer(ChangelogComposerInterface):
    """Implements `ChangelogComposerInterface`. Pure: no I/O, no clock, no network."""

    def __init__(self, cfg: AnnounceConfig, repository: str, server_url: str) -> None:
        self._cfg = cfg
        self._base = f"{server_url.rstrip('/')}/{repository}"
        self._groups = {kind: label for label, kinds in cfg.groups for kind in kinds}
        self._words = dict(cfg.type_words)
        self._noise = tuple(re.compile(pattern) for pattern in cfg.noise_patterns)
        labels = [cfg.breaking_group, *(label for label, _ in cfg.groups), cfg.other_group]
        self._order = {label: index for index, label in enumerate(labels)}

    @staticmethod
    def escape(text: str) -> str:
        visible = "".join(
            ChangelogComposer._visible(char) for char in unicodedata.normalize("NFC", text)
        )
        return _MARKDOWN.sub(r"\\\1", " ".join(visible.split()))

    @staticmethod
    def _visible(char: str) -> str:
        """A control character as a space; a format character or a blank filler as nothing."""
        category = unicodedata.category(char)
        if category == "Cc":
            return " "
        if category == "Cf" or ord(char) in _BLANK:
            return ""
        return char

    def _change(self, kind: str, scope: str, text: str, reference: str, breaking: bool) -> Change:
        group = (
            self._cfg.breaking_group if breaking else self._groups.get(kind, self._cfg.other_group)
        )
        url = ""
        if reference.startswith("#"):
            url = f"{self._base}/pull/{reference[1:]}"
        elif reference:
            url = f"{self._base}/commit/{reference}"
        return Change(
            group=group,
            word=self._words.get(kind, kind.capitalize()),
            scope=scope,
            description=text,
            reference=reference if reference.startswith("#") else reference[:7],
            url=url,
            breaking=breaking,
        )

    def _sort(self, changes: Sequence[Change]) -> tuple[Change, ...]:
        return tuple(sorted(changes, key=lambda change: self._order[change.group]))

    def from_commits(self, commits: Sequence[CommitRecord], unread: int = 0) -> ChangeSet:
        changes: list[Change] = []
        noise = 0
        # Newest first: the compare API lists a range oldest first, and a reader wants the
        # latest change at the top of its group.
        for record in reversed(commits):
            subject = record.message.partition("\n")[0].strip()
            # Asked of `Flattener`, which owns both spellings of "breaking" for this package,
            # so an announcement can never call a change minor that a version bump called major.
            breaking = Flattener._marks_breaking(subject) or bool(
                Flattener._breaking_lines(record.message)
            )
            if not breaking and any(pattern.search(subject) for pattern in self._noise):
                noise += 1
                continue
            kind, scope, text = "", "", subject
            # Conformance is `fingerprints`' to decide, as it is for every gate in this package;
            # `_SUBJECT` only takes a conforming subject apart.
            conforming = fingerprints.conventional_subject(subject)
            match = _SUBJECT.match(subject) if conforming else None
            if match is not None:
                kind, scope, text = match["type"], match["scope"] or "", match["description"]
            number = _TRAILING_PR.search(text)
            reference = record.sha
            if number is not None:
                text, reference = text[: number.start()], f"#{number['number']}"
            changes.append(self._change(kind, scope, text, reference, breaking))
        return ChangeSet(self._sort(changes), noise=noise, unread=max(unread, 0))

    def from_changelog(self, text: str, version: str) -> ReleaseNotes | None:
        lines = text.splitlines()
        start = next(
            (
                index
                for index, line in enumerate(lines)
                if (heading := _VERSION_HEADING.match(line)) and heading["version"] == version
            ),
            None,
        )
        if start is None:
            return None
        previous: str | None = None
        end = len(lines)
        for index in range(start + 1, len(lines)):
            heading = _VERSION_HEADING.match(lines[index])
            if heading is not None:
                end = index
                if heading["version"].lower() != "unreleased":
                    previous = heading["version"]
                break
        changes: list[Change] = []
        kind, breaking = "", False
        entry: list[str] = []
        for line in lines[start + 1 : end]:
            if entry and line.startswith("  ") and line.strip():
                entry.append(line.strip())
                continue
            if entry:
                changes.append(self._entry(" ".join(entry), kind, breaking))
                entry = []
            if line.startswith("### "):
                heading_text = line[4:].strip().lower()
                breaking = heading_text in _BREAKING_HEADINGS
                # A breaking entry's group already says what it is; it keeps only its scope.
                kind = "" if breaking else _HEADING_TYPES.get(heading_text, heading_text.split()[0])
            elif line.startswith(("* ", "- ")):
                entry = [line[2:].strip()]
        if entry:
            changes.append(self._entry(" ".join(entry), kind, breaking))
        return ReleaseNotes(ChangeSet(self._sort(changes)), previous)

    def _entry(self, text: str, kind: str, breaking: bool) -> Change:
        """One changelog bullet as a change: its `**scope:**`, its first sentence, its PR."""
        scope = ""
        match = _ENTRY_SCOPE.match(text)
        if match is not None:
            scope, text = match["scope"].strip(), text[match.end() :]
        number = _PR_REFERENCE.search(text)
        plain = _MARKDOWN_LINK.sub(lambda link: link["text"], text)
        end = _SENTENCE_END.search(plain)
        sentence = _TRAILING_PR.sub("", plain[: end.start()] if end is not None else plain)
        reference = f"#{number['number']}" if number is not None else ""
        return self._change(kind, scope, sentence, reference, breaking)

    def _line(self, change: Change, limit: int) -> str:
        description = " ".join(change.description.split()).rstrip(" .;:")
        if len(description) > limit:
            description = description[: limit - 1].rstrip() + "…"
        lead = " · ".join(self.escape(part) for part in (change.word, change.scope) if part)
        body = f"{lead}: {self.escape(description)}" if lead else self.escape(description)
        if not change.reference:
            return f"- {body}"
        # Built here, never read from a subject: `#` and digits, or a short hex commit id.
        label = change.reference
        if self._cfg.link_pull_requests and change.url:
            return f"- {body} ([{label}](<{change.url}>))"
        return f"- {body} ({label})"

    def render(
        self,
        header: str,
        changes: ChangeSet,
        *,
        more_url: str = "",
        more_label: str = "",
        surfaces: Sequence[Surface] = (),
    ) -> Announcement:
        cfg = self._cfg
        breaking = [change for change in changes.changes if change.breaking]
        rest = [change for change in changes.changes if not change.breaking]
        hidden = 0
        if not cfg.include_other:
            hidden = sum(change.group == cfg.other_group for change in rest)
            rest = [change for change in rest if change.group != cfg.other_group]
        listed = rest[: cfg.max_changes]
        surface_line = ""
        if cfg.link_surfaces and surfaces:
            surface_line = "Read: " + " · ".join(
                f"[{self.escape(surface.label)}](<{surface.url}>)" for surface in surfaces
            )
        link = ""
        if more_url and cfg.link_compare:
            link = f"[{self.escape(more_label or 'full list')}](<{more_url}>)"
        # Give up the least important thing first, deciding each count in one pass over
        # prefix sums rather than by re-rendering: listed changes go from the end; then
        # breaking lines get shorter; then, only when breaking changes alone cannot fit, the
        # last of them are counted, by name, as breaking; then the surface line.
        full = cfg.max_subject_chars
        levels = list(dict.fromkeys((full, max(min(full, 40), full // 2), min(full, 40))))
        listed_units = self._prefix(listed, full)
        breaking_units = {limit: self._prefix(breaking, limit) for limit in levels}
        others = len(rest) + hidden
        for surface in dict.fromkeys((surface_line, "")):
            fixed = (header, surface)
            # Every breaking change at full length, and as many listed changes as fit.
            count = self._fit(
                [
                    self._size(
                        fixed,
                        breaking_units[full][-1] + listed_units[n],
                        self._tail(changes, 0, others - n, link),
                    )
                    for n in range(len(listed) + 1)
                ]
            )
            if count is not None:
                tail = self._tail(changes, 0, others - count, link)
                return self._assemble(
                    header, breaking, listed[:count], full, surface, tail, len(surfaces)
                )
            # No listed change; every breaking change, shorter and shorter.
            for limit in levels[1:]:
                tail = self._tail(changes, 0, others, link)
                if self._size(fixed, breaking_units[limit][-1], tail) <= cfg.max_message_chars:
                    return self._assemble(header, breaking, [], limit, surface, tail, len(surfaces))
            # As many breaking changes as fit at the shortest, the rest counted as breaking.
            shortest = levels[-1]
            count = self._fit(
                [
                    self._size(
                        fixed,
                        breaking_units[shortest][n],
                        self._tail(changes, len(breaking) - n, others, link),
                    )
                    for n in range(len(breaking) + 1)
                ]
            )
            if count is not None:
                tail = self._tail(changes, len(breaking) - count, others, link)
                return self._assemble(
                    header, breaking[:count], [], shortest, surface, tail, len(surfaces)
                )
        tail = self._tail(changes, len(breaking), others, link)
        cut = self._assemble(header, [], [], full, "", tail)
        return Announcement(self._hard_cut(cut.content, cfg.max_message_chars))

    def _prefix(self, shown: Sequence[Change], limit: int) -> list[int]:
        """`units[n]`: what the first `n` changes cost, lines and group headings, each with
        the newline before it."""
        units = [0]
        group = ""
        for change in shown:
            cost = _units(self._line(change, limit)) + 1
            if change.group != group:
                group = change.group
                cost += _units(f"**{self.escape(group)}**") + 1
            units.append(units[-1] + cost)
        return units

    def _tail(self, changes: ChangeSet, cut_breaking: int, cut: int, link: str) -> str:
        """The line after the list: what was left out, counted, and where to read it all."""
        more = cut + changes.unread
        tail = []
        if cut_breaking:
            tail.append(f"**+{_plural(cut_breaking, 'more breaking change')}**")
        if more:
            tail.append(f"…and {more} more")
        if changes.noise:
            tail.append(f"+{_plural(changes.noise, 'maintenance commit')}")
        if link:
            tail.append(link)
        return " · ".join(tail)

    @staticmethod
    def _size(fixed: Sequence[str], lines: int, tail: str) -> int:
        """The rendered length, in units, without rendering it: the header and the optional
        lines, each after a newline but the first, plus the listed lines' prefix cost."""
        parts = [part for part in (*fixed, tail) if part]
        return sum(_units(part) for part in parts) + len(parts) - 1 + lines

    def _fit(self, sizes: Sequence[int]) -> int | None:
        """The largest `n` whose message, `sizes[n]` units long, fits; None when none does.
        Each size is arithmetic on prefix sums, so the whole choice is linear."""
        for count in range(len(sizes) - 1, -1, -1):
            if sizes[count] <= self._cfg.max_message_chars:
                return count
        return None

    def _assemble(
        self,
        header: str,
        breaking: Sequence[Change],
        listed: Sequence[Change],
        limit: int,
        surface: str,
        tail: str,
        links: int = 0,
    ) -> Announcement:
        body = [header]
        group = ""
        for change in [*breaking, *listed]:
            if change.group != group:
                group = change.group
                body.append(f"**{self.escape(group)}**")
            body.append(self._line(change, limit))
        body.extend(part for part in (tail, surface) if part)
        return Announcement(
            "\n".join(body),
            listed=len(breaking) + len(listed),
            surfaces=links if surface else 0,
        )

    @staticmethod
    def _hard_cut(content: str, limit: int) -> str:
        """The backstop no ordinary message reaches: cut to fit, ending in an ellipsis."""
        while _units(content) > limit - 1:
            content = content[:-1]
        return content + "…"


class DiscordWebhook(WebhookPosterInterface):
    """Implements `WebhookPosterInterface` for a Discord webhook, with the stdlib client."""

    def __init__(self, *, timeout: float = 30.0) -> None:
        self._timeout = timeout

    @staticmethod
    def redact(text: str, url: str) -> str:
        """`text` with the webhook, and any other URL, removed: the URL IS the credential.

        Removed whole, then by its path, its path quoted, and each long piece of it, because
        a client error quotes whichever of those it choked on (http.client names the PATH
        when it holds a space), and GitHub's log masking only matches the secret's full
        value, never a fragment of it.
        """
        if url:
            pieces = [url]
            try:
                path = urllib.parse.urlsplit(url).path
            except ValueError:
                path = ""
            if len(path) > 1:
                pieces += [path, urllib.parse.quote(path)]
                # Each long segment of the path on its own: the id and the token.
                pieces += [
                    part
                    for part in re.split(r"[/\s?#&=]", path)
                    if len(part) >= 6 and part not in ("webhooks", "<webhook>")
                ]
            for piece in sorted(pieces, key=len, reverse=True):
                text = text.replace(piece, "<webhook>")
        text = re.sub(r"/api/webhooks/\S+", "/api/webhooks/<webhook>", text)
        return re.sub(r"[A-Za-z][A-Za-z0-9+.-]*://\S+", "<url>", text)

    def post(self, url: str, payload: Mapping[str, Any]) -> tuple[bool, str]:
        if not url.startswith(("https://", "http://")):
            return False, "the webhook is not an http(s) URL"
        try:
            request = urllib.request.Request(
                url,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json", "User-Agent": "vibey-gh announce"},
                method="POST",
            )
            # The scheme is checked just above: http(s) only, never file: or a custom one.
            with urllib.request.urlopen(request, timeout=self._timeout) as response:  # nosec B310
                return True, f"HTTP {response.status}"
        except urllib.error.HTTPError as exc:
            return False, f"HTTP {exc.code}"
        except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError) as exc:
            # `http.client.InvalidURL` (a space or control character inside the secret) is an
            # HTTPException, not a URLError: uncaught, its traceback printed the webhook's path.
            return False, self.redact(f"{type(exc).__name__}: {exc}", url)


class Announcer(AnnouncerInterface):
    """Implements `AnnouncerInterface`. Every collaborator is a seam; the defaults are real."""

    def __init__(
        self,
        cfg: GhConfig,
        history: ReleaseHistoryInterface,
        *,
        composer: ChangelogComposerInterface | None = None,
        poster: WebhookPosterInterface | None = None,
        out: Callable[[str], None] = print,
    ) -> None:
        self._cfg = cfg
        self._history = history
        self._composer = composer
        self._poster = poster or DiscordWebhook()
        self._out = out

    def _composer_for(self, request: AnnounceRequest) -> ChangelogComposerInterface:
        return self._composer or ChangelogComposer(
            self._cfg.announce, request.repository, request.server_url
        )

    @staticmethod
    def surfaces(request: AnnounceRequest) -> tuple[Surface, ...]:
        """The channel site, then every surface this deploy actually produced."""
        owner, name = request.repository.split("/", 1)
        root = f"https://{owner}.github.io/{name}/{request.channel}/"
        found = [Surface("site", root)]
        for path, label in _SURFACES:
            if (request.site_dir / path).is_file():
                found.append(Surface(label, root + path.removesuffix("index.html")))
        return tuple(found)

    def compose(self, request: AnnounceRequest) -> Announcement:
        composer = self._composer_for(request)
        surfaces = self.surfaces(request)
        repo = f"**{composer.escape(request.repository)}**"
        link = f"{request.server_url.rstrip('/')}/{request.repository}"
        if request.branch == self._cfg.release_branch:
            return self._release(request, composer, repo, link, surfaces)
        lead = f"{repo} published `{request.channel}` from `{request.sha[:12]}`"
        position = self._history.previous_position(request.branch, request.sha)
        why, structural = position.reason, position.structural
        base = position.sha
        if base is not None and base.startswith(request.sha):
            announcement = composer.render(
                f"{lead} · already announced", ChangeSet(), surfaces=surfaces
            )
            return dataclasses.replace(announcement, duplicate=True)
        if base is not None:
            found, problem = self._history.compare(base, request.sha)
            if found is not None and found.status in ("ahead", "identical"):
                return composer.render(
                    f"{lead} · changes since `{base[:12]}`:",
                    composer.from_commits(found.commits, found.total - len(found.commits)),
                    more_url=found.html_url,
                    more_label=f"compare {base[:7]}…{request.sha[:7]}",
                    surfaces=surfaces,
                )
            # A compare that answered "diverged" or "behind" is structural (history was
            # rewritten under the last position); one that did not answer is not.
            structural = found is not None
            why = problem or (
                f"the last announced commit {base[:12]} is not behind this one "
                f"({found.status if found is not None else ''}; history was rewritten)"
            )
        return self._one_commit(request, composer, lead, link, surfaces, why, structural)

    def _one_commit(
        self,
        request: AnnounceRequest,
        composer: ChangelogComposerInterface,
        lead: str,
        link: str,
        surfaces: Sequence[Surface],
        why: str,
        structural: bool,
    ) -> Announcement:
        """The fallback when the range is not known: this commit, and what that means.

        Structural: re-anchored here, recorded, and said. Otherwise: said to be unknown, and
        NOT recorded, so the next announcement reads the same span again (10.g).
        """
        reason = composer.escape(why[:160])
        if structural:
            header = f"{lead} · re-anchored here ({reason}) — this commit only:"
        else:
            header = (
                f"{lead} · changes since: unknown ({reason}) — this commit only; "
                "the next announcement covers the span again:"
            )
        record, _problem = self._history.commit(request.sha)
        changes = composer.from_commits([record]) if record is not None else ChangeSet(unread=1)
        announcement = composer.render(
            header,
            changes,
            more_url=f"{link}/commit/{request.sha}",
            more_label="this commit",
            surfaces=surfaces,
        )
        return dataclasses.replace(announcement, position=REANCHORED if structural else UNKNOWN)

    def _release(
        self,
        request: AnnounceRequest,
        composer: ChangelogComposerInterface,
        repo: str,
        link: str,
        surfaces: Sequence[Surface],
    ) -> Announcement:
        """A release announces its own notes, and the tag range when one resolves."""
        cfg = self._cfg
        version = request.version
        if not version:
            try:
                version = read_version(cfg)
            except (RuntimeError, OSError, ValueError):
                version = ""
        notes: ReleaseNotes | None = None
        changelog = cfg.root / cfg.announce.changelog_path
        if version and changelog.is_file():
            notes = composer.from_changelog(changelog.read_text(encoding="utf-8"), version)
        found: CommitRange | None = None
        why = f"no earlier version in {cfg.announce.changelog_path}"
        tag = ""
        if notes is not None and notes.previous_version:
            tag = f"{cfg.github_release.tag_prefix}{notes.previous_version}"
            found, why = self._history.compare(tag, request.sha)
            if found is not None and found.status not in ("ahead", "identical"):
                why, found = f"{tag} is not behind this commit ({found.status})", None
        titled = f"**{composer.escape(version)}**" if version else "a release"
        lead = f"{repo} released {titled} on `{request.channel}` from `{request.sha[:12]}`"
        compare = f"compare {tag}…{request.sha[:7]}"
        if notes is not None:
            if found is not None:
                since = f"{_plural(found.total, 'commit')} since `{tag}`"
                more_url, more_label = found.html_url, compare
            else:
                since = f"tag range unavailable ({composer.escape(why[:160])})"
                more_url = f"{link}/blob/{request.sha}/{cfg.announce.changelog_path}"
                more_label = "full changelog"
            return composer.render(
                f"{lead} · release notes, {since}:",
                notes.changes,
                more_url=more_url,
                more_label=more_label,
                surfaces=surfaces,
            )
        # A release is not ranged by the Actions history, so this is the one case that is
        # neither: the release has no notes to announce, which reading again will not change.
        missing = f"no {cfg.announce.changelog_path} section for {version or 'this version'}"
        return self._one_commit(request, composer, lead, link, surfaces, missing, True)

    def payload(self, announcement: Announcement) -> dict[str, Any]:
        """The webhook body: the message, and the switches that keep it inert."""
        body: dict[str, Any] = {
            "username": self._cfg.announce.username,
            "content": announcement.content,
            "allowed_mentions": {"parse": []},
        }
        if self._cfg.announce.suppress_embeds:
            body["flags"] = _SUPPRESS_EMBEDS
        return body

    def run(
        self,
        request: AnnounceRequest,
        webhook_url: str,
        *,
        dry_run: bool = False,
        github_output: str = "",
    ) -> int:
        settings = self._cfg.announce
        posted = False
        position = UNKNOWN
        if not settings.enabled:
            self._out("announce: [announce] enabled = false; nothing posted")
        elif not webhook_url and not dry_run:
            self._out(f"announce: no {settings.webhook_secret} secret is set; nothing posted")
        else:
            announcement = self.compose(request)
            position = announcement.position
            if dry_run:
                self._out(announcement.content)
            elif announcement.duplicate:
                # De-duplicated by identity: this commit's announcement was already accepted
                # for this branch (a re-run, or a replayed deploy), so it is not posted twice.
                self._out(
                    f"announce: {request.sha[:12]} was already announced for {request.branch}; "
                    "nothing posted"
                )
            else:
                posted, detail = self._poster.post(webhook_url, self.payload(announcement))
                if posted:
                    self._out(
                        f"announce: posted {_plural(announcement.listed, 'change')} and "
                        f"{_plural(announcement.surfaces, 'surface link')} to Discord "
                        f"({detail}); position {position}"
                    )
                else:
                    self._out(
                        "::warning::announce: the Discord webhook post failed and the deploy "
                        f"stands: {DiscordWebhook.redact(detail, webhook_url)}"
                    )
        if github_output:
            with open(github_output, "a", encoding="utf-8") as handle:
                handle.write(f"posted={'true' if posted else 'false'}\nposition={position}\n")
        return 0

    @staticmethod
    def declare(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        """Add the command's arguments to `parser`."""
        parser.add_argument("--channel", required=True, help="the published channel, e.g. develop")
        parser.add_argument("--branch", required=True, help="the branch that released it")
        parser.add_argument("--sha", required=True, help="the release commit it was built from")
        parser.add_argument(
            "--site-dir", default="channel-site", help="the built site, to find its surfaces"
        )
        parser.add_argument(
            "--version", default="", help="the released version (default: the version files)"
        )
        parser.add_argument(
            "--repository",
            default=os.environ.get("GITHUB_REPOSITORY", ""),
            help="owner/name (default: $GITHUB_REPOSITORY)",
        )
        parser.add_argument(
            "--server-url",
            default=os.environ.get("GITHUB_SERVER_URL", "https://github.com"),
            help="the forge's web root (default: $GITHUB_SERVER_URL)",
        )
        parser.add_argument(
            "--run-id",
            default=os.environ.get("GITHUB_RUN_ID", ""),
            help="this workflow run (default: $GITHUB_RUN_ID)",
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="print the message and post nothing"
        )
        return parser

    @classmethod
    def dispatch(cls, args: argparse.Namespace) -> int:
        """Run parsed arguments with the production collaborators; the exit status."""
        cfg = load_config()
        request = AnnounceRequest(
            channel=args.channel,
            branch=args.branch,
            sha=args.sha,
            repository=args.repository,
            server_url=args.server_url,
            site_dir=Path(args.site_dir),
            version=args.version,
        )
        history = ReleaseHistory(
            request.repository,
            args.run_id,
            pages=cfg.announce.max_history_pages,
            candidates=cfg.announce.max_history_candidates,
        )
        return cls(cfg, history).run(
            request,
            os.environ.get(WEBHOOK_ENV, ""),
            dry_run=args.dry_run,
            github_output=os.environ.get("GITHUB_OUTPUT", ""),
        )
