# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey-gh forge-snapshot`: the forge's own state, read out into plain files the project owns.

A project's code is in git and survives any host. Its issues, pull requests, reviews and
releases are not: they live in the forge's database, and leave only on the forge's terms.
This is the first, deliberately small slice of vibey#136, which wants every one of them held
as a lossless record the project owns. It reads a GitHub repository and writes what it
finds to plain JSON Lines on disk:

- one file per artifact class, `<DIR>/<class>.jsonl`, append-only;
- each line one record: a forge-neutral envelope around the forge's native JSON, verbatim;
- each record sealed with a SHA-256 over its canonical form, and linked to the record before
  it in the same file, so a line removed, reordered or edited breaks the chain;
- `<DIR>/manifest.json`, naming what happened to every class — captured, could not look, or
  not selected — and every class it never captures, each with its reason.

It is read-only against the forge, and writes nothing into the vibey ledger: that writer
needs the storage tiers of vibey#114 and is a later slice. Only the envelope is neutral;
each payload stays exactly what the forge returned, so no meaning is lost to a translation
that a later slice might want to make differently. The schema is documented, human-first,
in `docs/forge-snapshot.md`.

Every call goes through `GhTransportInterface.survey`, which answers with a problem string
rather than an empty list when the forge cannot be asked. That distinction is the point of
the whole command: a class it could not look at is recorded as such, its file untouched and
its resume point unmoved, and is never written down as having nothing in it.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from functools import partial
from pathlib import Path
from typing import Any

from vibey_gh.interfaces.forge_snapshot_interface import (
    AppendOutcome,
    ChainHead,
    ForgeRead,
    ForgeReaderInterface,
    ForgeSnapshotInterface,
    Observation,
    SnapshotStoreInterface,
)
from vibey_gh.interfaces.gh_transport_interface import GhTransportInterface

__all__ = [
    "CLASSES",
    "EXCLUDED",
    "MANIFEST_NAME",
    "MANIFEST_SCHEMA",
    "RECORD_SCHEMA",
    "ForgeClass",
    "ForgeSnapshot",
    "GithubForgeReader",
    "JsonlSnapshotStore",
    "SnapshotStoreError",
    "canonical_bytes",
    "digest",
    "moment",
    "stamp",
]

RECORD_SCHEMA = "vibey.forge-record/1"
MANIFEST_SCHEMA = "vibey.forge-manifest/1"
MANIFEST_NAME = "manifest.json"
# The word `--since` accepts in place of a moment: the resume point the last manifest left.
RESUME = "resume"
# `owner/name`, as the forge spells a repository. Checked because it is spliced into every
# API path; a value that is not one would ask the forge about something else entirely.
_REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
# The largest page GitHub's REST listings serve. Fewer is allowed; more is silently capped,
# which would break the short-page test that tells the change-request walk it is done.
_MAX_PER_PAGE = 100


@dataclass(frozen=True)
class ForgeClass:
    """One artifact class: its forge-neutral name, GitHub's name for it, and how it is walked.

    `endpoint` is the REST listing, with `{repository}` and `{per_page}` to fill in (and
    `{number}` for a class listed per change request). `since` says the endpoint filters by
    update time itself. `cursor` says a capture of this class can be resumed from a moment,
    which is true of every class whose walk is bounded by one, directly or through the
    change requests it hangs off.
    """

    name: str
    native_class: str
    endpoint: str
    id_field: str = "id"
    since: bool = False
    cursor: bool = False

    @classmethod
    def named(cls, name: str) -> ForgeClass:
        """The class a forge-neutral name stands for. Raises `ValueError` for any other."""
        for spec in CLASSES:
            if spec.name == name:
                return spec
        supported = ", ".join(spec.name for spec in CLASSES)
        raise ValueError(f"unknown artifact class {name!r}; supported: {supported}")


