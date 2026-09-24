"""What the storm runs next, decided in one place -- and the priority lane that can change it.

The operator's request (2026-09-24): "The system should be able to push a priority item into
the queue and have that run next so that it doesn't have to wait for the other jobs in front
of it." ADR-0054 is the contract, and vibey's PostgreSQL job queue keeps the same one:

1. NEXT MEANS NEXT AFTER WHATEVER IS RUNNING. Lanes run one at a time (8.c) and
   `storm-queue.sh` asks what is next only once no lane is running. Nothing here stops,
   signals or rewrites a running lane; a push changes only which lane starts after it.
2. PRIORITY ITEMS RUN FIRST, FIRST PUSHED FIRST, ahead of every other eligible line of
   `queue.txt`.
3. DEPENDENCIES ARE RESPECTED AND PULLED FORWARD. Pushing an item whose dependencies are not
   integrated prioritises those too, transitively and in dependency order, and the report
   names everything that moved. A push or bump whose dependency can never finish -- it was
   abandoned, or nothing queues it -- is refused, naming it. Eligibility is unchanged: a
   lane starts only when every dependency is in `integrated.txt`.
4. AUTHORISATION. See `Authority`: the operator, or a declared source, running as the
   account that owns the storm. Anything else is refused, recorded and reported (12.j).
   Nothing here reads the forge. Priority never bypasses admission: `storm_trust.py admit`
   still judges a pushed issue when its lane starts, and `lane-verify.py` still refuses
   forbidden paths at publish.
5. RECORDED, APPEND-ONLY, VISIBLE. EVERY request -- one that moved something, one that
   moved nothing, and one that was refused -- is one JSON line appended to the priority log
   (`[priority] log` in storm.toml, beside the ledgers when undeclared), plus a plain-words
   line in `progress.log`. The lane order is the log's replay; nothing is edited in place.
   `storm-evidence.py` consumes the log by byte offset like the other ledgers (10.g).
6. REVERSIBLE. Un-bump undoes exactly what the push or bump moved: the lane itself, plus
   each dependency its own push or bump pulled forward that no other still-prioritised lane
   needs and that was not pushed or bumped in its own right. Un-bumping a lane another
   prioritised lane still depends on is refused, naming the dependents.
7. A NEW ITEM is appended to `queue.txt`, with its dependencies, and prioritised in one step.

ORDER OF A REQUEST
------------------
Shape first (every name against `Names`, the issue a number -- no lookups), then authority,
then the lookups (queue, ledgers, log), then the record. Every outcome is recorded, refusals
included. A refused input is written only through `json.dumps` into the log and escaped into
`progress.log`, so no request can add a line of its own to either -- the review of #1089
forged a `start` line into `progress.log` with a newline in a slug, which `storm-evidence`
then counted as a lane start.

WHY ONE RESOLVER
----------------
`storm-queue.sh` used to decide what was next in shell, over `queue.txt` alone. So the shell
asks this module (`python3 storm_queue.py next`) and the CLI lists from the same `Resolver`;
there is one answer. The shell's rules are kept: a settled lane is skipped, a finished one
awaits review and (unless `UNATTENDED`) holds the storm, and a lane met before the next one
whose dependency was abandoned is marked blocked. A `queue.txt` line whose slug, issue or
dependencies fall outside `Names` is never run: it is skipped and said in `progress.log`.

THE LOG FORMAT
--------------
One JSON object per line, `"v": 1`, every one carrying `action`, `slug`, `by` and `at`:

    push    + issue, deps, moved, appended
    bump    + issue, deps, moved
    unbump  + removed                      (the slugs it took out of the lane)
    refused + requested, reason, authorised (whether `by` was verified or only claimed)

Replay: `push`/`bump` append each of `moved` not already in the lane; `unbump` removes each
of `removed`; `refused` changes nothing. What `replay()` guarantees is SHAPE: a line that is
not JSON, names an unknown version or action, lacks a field, or carries a name outside
`Names` makes the whole log unreadable, and an unreadable order is reported and waited out,
never guessed at as "no priority" (10.f). What it does NOT guarantee is AUTHENTICITY: any
process running as the storm's owner can append a well-formed line, and replay cannot tell
it from one this module wrote. See `Authority` for why, and for the spec that fixes it.

A MISSING LOG IS NOT AN EMPTY ONE
---------------------------------
The first change writes the log's creation into its lock file, and the lock file is never
removed; the evidence watermark also records how far it has read the log. If either says the
log existed and the log is gone, the order is unknown (`Unreadable`), and `next` waits and
says so rather than running `queue.txt` in file order as though nothing had been pushed.

Classes, each declared in `interfaces/storm_queue_interface.py` (ADR-0016, 9.b). The one bare
function is `main`, the entry point a script run by path must have.

CLI, for `storm-queue.sh`:

    python3 storm_queue.py next    # run SLUG ISSUE | review SLUG.. | wait [SLUG..] | empty

Exit: 0 a decision on stdout; 2 usage; 3 the priority order is unknown (the log cannot be
replayed); 4 the resolver crashed (an OSError, a malformed storm.toml, anything else). The
shell waits out every non-zero exit and says which it was.
"""

