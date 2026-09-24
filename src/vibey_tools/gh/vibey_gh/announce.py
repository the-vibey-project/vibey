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
  (`RUN_TITLE`), and only a run whose `ANNOUNCED_STEP` succeeded (the step that runs only
  after the webhook accepted the post) counts. When that cannot be established the message
  says `changes since: unknown` and falls back to the one commit being published. A release
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
import json
import os
import re
import unicodedata
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from vibey_gh import fingerprints
from vibey_gh.announce_records import (
    HEX_SHA,
    PLAIN_REF,
    Announcement,
    AnnounceRequest,
    Change,
    ChangeSet,
    CommitRange,
    CommitRecord,
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

# A commit or tag this module names in an API path: nothing that could step out of it.
_REF = PLAIN_REF
_SHA = HEX_SHA

_SUBJECT = re.compile(
    r"^(?P<type>[a-z][a-z0-9-]*)(?:\((?P<scope>[^)]*)\))?(?P<bang>!)?: (?P<description>.+)$"
)
_TRAILING_PR = re.compile(r"\s*\(#(?P<number>\d+)\)\s*$")
_PR_REFERENCE = re.compile(r"(?<![\w/&])#(?P<number>\d+)\b")

# Characters a subject could use to reorder or hide text: the C0 and C1 controls, the
# zero-width characters, the bidirectional overrides and isolates, and the byte-order mark.
# Built from code points so the source carries no invisible character of its own.
_INVISIBLE = re.compile(
    "["
    + "".join(
        f"{re.escape(chr(low))}-{re.escape(chr(high))}"
        for low, high in (
            (0x00, 0x1F),
            (0x7F, 0x9F),
            (0x200B, 0x200F),
            (0x202A, 0x202E),
            (0x2060, 0x2069),
            (0xFEFF, 0xFEFF),
        )
    )
    + "]"
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
    """Implements `ReleaseHistoryInterface` over the GitHub REST API through `gh api`."""

    def __init__(
        self,
        repository: str,
        run_id: str,
        *,
        transport: GhTransportInterface | None = None,
        pages: int = 10,
    ) -> None:
        self._repository = repository
        self._run_id = run_id
        self._transport = transport or GhTransport()
        self._pages = pages

    def _api(self, path: str) -> tuple[Any, str]:
        return self._transport.survey(["api", f"repos/{self._repository}/{path}"])

    def previous_position(self, branch: str, head: str) -> tuple[str | None, str]:
        if not self._run_id.isdigit():
            return None, "this run's id is unknown, so its workflow cannot be asked"
        run, problem = self._api(f"actions/runs/{self._run_id}")
        workflow = run.get("workflow_id") if isinstance(run, dict) else None
        if problem or not isinstance(workflow, int):
            return None, f"the Actions API did not name this workflow ({problem or 'no id'})"
        for page in range(1, self._pages + 1):
            data, problem = self._api(
                f"actions/workflows/{workflow}/runs?status=success&per_page=100&page={page}"
            )
            if problem:
                return None, f"the Actions API did not list earlier runs ({problem})"
            runs = data.get("workflow_runs", []) if isinstance(data, dict) else []
            for candidate in runs:
                match = RUN_TITLE.search(str(candidate.get("display_title", "")))
                if match is None or match["branch"] != branch:
                    continue
                announced, why = self._announced(candidate.get("id"))
                if why:
                    return None, why
                if announced:
                    return self._resolve(match["ref"])
            if len(runs) < 100:
                return None, f"no earlier announcement is recorded for {branch}"
        return None, f"no announcement for {branch} in the last {self._pages * 100} runs"

    def _announced(self, run_id: object) -> tuple[bool, str]:
        """Whether run `run_id`'s announcement was accepted, or why that cannot be read."""
        data, problem = self._api(f"actions/runs/{run_id}/jobs?per_page=100")
        if problem:
            return False, f"the Actions API did not list run {run_id}'s jobs ({problem})"
        jobs = data.get("jobs", []) if isinstance(data, dict) else []
        accepted = any(
            step.get("name") == ANNOUNCED_STEP and step.get("conclusion") == "success"
            for job in jobs
            for step in job.get("steps") or []
        )
        return accepted, ""

    def _resolve(self, ref: str) -> tuple[str | None, str]:
        """A run title's reference as a commit: a commit already, or a release run's."""
        if len(ref) == 40 and not ref.isdigit():
            return ref, ""
        run, problem = self._api(f"actions/runs/{ref}")
        sha = run.get("head_sha") if isinstance(run, dict) else None
        if problem or not isinstance(sha, str) or not _SHA.fullmatch(sha):
            return None, f"release run {ref} names no commit ({problem or 'no head_sha'})"
        return sha, ""

    def compare(self, base: str, head: str) -> tuple[CommitRange | None, str]:
        if not (_REF.fullmatch(base) and _REF.fullmatch(head)):
            return None, f"{base!r}...{head!r} is not a range of plain references"
        status, total, html_url = "", 0, ""
        commits: list[CommitRecord] = []
        for page in range(1, self._pages + 1):
            data, problem = self._api(f"compare/{base}...{head}?per_page=100&page={page}")
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
        text = _INVISIBLE.sub(" ", unicodedata.normalize("NFC", text))
        return _MARKDOWN.sub(r"\\\1", " ".join(text.split()))

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
        cut = len(rest) - len(listed)
        cut_breaking = 0
        limit = cfg.max_subject_chars
        surface_line = ""
        if cfg.link_surfaces and surfaces:
            surface_line = "Read: " + " · ".join(
                f"[{self.escape(surface.label)}](<{surface.url}>)" for surface in surfaces
            )
        while True:
            more = cut + hidden + changes.unread
            tail = []
            if cut_breaking:
                tail.append(f"**+{_plural(cut_breaking, 'more breaking change')}**")
            if more:
                tail.append(f"…and {more} more")
            if changes.noise:
                tail.append(f"+{_plural(changes.noise, 'maintenance commit')}")
            if more_url and cfg.link_compare:
                tail.append(f"[{self.escape(more_label or 'full list')}](<{more_url}>)")
            body = [header]
            group = ""
            for change in [*breaking, *listed]:
                if change.group != group:
                    group = change.group
                    body.append(f"**{self.escape(group)}**")
                body.append(self._line(change, limit))
            if tail:
                body.append(" · ".join(tail))
            if surface_line:
                body.append(surface_line)
            content = "\n".join(body)
            if _units(content) <= cfg.max_message_chars:
                break
            # Over the limit: give up the least important thing first. Listed changes go
            # from the end; then breaking lines get shorter; then, only when breaking
            # changes alone cannot fit, the last of them are counted, as breaking.
            if listed:
                listed.pop()
                cut += 1
            elif breaking and limit > 40:
                limit = max(40, limit // 2)
            elif breaking:
                breaking.pop()
                cut_breaking += 1
            elif surface_line:
                surface_line = ""
            else:
                content = self._hard_cut(content, cfg.max_message_chars)
                break
        return Announcement(content, listed=len(breaking) + len(listed), surfaces=len(surfaces))

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
        """`text` with the webhook, and any other URL, removed: the URL IS the credential."""
        if url:
            text = text.replace(url, "<webhook>")
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
        except (urllib.error.URLError, OSError, ValueError) as exc:
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

    def _single(self, request: AnnounceRequest, composer: ChangelogComposerInterface) -> ChangeSet:
        """The fallback when the range is unknown: the one commit being published."""
        record, _problem = self._history.commit(request.sha)
        return composer.from_commits([record]) if record is not None else ChangeSet(unread=1)

    def compose(self, request: AnnounceRequest) -> Announcement:
        composer = self._composer_for(request)
        surfaces = self.surfaces(request)
        repo = f"**{composer.escape(request.repository)}**"
        link = f"{request.server_url.rstrip('/')}/{request.repository}"
        if request.branch == self._cfg.release_branch:
            return self._release(request, composer, repo, link, surfaces)
        lead = f"{repo} published `{request.channel}` from `{request.sha[:12]}`"
        base, why = self._history.previous_position(request.branch, request.sha)
        if base is not None and base.startswith(request.sha):
            return composer.render(
                f"{lead} · no new commits since the last announcement",
                ChangeSet(),
                surfaces=surfaces,
            )
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
            status = found.status if found is not None else ""
            why = problem or f"{base[:12]} is not behind this commit ({status})"
        return composer.render(
            f"{lead} · changes since: unknown ({composer.escape(why[:160])}) — this commit only:",
            self._single(request, composer),
            more_url=f"{link}/commit/{request.sha}",
            more_label="this commit",
            surfaces=surfaces,
        )

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
        missing = f"no {cfg.announce.changelog_path} section for {version or 'this version'}"
        return composer.render(
            f"{lead} · changes since: unknown ({composer.escape(missing)}) — this commit only:",
            self._single(request, composer),
            more_url=f"{link}/commit/{request.sha}",
            more_label="this commit",
            surfaces=surfaces,
        )

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
        if not settings.enabled:
            self._out("announce: [announce] enabled = false; nothing posted")
        elif not webhook_url and not dry_run:
            self._out(f"announce: no {settings.webhook_secret} secret is set; nothing posted")
        else:
            announcement = self.compose(request)
            if dry_run:
                self._out(announcement.content)
            else:
                posted, detail = self._poster.post(webhook_url, self.payload(announcement))
                if posted:
                    self._out(
                        f"announce: posted {_plural(announcement.listed, 'change')} and "
                        f"{_plural(announcement.surfaces, 'surface link')} to Discord ({detail})"
                    )
                else:
                    self._out(
                        "::warning::announce: the Discord webhook post failed and the deploy "
                        f"stands: {DiscordWebhook.redact(detail, webhook_url)}"
                    )
        if github_output:
            with open(github_output, "a", encoding="utf-8") as handle:
                handle.write(f"posted={'true' if posted else 'false'}\n")
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
            request.repository, args.run_id, pages=cfg.announce.max_history_pages
        )
        return cls(cfg, history).run(
            request,
            os.environ.get(WEBHOOK_ENV, ""),
            dry_run=args.dry_run,
            github_output=os.environ.get("GITHUB_OUTPUT", ""),
        )