# The order is the order of a capture. Reviews come after change requests because they are
# found through them, and one walk of the change requests serves both.
CLASSES: tuple[ForgeClass, ...] = (
    ForgeClass(
        "issue",
        "issue",
        "repos/{repository}/issues?state=all&sort=updated&direction=asc&per_page={per_page}",
        since=True,
        cursor=True,
    ),
    ForgeClass(
        "comment",
        "issue_comment",
        "repos/{repository}/issues/comments?sort=updated&direction=asc&per_page={per_page}",
        since=True,
        cursor=True,
    ),
    ForgeClass(
        "change-request",
        "pull_request",
        "repos/{repository}/pulls?state=all&sort=updated&direction=desc&per_page={per_page}",
        cursor=True,
    ),
    ForgeClass(
        "review",
        "pull_request_review",
        "repos/{repository}/pulls/{number}/reviews?per_page={per_page}",
        cursor=True,
    ),
    ForgeClass(
        "review-comment",
        "pull_request_review_comment",
        "repos/{repository}/pulls/comments?sort=updated&direction=asc&per_page={per_page}",
        since=True,
        cursor=True,
    ),
    ForgeClass("label", "label", "repos/{repository}/labels?per_page={per_page}"),
    ForgeClass(
        "milestone", "milestone", "repos/{repository}/milestones?state=all&per_page={per_page}"
    ),
    ForgeClass("release", "release", "repos/{repository}/releases?per_page={per_page}"),
    ForgeClass("tag", "tag", "repos/{repository}/tags?per_page={per_page}", id_field="name"),
)

# Every artifact class a GitHub repository exposes that this capture does NOT hold, and why.
# Written into every manifest. The acceptance bar of vibey#136 is that nothing is dropped
# silently: a class is captured, or it is named here with its reason, and a test holds the
# two lists disjoint and the issue's own enumeration inside their union.
EXCLUDED: tuple[tuple[str, str], ...] = (
    (
        "timeline-event",
        (
            "Issue and change-request timelines (label, assignment, milestone, rename,"
            " cross-reference, close and reopen events) are one call per item and are not read."
            " The state those events produced is inside the captured payloads; the sequence of"
            " events is not."
        ),
    ),
    (
        "review-thread",
        (
            "Whether a review thread is resolved, and by whom, exists only in the GraphQL API."
            " Every review comment is captured; its thread's resolution is not."
        ),
    ),
    (
        "reaction",
        (
            "Who reacted, and with what, is one call per item. The per-item reaction totals"
            " inside issue, comment and review-comment payloads are captured."
        ),
    ),
    (
        "edit-history",
        (
            "Earlier versions of an edited body (GraphQL `userContentEdits`) are not read. A"
            " capture records a body as it stands; a later capture records a later edit."
        ),
    ),
    (
        "single-item-detail",
        (
            "Some fields exist only when one item is fetched by number: an issue's `closed_by`,"
            " a change request's `merged_by`, mergeability, and commit, file and line counts."
            " Payloads are kept verbatim as the listings return them, and the listings omit"
            " those fields."
        ),
    ),
    (
        "deletion",
        (
            "A deleted artifact is never returned again, and a capture from a moment cannot"
            " tell deleted from unchanged. There are no tombstones: absence from a full capture"
            " is the only evidence, and nothing here infers anything from it."
        ),
    ),
    (
        "release-asset-content",
        (
            "Every release payload carries its asset manifest: name, label, size, content type,"
            " digest where the forge reports one, download count and URL. The asset bytes"
            " themselves are not downloaded."
        ),
    ),
    ("commit-comment", "Comments on commits are not read."),
    (
        "check-run",
        (
            "Check runs and check suites belong to commits, are listed one commit at a time,"
            " and are not read."
        ),
    ),
    (
        "commit-status",
        "Commit statuses belong to commits, are listed one commit at a time, and are not read.",
    ),
    (
        "workflow-run",
        (
            "Actions workflow runs, jobs, logs and artifacts are not read: their volume, and the"
            " forge's own retention limits on them, make them a slice of their own."
        ),
    ),
    (
        "discussion",
        (
            "Discussions and their comments exist only in the GraphQL API; this capture reads"
            " the REST API."
        ),
    ),
    (
        "project",
        (
            "Projects belong to a user or an organisation rather than to the repository, and"
            " exist only in the GraphQL API."
        ),
    ),
    (
        "ruleset",
        (
            "Repository rulesets are not read. vibey-gh declares the ones it manages in"
            " `.vibey-gh.toml` and reconciles them with `vibey-gh rulesets`, so the intended"
            " configuration is already code."
        ),
    ),
    ("branch-protection", "Classic branch protection needs administration permission to read."),
    (
        "repository-metadata",
        (
            "The repository object and its settings are not read. The settings vibey-gh manages"
            " are declared in `[repository_profile]` of `.vibey-gh.toml`."
        ),
    ),
    (
        "collaborator",
        (
            "Collaborators, teams, invitations and their permissions need administration"
            " permission, and are personal data beyond the account references the captured"
            " payloads already carry."
        ),
    ),
    (
        "git-object",
        (
            "Commits, trees, blobs and branch heads, `refs/pull/*` among them, are the git"
            " repository itself, and `git clone --mirror` is its lossless snapshot. Tags are"
            " captured as the forge lists them: a name and the commit it points at."
        ),
    ),
    (
        "wiki",
        (
            "The wiki is a git repository of its own, `<repository>.wiki.git`, and is kept by"
            " cloning it; the API does not serve it."
        ),
    ),
    ("deployment", "Deployments, deployment statuses and environments are not read."),
    (
        "webhook",
        (
            "Repository webhooks need administration permission, and their configuration holds"
            " secrets."
        ),
    ),
    (
        "secret",
        (
            "Actions, Dependabot and Codespaces secrets are write-only by design: the forge never"
            " returns a value, and nothing here asks for one."
        ),
    ),
    ("variable", "Actions variables are not read."),
    (
        "security-alert",
        (
            "Code scanning, secret scanning and Dependabot alerts, and repository security"
            " advisories, are permission-gated and security-sensitive, and are not read."
        ),
    ),
    ("package", "Packages belong to the owning account, not to the repository."),
    (
        "stargazer-watcher-fork",
        (
            "Stars, watchers and forks are other accounts' relationships to the repository, not"
            " state the repository holds."
        ),
    ),
    (
        "traffic",
        (
            "Traffic views, clones and referrers are a rolling fourteen-day window the forge"
            " discards, and need push access."
        ),
    ),
    ("pages", "The GitHub Pages site configuration is not read."),
    ("sub-issue", "Sub-issue links and issue types are not read."),
    ("pinned-issue", "Which issues are pinned exists only in the GraphQL API."),
    ("autolink", "Autolink references need administration permission to read."),
    ("deploy-key", "Deploy keys need administration permission to read."),
    (
        "custom-property",
        "Repository custom properties are set by the organisation, and are not read.",
    ),
)