from __future__ import annotations

import fcntl
import json
import os
import pwd
import re
import sys
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import storm_paths
from lane_environment import LaneEnvironment

VERSION = 1
VERBS = ("push", "bump", "unbump")
ACTIONS = frozenset({*VERBS, "refused"})


class Invalid(Exception):
    """The request cannot be carried out as asked. Recorded as a refusal; nothing changed."""


class Unreadable(Exception):
    """The priority log cannot be replayed, so the priority order is unknown."""


class Unauthorised(Exception):
    """The caller may not change the priority lane. Recorded as a refusal."""

    def __init__(self, principal: str, reason: str) -> None:
        super().__init__(reason)
        self.principal = principal


class Names:
    """What a slug, a dependency or a source name may be, and how outside text is written.

    A strict allow-list, `^[A-Za-z0-9][A-Za-z0-9._-]*$` with `..` refused anywhere: a slug
    becomes a directory under `lanes/`, a shell word in `storm-queue.sh` and a word in
    `progress.log`, so `../../escape`, `a*` and `x;y` are refused wherever they enter --
    the CLI, `queue.txt` and the log alike.
    """

    PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
    LONGEST = 200

    def valid(self, value: object) -> bool:
        return (
            isinstance(value, str)
            and len(value) <= self.LONGEST
            and self.PATTERN.fullmatch(value) is not None
            and ".." not in value
        )

    def check(self, value: str, what: str) -> None:
        if not self.valid(value):
            raise Invalid(
                f"a {what} must match [A-Za-z0-9][A-Za-z0-9._-]* with no '..', "
                f"not {self.quote(value)}"
            )

    def quote(self, value: object) -> str:
        """Outside text as one printable JSON string, cut short: never raw."""
        text = json.dumps(str(value), ensure_ascii=True)
        return text if len(text) <= self.LONGEST else text[: self.LONGEST] + '..."'

    def printable(self, text: str) -> str:
        """Every character that is not printable -- a newline, a carriage return, an escape
        sequence, U+2028 -- written as its escape, so one message is always one line."""
        return "".join(ch if ch.isprintable() else ascii(ch)[1:-1] for ch in text)


NAMES = Names()


@dataclass(frozen=True)
class QueueEntry:
    """One `queue.txt` line: `<slug> <issue> [dep1,dep2,...]`."""

    slug: str
    issue: str
    deps: tuple[str, ...] = ()

    def line(self) -> str:
        return " ".join([self.slug, self.issue, *([",".join(self.deps)] if self.deps else [])])


class QueueFile:
    """`queue.txt`, read the way `read -r slug issue deps` splits it -- and checked."""

    NAME = "queue.txt"

    def __init__(self, root: Path) -> None:
        self.path = root / self.NAME
        self.rejected: list[str] = []

    def entries(self) -> list[QueueEntry]:
        """Every well-formed entry in file order; a slug listed twice keeps its first line.
        A line whose slug, issue or dependencies fall outside `Names` is left out and said
        in `self.rejected` -- never run, never silently dropped."""
        self.rejected = []
        if not self.path.is_file():
            return []
        found: dict[str, QueueEntry] = {}
        for number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            fields = line.split(maxsplit=2)
            if not fields:
                continue
            issue = fields[1] if len(fields) > 1 else ""
            deps = tuple(fields[2].replace(",", " ").split()) if len(fields) > 2 else ()
            why = self._fault(fields[0], issue, deps)
            if why is not None:
                self.rejected.append(
                    f"queue.txt line {number} skipped, never run: {NAMES.quote(line)} ({why})"
                )
                continue
            found.setdefault(fields[0], QueueEntry(fields[0], issue, deps))
        return list(found.values())

    def append(self, entry: QueueEntry) -> None:
        """A whole line, even onto a file whose last line has no newline."""
        existing = self.path.read_bytes() if self.path.is_file() else b""
        separator = b"\n" if existing and not existing.endswith(b"\n") else b""
        with self.path.open("ab") as handle:
            handle.write(separator + (entry.line() + "\n").encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())

    @staticmethod
    def _fault(slug: str, issue: str, deps: tuple[str, ...]) -> str | None:
        if not NAMES.valid(slug):
            return "the slug is outside the allow-list"
        if not issue.isdigit():
            return "the issue is not a number"
        if not all(NAMES.valid(dep) for dep in deps):
            return "a dependency is outside the allow-list"
        return None


