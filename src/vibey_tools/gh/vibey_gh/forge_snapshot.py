# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey-gh forge-snapshot`: the forge's own state, read out into plain files the project owns.

A project's code is in git and survives any host. Its issues, pull requests, reviews and
releases are not: they live in the forge's database, and leave only on the forge's terms.
This is the first, deliberately small slice of vibey#136, which wants every one of them held
as a lossless record the project owns. It reads a repository and writes what it
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

Every call goes through a `ForgeAdapterInterface`, which answers with a problem string
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
RESUME = "resume"
_REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
_MAX_PER_PAGE = 100


@dataclass(frozen=True)
class ForgeClass:
    """One artifact class: its forge-neutral name, GitHub's name for it, and how it is walked."""

    name: str
    native_class: str
    endpoint: str
    id_field: str = "id"
    since: bool = False
    cursor: bool = False

    @classmethod
    def named(cls, name: str) -> ForgeClass:
        for spec in CLASSES:
            if spec.name == name:
                return spec
        supported = ", ".join(spec.name for spec in CLASSES)
        raise ValueError(f"unknown artifact class {name!r}; supported: {supported}")


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

EXCLUDED: tuple[tuple[str, str], ...] = (
    ("timeline-event", "Issue and change-request timelines are not read."),
    ("review-thread", "Whether a review thread is resolved exists only in the GraphQL API."),
    ("reaction", "Who reacted is one call per item."),
    ("edit-history", "Earlier versions of an edited body are not read."),
    ("single-item-detail", "Some fields exist only when one item is fetched by number."),
    ("deletion", "A deleted artifact is never returned again."),
    ("release-asset-content", "Asset bytes themselves are not downloaded."),
    ("commit-comment", "Comments on commits are not read."),
    ("check-run", "Check runs belong to commits."),
    ("commit-status", "Commit statuses belong to commits."),
    ("workflow-run", "Actions workflow runs are a slice of their own."),
    ("discussion", "Discussions exist only in the GraphQL API."),
    ("project", "Projects belong to a user or an organisation."),
    ("ruleset", "Repository rulesets are not read."),
    ("branch-protection", "Classic branch protection needs administration permission."),
    ("repository-metadata", "The repository object and its settings are not read."),
    ("collaborator", "Collaborators and their permissions are not read."),
    ("git-object", "Commits, trees, blobs are the git repository itself."),
    ("wiki", "The wiki is a git repository of its own."),
    ("deployment", "Deployments and environments are not read."),
    ("webhook", "Repository webhooks need administration permission."),
    ("secret", "Secrets are write-only by design."),
    ("variable", "Actions variables are not read."),
    ("security-alert", "Security alerts are permission-gated."),
    ("package", "Packages belong to the owning account."),
    ("stargazer-watcher-fork", "Stars, watchers and forks are other accounts' relationships."),
    ("traffic", "Traffic views are a rolling fourteen-day window."),
    ("pages", "The GitHub Pages site configuration is not read."),
    ("sub-issue", "Sub-issue links and issue types are not read."),
    ("pinned-issue", "Which issues are pinned exists only in the GraphQL API."),
    ("autolink", "Autolink references need administration permission."),
    ("deploy-key", "Deploy keys need administration permission."),
    ("custom-property", "Repository custom properties are set by the organisation."),
)

_NOT_SELECTED = "not selected for this capture; its file and its chain were left untouched"


class SnapshotStoreError(RuntimeError):
    """A snapshot directory holds something this store did not write, or did not finish."""


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def moment(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def stamp(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class GithubForgeReader(ForgeReaderInterface):
    """Read GitHub snapshot classes through the existing ``gh`` transport.

    This compatibility reader keeps the snapshot command's established wire contract while
    the forge-neutral adapter reader is adopted by callers one verb at a time. It remains
    behind ``ForgeReaderInterface``: the snapshot orchestration never depends on GitHub's
    response types.
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
                problem=(
                    "the change requests these reviews belong to could not be listed: "
                    f"{pulls.problem}"
                ),
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


class JsonlSnapshotStore(SnapshotStoreInterface):
    def __init__(self, root: Path, *, forge: str, repository: str) -> None:
        self._root = root
        self._forge = forge
        self._repository = repository
        self._chains: dict[str, _Chain] = {}

    def path(self, forge_class: str) -> Path:
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
                f"{path} describes {value.get('forge')} {value.get('repository')}, not {self._forge} {self._repository}"
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
            previous: str | None = None
            with path.open("rb") as handle:
                for number, line in enumerate(handle, start=1):
                    record = self._parse(path, number, line, forge_class, previous)
                    loaded.records += 1
                    loaded.head = record["sha256"]
                    previous = loaded.head
                    loaded.latest[(record["native_class"], record["native_id"])] = record[
                        "payload_sha256"
                    ]
        self._chains[forge_class] = loaded
        return loaded

    def _parse(
        self,
        path: Path,
        number: int,
        line: bytes,
        forge_class: str,
        previous: str | None,
    ) -> dict[str, Any]:
        try:
            record = json.loads(line)
        except (UnicodeError, ValueError):
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
                for key in (
                    "native_class",
                    "native_id",
                    "captured_at",
                    "payload_sha256",
                    "sha256",
                )
            )
            or not (record.get("prev") is None or isinstance(record.get("prev"), str))
            or "payload" not in record
        ):
            raise SnapshotStoreError(
                f"{path} line {number} is not a {RECORD_SCHEMA} {forge_class} record"
            )
        if canonical_bytes(record) != line.removesuffix(b"\n"):
            raise SnapshotStoreError(f"{path} line {number} is not in canonical form")

        sealed = record["sha256"]
        body = {key: value for key, value in record.items() if key != "sha256"}
        if digest(body) != sealed:
            raise SnapshotStoreError(f"{path} line {number} has an invalid sha256")
        if digest(record["payload"]) != record["payload_sha256"]:
            raise SnapshotStoreError(f"{path} line {number} has an invalid payload_sha256")
        if record["prev"] != previous:
            raise SnapshotStoreError(f"{path} line {number} does not link to the preceding record")
        return record


@dataclass
class _Chain:
    records: int = 0
    head: str | None = None
    latest: dict[tuple[str, str], str] = field(default_factory=dict)


class ForgeSnapshot(ForgeSnapshotInterface):
    def __init__(
        self,
        reader: ForgeReaderInterface,
        store: SnapshotStoreInterface,
        *,
        clock: Callable[[], datetime] | None = None,
        clock_skew: timedelta = timedelta(minutes=5),
        excluded: Sequence[tuple[str, str]] = EXCLUDED,
    ) -> None:
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
        chains = {spec.name: self._store.chain(spec.name) for spec in CLASSES}
        began = self._clock()
        started = stamp(began)
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