_NOT_SELECTED = "not selected for this capture; its file and its chain were left untouched"


class SnapshotStoreError(RuntimeError):
    """A snapshot directory holds something this store did not write, or did not finish."""


# Module-level rather than methods (vibey ADR-0016): the canonical form and the two moment
# conversions below are pure functions of their input, which the store, the reader, the
# snapshot, the tests and the verifier of a later slice must all compute identically. A
# class would add a seam with nothing behind it that could ever be swapped.
def canonical_bytes(value: object) -> bytes:
    """The one serialisation every digest here is taken over.

    Byte for byte the vibey ledger's (`vibey.domain.ledger.canonical_bytes`): sorted keys,
    compact separators, ASCII-escaped, UTF-8. A record hashed here hashes the same there,
    which is what lets a later slice move these records into the ledger without re-sealing
    any of them. Repeated rather than imported because vibey-gh depends on nothing, vibey
    included; `test_forge_snapshot.py` holds the two equal whenever both are installed.
    """
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()


# Module-level: see `canonical_bytes`.
def digest(value: object) -> str:
    """The SHA-256 of `value`'s canonical form, as lowercase hex."""
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


# Module-level: see `canonical_bytes`.
def moment(value: str) -> datetime:
    """Read an ISO 8601 moment; one with no offset is taken to be UTC. Raises `ValueError`."""
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