class Ledger:
    """The storm's settled and finished state, and the records the queue writes."""

    def __init__(self, root: Path, now: Callable[[], datetime] = lambda: datetime.now(UTC)):
        self.root = root
        self.now = now

    @staticmethod
    def stamp(now: datetime) -> str:
        """UTC to the second, the form `date -u +%FT%TZ` writes in progress.log."""
        return now.strftime("%Y-%m-%dT%H:%M:%SZ")

    def integrated(self) -> frozenset[str]:
        return self._lines("integrated.txt")

    def abandoned(self) -> frozenset[str]:
        return self._lines("abandoned.txt")

    def finished(self, slug: str) -> bool:
        """The lane has a verdict and awaits review (or a reviewer's settling)."""
        return (self.root / "lanes" / slug / ".qwenstorm" / "result.json").is_file()

    def unattended(self) -> bool:
        return (self.root / "UNATTENDED").is_file()

    def block(self, entry: QueueEntry, dep: str) -> None:
        """What `storm-queue.sh` wrote for a lane whose dependency was abandoned."""
        state = self.root / "lanes" / entry.slug / ".qwenstorm"
        state.mkdir(parents=True, exist_ok=True)
        (state / "result.json").write_text(json.dumps({"completed": False, "blocked_on": dep}))
        self.say(f"blocked {entry.slug} #{entry.issue}: dependency {dep} was abandoned")

    def say(self, message: str) -> None:
        """One stamped line in progress.log -- one, whatever `message` carries -- echoed on
        stderr (stdout is the decision the shell reads)."""
        line = f"{self.stamp(self.now())} {NAMES.printable(message)}"
        with (self.root / "progress.log").open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
        print(line, file=sys.stderr)

    def say_once(self, message: str) -> None:
        """`say`, unless the same words are already in the log's recent tail: a warning
        repeated on every pass of the runner would bury everything else in progress.log."""
        path = self.root / "progress.log"
        text = NAMES.printable(message)
        if path.is_file():
            with path.open("rb") as handle:
                handle.seek(max(0, path.stat().st_size - 262_144))
                if text in handle.read().decode("utf-8", "replace"):
                    return
        self.say(message)

    def _lines(self, name: str) -> frozenset[str]:
        # Whole lines, exactly: the shell asked `grep -qx`.
        path = self.root / name
        return frozenset(path.read_text().splitlines()) if path.is_file() else frozenset()