# Module-level: see `canonical_bytes`.
def stamp(value: datetime) -> str:
    """Write a moment the way GitHub does: UTC, to the second, `Z`-suffixed.

    Whole seconds only, so a moment written here compares equal to the forge's own. Dropping
    a fraction moves a `since` earlier, never later, which captures more and never less.
    """
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class GithubForgeReader(ForgeReaderInterface):
    """Reads a GitHub repository's artifact classes through the REST API, never writing.

    Listings are fetched with `gh api --paginate --slurp`, so every page is read and each
    page arrives as its own JSON array in one outer array. `--slurp` needs GitHub CLI 2.48 or
    later; an older client refuses the flag, and the class is recorded as one it could not
    look at, which is the honest outcome. Change requests are the exception: GitHub cannot
    filter them by update time, so they are paged by hand, newest update first, and the walk
    stops at the first one older than `since` instead of fetching every page to discard most.
    """

    forge = "github"

    def __init__(
        self,
        transport: GhTransportInterface,
        repository: str,
        *,
        per_page: int = _MAX_PER_PAGE,
    ) -> None:
        if not _REPOSITORY.fullmatch(repository):
            raise ValueError(f"not an owner/name repository: {repository!r}")
        if not 1 <= per_page <= _MAX_PER_PAGE:
            raise ValueError(f"per_page must be between 1 and {_MAX_PER_PAGE}: {per_page}")
        self.repository = repository
        self._transport = transport
        self._per_page = per_page
        # One walk of the change requests per moment serves both them and their reviews.
        self._change_requests: dict[str | None, ForgeRead] = {}

    def read(self, forge_class: str, since: str | None) -> ForgeRead:
        spec = ForgeClass.named(forge_class)
        if spec.name == "change-request":
            return self._pull_requests(spec, since)
        if spec.name == "review":
            return self._reviews(spec, since)
        path = spec.endpoint.format(repository=self.repository, per_page=self._per_page)
        if spec.since and since is not None:
            path += f"&since={since}"
        items, problem = self._listing(path)
        if problem:
            return ForgeRead(spec.name, spec.native_class, problem=problem)
        return self._observed(spec, items, self._high_water(items) if spec.cursor else None)

    def _listing(self, path: str) -> tuple[list[dict[str, Any]], str]:
        """Every item of a paginated listing, or the reason there are none to give."""
        value, problem = self._transport.survey(["api", path, "--paginate", "--slurp"])
        if problem:
            return [], problem
        if not isinstance(value, list) or not all(isinstance(page, list) for page in value):
            return [], f"`api {path}` did not answer with a list of pages"
        items = [item for page in value for item in page]
        if not all(isinstance(item, dict) for item in items):
            return [], f"`api {path}` listed something that is not a JSON object"
        return items, ""

    def _pull_requests(self, spec: ForgeClass, since: str | None) -> ForgeRead:
        if since in self._change_requests:
            return self._change_requests[since]
        base = spec.endpoint.format(repository=self.repository, per_page=self._per_page)
        cutoff = moment(since) if since is not None else None
        items: list[dict[str, Any]] = []
        page = 1
        while True:
            path = f"{base}&page={page}"
            value, problem = self._transport.survey(["api", path])
            if problem:
                result = ForgeRead(spec.name, spec.native_class, problem=problem)
                break
            if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
                result = ForgeRead(
                    spec.name,
                    spec.native_class,
                    problem=f"`api {path}` did not answer with a list of JSON objects",
                )
                break
            fresh = [item for item in value if not self._older(item, cutoff)]
            items.extend(fresh)
            if len(fresh) < len(value) or len(value) < self._per_page:
                result = self._observed(spec, items, self._high_water(items))
                break
            page += 1
        self._change_requests[since] = result
        return result

    def _reviews(self, spec: ForgeClass, since: str | None) -> ForgeRead:
        pulls = self._pull_requests(ForgeClass.named("change-request"), since)
        if pulls.problem:
            return ForgeRead(
                spec.name,
                spec.native_class,
                problem=f"the change requests these reviews belong to could not be listed:"
                f" {pulls.problem}",
            )
        items: list[dict[str, Any]] = []
        for native_id, pull in pulls.observations:
            number = pull.get("number")
            if not isinstance(number, int) or isinstance(number, bool):
                return ForgeRead(
                    spec.name,
                    spec.native_class,
                    problem=f"change request {native_id} has no number to list its reviews by",
                )
            found, problem = self._listing(
                spec.endpoint.format(
                    repository=self.repository, number=number, per_page=self._per_page
                )
            )
            if problem:
                return ForgeRead(spec.name, spec.native_class, problem=problem)
            items.extend(found)
        # A review carries no update time of its own. Submitting, editing or dismissing one
        # updates its change request, so the change requests' high water bounds the reviews.
        return self._observed(spec, items, pulls.high_water)

    @staticmethod
    def _observed(
        spec: ForgeClass, items: Sequence[dict[str, Any]], high_water: str | None
    ) -> ForgeRead:
        observations: list[Observation] = []
        for item in items:
            native_id = item.get(spec.id_field)
            if (
                not isinstance(native_id, (int, str))
                or isinstance(native_id, bool)
                or native_id == ""
            ):
                return ForgeRead(
                    spec.name,
                    spec.native_class,
                    problem=f"the forge listed a {spec.native_class} with no `{spec.id_field}`",
                )
            observations.append((str(native_id), item))
        return ForgeRead(spec.name, spec.native_class, tuple(observations), high_water)

    @staticmethod
    def _updated(item: Mapping[str, Any]) -> datetime | None:
        value = item.get("updated_at")
        try:
            return moment(value) if isinstance(value, str) else None
        except ValueError:
            return None

    @classmethod
    def _older(cls, item: Mapping[str, Any], cutoff: datetime | None) -> bool:
        updated = cls._updated(item)
        return cutoff is not None and updated is not None and updated < cutoff

    @classmethod
    def _high_water(cls, items: Iterable[Mapping[str, Any]]) -> str | None:
        moments = [value for value in map(cls._updated, items) if value is not None]
        return stamp(max(moments)) if moments else None


@dataclass
class _Chain:
    """One class's chain as loaded: its length, its head, the latest content per object."""

    records: int = 0
    head: str | None = None
    latest: dict[tuple[str, str], str] = field(default_factory=dict)


class JsonlSnapshotStore(SnapshotStoreInterface):
    """Keeps a snapshot as `<root>/<class>.jsonl` files and `<root>/manifest.json`.

    Each line of a class file is one record in canonical form (`canonical_bytes`), so the
    bytes on disk are the bytes the digests were taken over, less the `sha256` field. A file
    is only ever appended to, and the store reads it back whole before the first append of a
    run: that is where the chain's head and the latest content of every object come from,
    and where a file holding anything else is refused rather than extended.

    One writer at a time. Two captures appending to one directory at once would interleave
    two chains into one file.
    """

    def __init__(self, root: Path, *, forge: str, repository: str) -> None:
        self._root = root
        self._forge = forge
        self._repository = repository
        self._chains: dict[str, _Chain] = {}

    def path(self, forge_class: str) -> Path:
        """Where one class's records live."""
        return self._root / f"{forge_class}.jsonl"

    def manifest(self) -> Mapping[str, Any] | None:
        path = self._root / MANIFEST_NAME
        if not path.is_file():
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as error:
            raise SnapshotStoreError(f"{path} is not JSON: {error}") from error
        if not isinstance(value, dict) or value.get("schema") != MANIFEST_SCHEMA:
            raise SnapshotStoreError(f"{path} is not a {MANIFEST_SCHEMA} manifest")
        if (value.get("forge"), value.get("repository")) != (self._forge, self._repository):
            raise SnapshotStoreError(
                f"{path} describes {value.get('forge')} {value.get('repository')}, not"
                f" {self._forge} {self._repository}; a snapshot directory holds one repository"
            )
        return value

    def chain(self, forge_class: str) -> ChainHead:
        loaded = self._load(forge_class)
        return ChainHead(loaded.records, loaded.head)

    def append(
        self,
        forge_class: str,
        native_class: str,
        captured_at: str,
        observations: Sequence[Observation],
    ) -> AppendOutcome:
        loaded = self._load(forge_class)
        lines: list[str] = []
        unchanged = 0
        for native_id, payload in observations:
            content = digest(payload)
            key = (native_class, native_id)
            if loaded.latest.get(key) == content:
                unchanged += 1
                continue
            record: dict[str, Any] = {
                "schema": RECORD_SCHEMA,
                "forge": self._forge,
                "repository": self._repository,
                "class": forge_class,
                "native_class": native_class,
                "native_id": native_id,
                "captured_at": captured_at,
                "payload": payload,
                "payload_sha256": content,
                "prev": loaded.head,
            }
            record["sha256"] = digest(record)
            lines.append(canonical_bytes(record).decode() + "\n")
            loaded.records += 1
            loaded.head = record["sha256"]
            loaded.latest[key] = content
        if lines:
            self._root.mkdir(parents=True, exist_ok=True)
            with self.path(forge_class).open("a", encoding="utf-8") as handle:
                handle.write("".join(lines))
        return AppendOutcome(len(lines), unchanged, loaded.records, loaded.head)

    def write_manifest(self, manifest: Mapping[str, Any]) -> Path:
        self._root.mkdir(parents=True, exist_ok=True)
        path = self._root / MANIFEST_NAME
        partial_path = path.with_name(f"{MANIFEST_NAME}.partial")
        partial_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(partial_path, path)
        return path

    def _load(self, forge_class: str) -> _Chain:
        if forge_class in self._chains:
            return self._chains[forge_class]
        loaded = _Chain()
        path = self.path(forge_class)
        if path.is_file():
            # Bytes, not text: `json.loads` decodes each line itself, so a line that is not
            # UTF-8 is refused as a bad record like any other rather than escaping as an
            # error from the middle of the loop.
            with path.open("rb") as handle:
                for number, line in enumerate(handle, start=1):
                    record = self._parse(path, number, line, forge_class)
                    loaded.records += 1
                    loaded.head = record["sha256"]
                    loaded.latest[(record["native_class"], record["native_id"])] = record[
                        "payload_sha256"
                    ]
        self._chains[forge_class] = loaded
        return loaded

    def _parse(self, path: Path, number: int, line: bytes, forge_class: str) -> dict[str, Any]:
        try:
            record = json.loads(line)
        except ValueError:
            record = None
        expected = {
            "schema": RECORD_SCHEMA,
            "forge": self._forge,
            "repository": self._repository,
            "class": forge_class,
        }
        if (
            not isinstance(record, dict)
            or any(record.get(key) != value for key, value in expected.items())
            or not all(
                isinstance(record.get(key), str)
                for key in ("native_class", "native_id", "payload_sha256", "sha256")
            )
        ):
            raise SnapshotStoreError(
                f"{path} line {number} is not a {RECORD_SCHEMA} {forge_class} record of"
                f" {self._forge} {self._repository}. These files are only ever appended to"
                " by this command, so that line was written by something else or not"
                " written completely; nothing was appended after it."
            )
        return record