class PriorityLog:
    """The append-only priority log, and the lane order its replay gives.

    `watermark` and `key` name the evidence job's record of how far it read this log, a
    second witness that the log existed; both are optional.
    """

    def __init__(self, path: Path, watermark: Path | None = None, key: str | None = None):
        self.path = path
        self.lock = path.with_name(path.name + ".lock")
        self.watermark = watermark
        self.key = key

    def events(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            if self.existed():
                raise Unreadable(
                    f"{self.path} is missing, but it existed (its lock file or the evidence "
                    "watermark says so): the priority order is unknown until it is restored"
                )
            return []
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                # Shared lock: a line being appended is never read half-written.
                fcntl.flock(handle, fcntl.LOCK_SH)
                raw = handle.read()
        except (OSError, UnicodeDecodeError) as exc:
            raise Unreadable(f"{self.path}: {exc}") from exc
        events = []
        for number, line in enumerate(raw.splitlines(), 1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise Unreadable(f"{self.path} line {number} is not JSON: {exc}") from exc
            fault = self._fault(event)
            if fault is not None:
                raise Unreadable(f"{self.path} line {number} is malformed: {fault}")
            events.append(event)
        return events

    def replay(self) -> list[str]:
        lane: list[str] = []
        for event in self.events():
            if event["action"] in ("push", "bump"):
                for slug in event["moved"]:
                    if slug not in lane:
                        lane.append(slug)
            elif event["action"] == "unbump":
                for slug in event.get("removed", [event["slug"]]):
                    if slug in lane:
                        lane.remove(slug)
        return lane

    def append(self, event: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            # Exclusive for the write alone, against `events()`' shared lock.
            fcntl.flock(handle, fcntl.LOCK_EX)
            handle.write(json.dumps({"v": VERSION, **event}, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        if self.lock.is_file() and self.lock.stat().st_size == 0:
            # The witness: the lock file is never removed, and from now on it says the log
            # was written, so a log that disappears later reads as lost, not as empty.
            self.lock.write_text(f"{self.path.name} first written at {event.get('at')}\n")

    def existed(self) -> bool:
        """True when the lock file or the evidence watermark says the log was written."""
        if self.lock.is_file() and self.lock.stat().st_size > 0:
            return True
        if self.watermark is None or self.key is None or not self.watermark.is_file():
            return False
        try:
            offsets = json.loads(self.watermark.read_text()).get("offsets", {})
            return int(offsets.get(self.key, 0)) > 0
        except (OSError, ValueError, AttributeError, TypeError):
            # The evidence job reports its own unreadable watermark; the lock file still
            # stands as a witness here.
            return False

    @contextmanager
    def locked(self) -> Iterator[None]:
        """Exclusive: one request at a time, from reading the order to recording it.

        On a lock file beside the log, not the log itself: flock is per open file, so a
        request holding the log exclusively would deadlock on its own `replay()`."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.lock.open("a") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    @staticmethod
    def _fault(event: Any) -> str | None:
        """Why an entry is not one this version wrote, or None. Shape only (see module)."""
        if not isinstance(event, dict):
            return "not an object"
        if event.get("v") != VERSION:
            return f"version {event.get('v')!r}, not {VERSION}"
        action = event.get("action")
        if action not in ACTIONS:
            return f"unknown action {action!r}"
        for field in ("slug", "by", "at"):
            if not isinstance(event.get(field), str):
                return f"no {field}"
        if action == "refused":
            if event.get("requested") not in VERBS or not isinstance(event.get("reason"), str):
                return "a refusal without its request or reason"
            return None
        if not NAMES.valid(event["slug"]):
            return "a slug outside the allow-list"
        names = event.get("moved") if action in ("push", "bump") else event.get("removed", [])
        if not isinstance(names, list) or not all(NAMES.valid(n) for n in names):
            return "a list of lanes that is not a list of allowed names"
        return None


class Authority:
    """Who may change the priority lane.

    Every caller must run as the account that owns the storm's `queue.txt` -- the process
    uid against the file's owner, a tangible check (SD-01 §2), never $USER or $LOGNAME. On
    that account, a caller with no `--source` is the operator; automation names itself with
    `--source`, and only a name listed in storm.toml `[priority] sources` is accepted. A
    caller carrying `VIBEY_STORM_LANE` (exported by `LaneEnvironment` into every command a
    lane runs) is refused. Nothing takes a name from the forge, so a label or an issue opened
    by anyone else has no way in (12.j).

    WHAT THIS DOES NOT DO (12.i). Lanes run as the operator's uid today. A process running as
    that uid -- a lane's model among them -- can unset `VIBEY_STORM_LANE`, pass a declared
    `--source`, or append to the priority log and `queue.txt` directly. So the marker is
    defence in depth against an honest mistake, not containment of a hostile lane, and the
    source list names automation; it does not authenticate it. The fix is to run lanes as a
    separate low-privilege OS user who cannot write the storm's ledgers:
    `specs/storm-lane-os-user.md`.
    """

    def __init__(
        self,
        root: Path,
        sources: Sequence[str],
        uid: int | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> None:
        self.root = root
        self.sources = tuple(sources)
        self.uid = os.getuid() if uid is None else uid
        self.environ: Mapping[str, str] = os.environ if environ is None else environ
        self.user = self._account(self.uid)

    @classmethod
    def declared(cls, root: Path) -> Authority:
        return cls(root, storm_paths.declared_list(root, "priority", "sources") or ())

    def authorise(self, source: str | None) -> str:
        """The principal a change is recorded under, or `Unauthorised`."""
        marker = LaneEnvironment.MARKER
        if marker in self.environ:
            raise Unauthorised(
                f"lane:{NAMES.quote(self.environ[marker])}",
                f"a process inside a storm lane ({marker} is set) may not change the priority lane",
            )
        anchor = self.root / QueueFile.NAME
        owner = (anchor if anchor.exists() else self.root).stat().st_uid
        if self.uid != owner:
            raise Unauthorised(
                self.describe(source),
                f"the account {self.user} does not own the storm at {self.root}; only the "
                "owner's account may change the priority lane, with or without --source",
            )
        if source is None:
            return f"operator:{self.user}"
        if source not in self.sources:
            declared = ", ".join(self.sources) or "none"
            raise Unauthorised(
                self.describe(source),
                f"source {NAMES.quote(source)} is not declared in storm.toml [priority] sources "
                f"(declared: {declared})",
            )
        return f"source:{source}"

    def describe(self, source: str | None) -> str:
        """Who the caller claims to be, for recording a request that was not authorised."""
        if source is None:
            return f"account:{self.user}"
        return f"source:{source}" if NAMES.valid(source) else f"source:{NAMES.quote(source)}"

    @staticmethod
    def _account(uid: int) -> str:
        try:
            return pwd.getpwuid(uid).pw_name
        except KeyError:
            return f"uid-{uid}"


@dataclass(frozen=True)
class Row:
    """One lane in the effective order, and what the storm will do with it."""

    entry: QueueEntry
    prioritised: bool
    state: str  # next | ready | waiting | blocked | finished | settled
    status: str


@dataclass(frozen=True)
class Plan:
    """The effective order, the decision the shell acts on, and what `next` must report."""

    rows: tuple[Row, ...]
    decision: str
    blocked: tuple[tuple[QueueEntry, str], ...]
    stray: tuple[str, ...]  # prioritised slugs `queue.txt` does not carry
    warnings: tuple[str, ...]  # skipped `queue.txt` lines


class Resolver:
    """What runs next: the priority lane first, then `queue.txt`, by the shell's rules."""

    def __init__(self, queue: QueueFile, ledger: Ledger, log: PriorityLog) -> None:
        self.queue = queue
        self.ledger = ledger
        self.log = log

    @classmethod
    def at(cls, root: Path) -> Resolver:
        return cls(QueueFile(root), Ledger(root), PriorityLogs().at(root))

    def order(self) -> list[tuple[QueueEntry, bool]]:
        """Every queued entry, prioritised ones first in lane order, the rest in file order."""
        entries = self.queue.entries()
        known = {entry.slug: entry for entry in entries}
        lane = [slug for slug in self.log.replay() if slug in known]
        ahead = set(lane)
        return [(known[slug], True) for slug in lane] + [
            (entry, False) for entry in entries if entry.slug not in ahead
        ]

    def plan(self) -> Plan:
        """Pure: reads the storm, writes nothing."""
        integrated, abandoned = self.ledger.integrated(), self.ledger.abandoned()
        rows: list[Row] = []
        unreviewed: list[str] = []
        blocked: list[tuple[QueueEntry, str]] = []
        pending = 0
        chosen: QueueEntry | None = None
        for entry, prioritised in self.order():
            slug = entry.slug
            # The ledger decides, not the scratch directory: /tmp is wiped between sessions.
            if slug in integrated or slug in abandoned:
                which = "integrated" if slug in integrated else "abandoned"
                rows.append(Row(entry, prioritised, "settled", f"settled: {which}"))
                continue
            if self.ledger.finished(slug):
                unreviewed.append(slug)
                rows.append(Row(entry, prioritised, "finished", "finished, awaiting review"))
                continue
            pending += 1
            state, status, dead = self._judge(entry, integrated, abandoned)
            if chosen is None and state == "ready":
                chosen = entry
                state, status = "next", "next"
            elif chosen is None and dead is not None:
                blocked.append((entry, dead))
            rows.append(Row(entry, prioritised, state, status))
        warnings = tuple(self.queue.rejected)
        known = {entry.slug for entry in self.queue.entries()}
        stray = tuple(slug for slug in self.log.replay() if slug not in known)
        decision = self._decide(pending, unreviewed, chosen)
        return Plan(tuple(rows), decision, tuple(blocked), stray, warnings)

    def next(self) -> str:
        """The decision, after the shell's own side effect -- marking blocked the lanes the
        scan met before it -- and after saying, once, every line skipped and every
        prioritised lane `queue.txt` no longer carries."""
        plan = self.plan()
        for entry, dep in plan.blocked:
            self.ledger.block(entry, dep)
        for warning in plan.warnings:
            self.ledger.say_once(f"priority: {warning}")
        for slug in plan.stray:
            self.ledger.say_once(
                f"priority: {slug} is prioritised but not in queue.txt, so it cannot run; "
                "push it again with its issue number, or un-bump it"
            )
        return plan.decision

    def _decide(self, pending: int, unreviewed: list[str], chosen: QueueEntry | None) -> str:
        if pending == 0 and not unreviewed:
            return "empty"
        if unreviewed and not self.ledger.unattended():
            return "review " + " ".join(unreviewed)
        if chosen is None:
            return " ".join(["wait", *unreviewed])
        return f"run {chosen.slug} {chosen.issue}"

    @staticmethod
    def _judge(
        entry: QueueEntry, integrated: frozenset[str], abandoned: frozenset[str]
    ) -> tuple[str, str, str | None]:
        """(state, words, the abandoned dependency to mark it blocked on). Dependencies are
        checked in order and the first that is not integrated decides, as the shell did."""
        for dep in entry.deps:
            if dep in abandoned:
                return "blocked", f"blocked: dependency {dep} was abandoned", dep
            if dep not in integrated:
                waiting = [d for d in entry.deps if d not in integrated]
                return "waiting", "waiting on " + ", ".join(waiting), None
        return "ready", "ready", None


class PriorityLogs:
    """Finds a storm's priority log and its witnesses.

    The evidence watermark is consulted only for the storm these tools run in: the evidence
    job reads its own tree's watermark, so the same file says nothing about another root --
    a throwaway storm in a test, say.
    """

    def at(self, root: Path) -> PriorityLog:
        path = storm_paths.priority_log(root)
        if root.absolute() != storm_paths.storm(__file__):
            return PriorityLog(path)
        # Where storm-evidence.py keeps it: `.resolve()` follows `tools/` into the tracked
        # planning tree (see storm_paths for why the two directions differ).
        watermark = Path(__file__).resolve().parent.parent / "evidence" / "watermark.json"
        key = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
        return PriorityLog(path, watermark, key)


class PriorityDesk:
    """Push, bump and un-bump: shape, then authority, then lookups -- every outcome recorded."""

    def __init__(
        self,
        queue: QueueFile,
        ledger: Ledger,
        log: PriorityLog,
        authority: Authority,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.queue = queue
        self.ledger = ledger
        self.log = log
        self.authority = authority
        self.now = now

    @classmethod
    def at(cls, root: Path, authority: Authority | None = None) -> PriorityDesk:
        return cls(
            QueueFile(root),
            Ledger(root),
            PriorityLogs().at(root),
            authority or Authority.declared(root),
        )

    def push(self, slug: str, issue: str, deps: Sequence[str], source: str | None) -> list[str]:
        """Prioritise `slug`, appending it to `queue.txt` first when it is new."""

        def shape() -> None:
            if not issue.isdigit():
                raise Invalid(f"the issue must be a number, not {NAMES.quote(issue)}")
            for dep in deps:
                NAMES.check(dep, "dependency")

        return self._request(
            "push", slug, source, shape, lambda by: self._push(slug, issue, deps, by)
        )

    def bump(self, slug: str, source: str | None) -> list[str]:
        """Prioritise a lane `queue.txt` already carries."""
        return self._request("bump", slug, source, lambda: None, lambda by: self._bump(slug, by))

    def unbump(self, slug: str, source: str | None) -> list[str]:
        """Undo exactly what `slug`'s push or bump moved (module docstring, item 6)."""
        return self._request(
            "unbump", slug, source, lambda: None, lambda by: self._unbump(slug, by)
        )

    def _request(
        self,
        verb: str,
        slug: str,
        source: str | None,
        shape: Callable[[], None],
        act: Callable[[str], list[str]],
    ) -> list[str]:
        with self.log.locked():
            authorised = False
            by = self.authority.describe(source)
            try:
                NAMES.check(slug, "slug")
                if source is not None:
                    NAMES.check(source, "source")
                shape()
                by = self.authority.authorise(source)
                authorised = True
                return act(by)
            except Unauthorised as refused:
                self._refuse(verb, slug, refused.principal, False, str(refused))
                raise
            except Invalid as invalid:
                self._refuse(verb, slug, by, authorised, str(invalid))
                raise

    def _push(self, slug: str, issue: str, deps: Sequence[str], by: str) -> list[str]:
        lane = self.log.replay()
        known = {entry.slug: entry for entry in self.queue.entries()}
        entry = known.get(slug)
        if entry is not None:
            if entry.issue != issue:
                raise Invalid(f"{slug} is already queued for #{entry.issue}, not #{issue}")
            if deps and tuple(deps) != entry.deps:
                raise Invalid(
                    f"{slug} is already queued with dependencies "
                    f"{','.join(entry.deps) or 'none'}; bump it, or edit queue.txt"
                )
            appended = False
        else:
            entry = QueueEntry(slug, issue, tuple(deps))
            known[slug] = entry
            appended = True
        moved, already, notes = self._pull(entry, known, lane)
        if appended:
            self.queue.append(entry)
        return self._record("push", entry, by, moved, already, notes, lane, appended)

    def _bump(self, slug: str, by: str) -> list[str]:
        lane = self.log.replay()
        known = {entry.slug: entry for entry in self.queue.entries()}
        if slug not in known:
            raise Invalid(f"{slug} is not in queue.txt; push it with its issue number")
        moved, already, notes = self._pull(known[slug], known, lane)
        return self._record("bump", known[slug], by, moved, already, notes, lane, None)

    def _unbump(self, slug: str, by: str) -> list[str]:
        events = self.log.events()
        lane = self.log.replay()
        if slug not in lane:
            raise Invalid(f"{slug} is not prioritised; there is nothing to un-bump")
        known = {entry.slug: entry for entry in self.queue.entries()}
        integrated = self.ledger.integrated()
        others = [s for s in lane if s != slug]
        dependents = [s for s in others if slug in self._needs(s, known, integrated)]
        if dependents:
            raise Invalid(
                f"{slug} is needed by prioritised {', '.join(dependents)}; un-bump "
                f"{'them' if len(dependents) > 1 else 'it'} first"
            )
        # What this lane's own pushes and bumps moved, since it last entered the lane, and
        # which lanes were asked for in their own right.
        moved: list[str] = []
        targets: set[str] = set()
        for event in events:
            if event["action"] in ("push", "bump"):
                targets.add(event["slug"])
                if event["slug"] == slug:
                    moved.extend(s for s in event["moved"] if s not in moved)
            elif event["action"] == "unbump":
                removed = event.get("removed", [event["slug"]])
                targets.difference_update(removed)
                if slug in removed:
                    moved = []
        removed_set = {slug} | {s for s in moved if s in lane and s not in targets - {slug}}
        # A dependency stays while any lane left in the priority lane still needs it.
        while True:
            kept = [s for s in lane if s not in removed_set]
            needed = {d for s in kept for d in self._needs(s, known, integrated)} & removed_set
            needed.discard(slug)
            if not needed:
                break
            removed_set -= needed
        removed = [s for s in lane if s in removed_set]
        self.log.append(
            {"action": "unbump", "slug": slug, "removed": removed, "by": by, "at": self._now()}
        )
        self.ledger.say(
            f"priority: {by} un-bumped {slug}; returned to their queue.txt places: "
            f"{', '.join(removed)}"
        )
        report = [
            f"unbumped {slug} by {by}; returned to their queue.txt places: {', '.join(removed)}"
        ]
        left = [s for s in moved if s in lane and s not in removed_set]
        if left:
            report.append(
                f"still prioritised (pushed in their own right, or needed by another "
                f"prioritised lane): {', '.join(left)}"
            )
        return report

    def _refuse(self, verb: str, slug: str, by: str, authorised: bool, reason: str) -> None:
        """Every refusal is recorded: the request as JSON in the log, escaped in progress."""
        self.log.append(
            {
                "action": "refused",
                "requested": verb,
                "slug": slug[: Names.LONGEST * 4],
                "by": by,
                "authorised": authorised,
                "reason": reason,
                "at": self._now(),
            }
        )
        self.ledger.say(f"priority: refused a {verb} of {NAMES.quote(slug)} from {by}: {reason}")

    def _pull(
        self, entry: QueueEntry, known: dict[str, QueueEntry], lane: list[str]
    ) -> tuple[list[str], list[str], list[str]]:
        """(moved, already prioritised, notes): `entry` and every dependency it still needs,
        in dependency order. Raises `Invalid` for a lane that can never run."""
        integrated, abandoned = self.ledger.integrated(), self.ledger.abandoned()
        if entry.slug in integrated or entry.slug in abandoned:
            which = "integrated" if entry.slug in integrated else "abandoned"
            raise Invalid(f"{entry.slug} is already settled ({which}); there is nothing to run")
        if self.ledger.finished(entry.slug):
            raise Invalid(
                f"{entry.slug} has already run and awaits review; delete its result.json to "
                "run it again"
            )
        needed: list[str] = []
        notes: list[str] = []
        self._visit(entry.slug, known, integrated, abandoned, (entry.slug,), needed, notes)
        moved = [slug for slug in needed if slug not in lane]
        already = [slug for slug in needed if slug in lane]
        return moved, already, notes

    def _visit(
        self,
        slug: str,
        known: dict[str, QueueEntry],
        integrated: frozenset[str],
        abandoned: frozenset[str],
        path: tuple[str, ...],
        needed: list[str],
        notes: list[str],
    ) -> None:
        for dep in known[slug].deps:
            if dep in integrated:
                continue
            if dep in abandoned:
                raise Invalid(
                    f"{slug} depends on {dep}, which was abandoned, so it can never run; "
                    "settle that first"
                )
            if dep not in known:
                raise Invalid(f"{slug} depends on {dep}, which is neither queued nor integrated")
            if dep in path:
                raise Invalid(f"the dependencies form a cycle: {' -> '.join((*path, dep))}")
            if self.ledger.finished(dep):
                notes.append(f"{dep} has already run and awaits review; {slug} waits for it")
                continue
            self._visit(dep, known, integrated, abandoned, (*path, dep), needed, notes)
        if slug not in needed:
            needed.append(slug)

    def _needs(
        self, slug: str, known: dict[str, QueueEntry], integrated: frozenset[str]
    ) -> set[str]:
        """Every unintegrated dependency of `slug`, transitively, through `queue.txt`."""
        found: set[str] = set()
        todo = list(known[slug].deps) if slug in known else []
        while todo:
            dep = todo.pop()
            if dep in integrated or dep in found:
                continue
            found.add(dep)
            todo.extend(known[dep].deps if dep in known else ())
        return found

    def _record(
        self,
        verb: str,
        entry: QueueEntry,
        by: str,
        moved: list[str],
        already: list[str],
        notes: list[str],
        lane: list[str],
        appended: bool | None,
    ) -> list[str]:
        event: dict[str, Any] = {
            "action": verb,
            "slug": entry.slug,
            "issue": entry.issue,
            "deps": list(entry.deps),
            "moved": moved,
            "by": by,
            "at": self._now(),
        }
        if appended is not None:
            event["appended"] = appended
        self.log.append(event)
        done = "pushed" if verb == "push" else "bumped"
        self.ledger.say(
            f"priority: {by} {done} {entry.slug} (#{entry.issue}); moved to the front: "
            f"{', '.join(moved) or 'nothing new'}"
        )
        report = [f"{done} {entry.slug} (#{entry.issue}) by {by}"]
        if appended:
            report.append(f"appended to queue.txt: {entry.line()}")
        if moved:
            report.append(f"moved to the priority lane, in this order: {', '.join(moved)}")
        if already:
            report.append(f"already prioritised, place kept: {', '.join(already)}")
        report.extend(notes)
        settled = self.ledger.integrated() | self.ledger.abandoned()
        runs = [s for s in [*lane, *moved] if s not in settled and not self.ledger.finished(s)]
        upto = runs[: runs.index(entry.slug) + 1] if entry.slug in runs else runs
        report.append(
            "after the lane running now (never interrupted), the storm runs: " + ", ".join(upto)
        )
        return report

    def _now(self) -> str:
        return Ledger.stamp(self.now())


def main(argv: list[str]) -> int:
    """The `__main__` entry point: the one bare function (ADR-0016) -- a script run by path
    needs something to call, and everything it does is a class's."""
    if argv != ["next"]:
        print("usage: storm_queue.py next", file=sys.stderr)
        return 2
    try:
        print(Resolver.at(storm_paths.storm(__file__)).next())
    except Unreadable as exc:
        # On stdout, where the shell reads the decision, so it can say why it is waiting.
        print(f"the priority order is unknown: {exc}")
        return 3
    except (Exception, SystemExit) as exc:  # a crash is not a refusal: its own code
        print(f"the resolver crashed: {type(exc).__name__}: {exc}")
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