class ForgeSnapshot(ForgeSnapshotInterface):
    """Runs a capture: every selected class read and appended, every class accounted for."""

    def __init__(
        self,
        reader: ForgeReaderInterface,
        store: SnapshotStoreInterface,
        *,
        clock: Callable[[], datetime] | None = None,
        clock_skew: timedelta = timedelta(minutes=5),
        excluded: Sequence[tuple[str, str]] = EXCLUDED,
    ) -> None:
        """`clock` is this machine's; `clock_skew` is how far ahead of the forge's it may run.

        A class that was walked but reported no update time, because it is empty or quiet,
        still has to be resumable, or one empty class would hold every resume point back
        for good. Its cursor comes from this machine's clock instead, taken back by
        `clock_skew` so that a clock running ahead of the forge's cannot carry a cursor past
        anything the forge has yet to report. Anything the allowance re-reads is counted as
        unchanged, so a generous one costs calls, never records.
        """
        if clock_skew < timedelta(0):
            raise ValueError(f"clock_skew must not be negative: {clock_skew}")
        self._reader = reader
        self._store = store
        self._clock = clock if clock is not None else partial(datetime.now, UTC)
        self._clock_skew = clock_skew
        self._excluded = tuple(excluded)

    def capture(
        self,
        *,
        classes: Sequence[str] | None = None,
        since: str | None = None,
    ) -> dict[str, Any]:
        selected = self._select(classes)
        previous = self._store.manifest() or {}
        since = self._since(since, previous)
        # Every chain is loaded, and so checked, before the forge is asked anything, so a
        # directory that cannot be appended to is refused with nothing written.
        chains = {spec.name: self._store.chain(spec.name) for spec in CLASSES}
        began = self._clock()
        started = stamp(began)
        # Taken from the start of the whole capture, not of each walk: a later walk can rest
        # on an earlier one (reviews on the change-request walk), and this bound is earlier
        # than both.
        floor = stamp(began - self._clock_skew)
        entries: dict[str, dict[str, Any]] = {}
        for spec in CLASSES:
            prior = self._prior_cursor(previous, spec.name)
            if spec.name not in selected:
                entries[spec.name] = self._entry(spec, "not-selected", chains[spec.name], prior)
                continue
            captured_at = stamp(self._clock())
            read = self._reader.read(spec.name, since)
            if read.problem:
                entries[spec.name] = self._entry(
                    spec,
                    "could-not-look",
                    chains[spec.name],
                    prior,
                    captured_at=captured_at,
                    problem=read.problem,
                )
                continue
            outcome = self._store.append(
                spec.name, spec.native_class, captured_at, read.observations
            )
            entries[spec.name] = {
                **self._entry(
                    spec,
                    "captured",
                    ChainHead(outcome.records, outcome.head),
                    self._cursor(prior, since, read.high_water, floor) if spec.cursor else None,
                    captured_at=captured_at,
                ),
                "observed": len(read.observations),
                "appended": outcome.appended,
                "unchanged": outcome.unchanged,
            }
        cursors = [entries[spec.name]["cursor"] for spec in CLASSES if spec.cursor]
        manifest: dict[str, Any] = {
            "schema": MANIFEST_SCHEMA,
            "record_schema": RECORD_SCHEMA,
            "forge": self._reader.forge,
            "repository": self._reader.repository,
            "captured_at": started,
            "since": since,
            "clock_skew_seconds": int(self._clock_skew.total_seconds()),
            "complete": all(entries[name]["status"] == "captured" for name in selected),
            # One moment a later `--since` can start from without missing anything any
            # resumable class has not yet captured: the earliest of their cursors, and only
            # when every one of them has one.
            "resume_since": (
                min(cursors, key=moment) if all(cursor is not None for cursor in cursors) else None
            ),
            "classes": entries,
            "excluded": [{"class": name, "reason": reason} for name, reason in self._excluded]
            + [
                {"class": spec.name, "reason": _NOT_SELECTED}
                for spec in CLASSES
                if spec.name not in selected
            ],
        }
        self._store.write_manifest(manifest)
        return manifest

    @staticmethod
    def _select(classes: Sequence[str] | None) -> frozenset[str]:
        if classes is None:
            return frozenset(spec.name for spec in CLASSES)
        if not classes:
            raise ValueError("no artifact class selected")
        return frozenset(ForgeClass.named(name).name for name in classes)

    @staticmethod
    def _since(since: str | None, previous: Mapping[str, Any]) -> str | None:
        if since == RESUME:
            resume = previous.get("resume_since")
            since = resume if isinstance(resume, str) else None
        if since is None:
            return None
        try:
            return stamp(moment(since))
        except ValueError as error:
            raise ValueError(f"not an ISO 8601 moment: {since!r}") from error

    @staticmethod
    def _cursor(
        prior: str | None, since: str | None, high_water: str | None, floor: str
    ) -> str | None:
        """Where a resumable class can next start from, after a walk that completed.

        A walk from a moment later than the class's cursor, or from any moment at all when
        the class has none, left a stretch of its history unwalked. The cursor then stays
        where it was, so that `--since resume` starts at the gap and fills it rather than
        stepping over it. Otherwise it moves to the latest of the old cursor, the latest
        update time the forge reported, and `floor`.
        """
        if since is not None and (prior is None or moment(since) > moment(prior)):
            return prior
        return ForgeSnapshot._latest(prior, high_water, floor)

    @staticmethod
    def _prior_cursor(previous: Mapping[str, Any], name: str) -> str | None:
        classes = previous.get("classes")
        entry = classes.get(name) if isinstance(classes, dict) else None
        cursor = entry.get("cursor") if isinstance(entry, dict) else None
        return ForgeSnapshot._latest(cursor)

    @staticmethod
    def _latest(*values: object) -> str | None:
        """The latest of the readable moments among `values`, or `None` when there is none."""
        moments: list[datetime] = []
        for value in values:
            if not isinstance(value, str):
                continue
            try:
                moments.append(moment(value))
            except ValueError:
                continue
        return stamp(max(moments)) if moments else None

    @staticmethod
    def _entry(
        spec: ForgeClass,
        status: str,
        chain: ChainHead,
        cursor: str | None,
        *,
        captured_at: str | None = None,
        problem: str = "",
    ) -> dict[str, Any]:
        return {
            "native_class": spec.native_class,
            "status": status,
            "problem": problem,
            "captured_at": captured_at,
            "observed": None,
            "appended": 0,
            "unchanged": 0,
            "records": chain.records,
            "head": chain.head,
            "cursor": cursor,
        }
