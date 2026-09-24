"""What the storm runs next, decided in one place -- and the priority lane that can change it.

The operator's request (2026-09-24): "The system should be able to push a priority item into
the queue and have that run next so that it doesn't have to wait for the other jobs in front
of it." ADR-0054 is the contract, and vibey's PostgreSQL job queue keeps the same one:

1. NEXT MEANS NEXT AFTER WHATEVER IS RUNNING. Nothing running is interrupted. Lanes run one
   at a time (8.c) unless this device's calibration evidence supports more
   (`[local_models] concurrent_runs`, ADR-0058), and `storm-queue.sh` asks what is next only
   once fewer lanes run than that. A running lane is never chosen again; nothing here stops,
   signals or rewrites a running lane.
2. PRIORITY ITEMS RUN FIRST, FIFO, ahead of every un-bumped `queue.txt` line. Re-bumping an
   item keeps its place.
3. DEPENDENCIES PULLED FORWARD, transitively and dependencies first, keeping their relative
   order. A dependency that can never finish refuses the push or bump and is named: in the
   storm that is one in `abandoned.txt` (where a failed or cancelled lane is settled), one
   nothing queues, or one in a cycle. Eligibility is unchanged: a lane starts only when every
   dependency is in `integrated.txt`.
4. AUTHORISATION. The operator is the account that owns the storm's `queue.txt`, checked by
   uid against the file owner, never a typed name or $USER. A `--source` must be declared in
   storm.toml `[priority] sources` AND run as the operator's account; no declaration means no
   source is accepted. Nothing reads the forge. Priority never bypasses another gate:
   `storm_trust.py admit` still judges a pushed issue when its lane starts, and
   `lane-verify.py` still refuses forbidden paths at publish. See `Authority` for what this
   check cannot do while lanes run as the operator's uid.
5. EVERY REQUEST IS RECORDED: moved something, moved nothing, or refused -- one JSON line in
   the priority log (`[priority] log` in storm.toml, beside the ledgers when undeclared), plus
   a plain-words line in `progress.log`. Authorisation runs before any lookup. The lane order
   is the log's replay; nothing is edited in place. `storm-evidence.py` consumes the log by
   byte offset like the other ledgers (10.g).
6. UN-BUMP UNDOES EXACTLY WHAT THE BUMP MOVED, by derivation. The priority lane is exactly:
   the items pushed or bumped BY NAME and not since un-bumped, plus all their unfinished
   transitive dependencies, ordered first-in first by when each entered the lane. Un-bumping
   X removes X from the named set, and is refused, naming them, while another named item
   depends on X. Every lane no remaining named item requires leaves with X -- so no orphan
   can remain -- and the `unbump` line records that resulting `removed` list, so replay is
   exact. An item bumped by name keeps its place.
7. AN ITEM CAN BE ENQUEUED ALREADY PRIORITISED IN ONE STEP: `push` appends a new slug to
   `queue.txt` with its dependencies and prioritises it. Doing so for a finished item -- one
   settled in either ledger, or one that has run and awaits review -- is a recorded no-op.

Where the storm's mechanism differs from vibey's job queue, as ADR-0054 records: the
declaration lives in storm.toml `[priority] sources` and the operator is the owner of
`queue.txt`; the record is this priority log and its replay, not a ledger written in the same
transaction; and a refusal exits 1 here, not 3.

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

A MISSING OR SHORTENED LOG IS NOT AN EMPTY ONE
----------------------------------------------
After every append a witness beside the log (`.<log name>.witness`, which a `priority.log*`
glob does not match) records the log's length; the evidence watermark records how far it
has read. If either says the log existed and it is gone, or the log is shorter than recorded,
the order is unknown (`Unreadable`): `next` exits 3 and the runner waits and says so, rather
than running `queue.txt` in file order as though nothing had been pushed. No request -- not
even a refusal that must be recorded -- re-creates a lost log, appends to a shortened one, or
rewrites an unreadable witness: it says so in progress.log and exits 3. Both witnesses are files the storm's own uid can rewrite (see `Authority`).

A CALLER WHO CANNOT WRITE
-------------------------
Authority is checked before the lock is taken, so another uid is refused (exit 1) rather than
crashing on a lock file it cannot open. If the refusal itself cannot be written -- no write
access to the log or progress.log -- it is still a refusal, reported on stderr as "could not
be recorded (no write access)"; ADR-0054 records the same case for vibey's queue.

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
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import storm_paths
from lane_environment import LaneEnvironment

VERSION = 1
# ASCII digits only: `str.isdigit()` also accepts "\u0663" and "\u00b2", which no forge numbers
# an issue with and `storm_trust.py admit` would then refuse far from where it entered.
ISSUE = re.compile(r"[0-9]+")
VERBS = ("push", "bump", "unbump", "reset")
ACTIONS = frozenset({*VERBS, "refused"})
# Said in every "order unknown" message, so the message itself names the way out.
RECOVER = (
    "restore the log, or -- as the operator, on the storm owner's account -- start a new one "
    "with `storm-priority.py reset --reason TEXT`, which records that the prior order was "
    "abandoned"
)


class Refusal(Exception):
    """A request refused. `recorded` is False only when the refusal could not be written --
    a caller without write access to the storm -- which is still a refusal (exit 1 or 2),
    reported as unrecorded, never a crash. `unrecorded` says why it could not be written: no
    write access, or -- for a refused reset -- a log that is lost or unreadable."""

    recorded = True
    unrecorded = "no write access"


class Invalid(Refusal):
    """The request cannot be carried out as asked. Recorded as a refusal; nothing changed."""


class Unreadable(Exception):
    """The priority log cannot be replayed, so the priority order is unknown."""

    reported = False  # set once progress.log has been told, so it is told once


class Unauthorised(Refusal):
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
        if ISSUE.fullmatch(issue) is None:
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

    def running(self, slug: str) -> bool:
        """The lane has started and not ended: `storm-queue.sh` marks it before the lane
        starts and clears the mark when it ends, so a second lane running beside it (when
        `[local_models] concurrent_runs` allows more than one) is never the same lane."""
        return (self.root / "lanes" / slug / ".qwenstorm" / "running").is_file()

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

    THE WITNESS. After every append, `.<log name>.witness` beside the log records that the
    log exists and how long it is. It is a dotfile so a `priority.log*` glob -- the obvious
    way to clear the log away -- does not take the witness with it. It is written to a
    `.new` file, fsynced, renamed over the old one, and the directory is fsynced, so a power
    loss leaves the old witness or the new one, never an empty one. With it:

    * a log that is missing while the witness says it existed is an unknown order, and so is
      one SHORTER than recorded (truncated), and so is an unreadable or empty witness: each
      is `Unreadable`, and each message names the way out (`RECOVER`);
    * `append` never creates the log when the witness says it existed, so a refused request
      meeting a lost log cannot quietly start a fresh, empty one; and, under the exclusive
      lock, it never appends to a log shorter than recorded or beside an unreadable witness,
      so a refusal cannot re-witness a truncated log as whole. It writes nothing then.

    The witness is read inside the same shared lock as the log, against the log's size under
    that lock, so a read racing an append never sees a false truncation. A log LONGER than
    recorded is accepted: a crash between the append and the witness update, safe to re-read.
    `watermark` and `key` name the evidence job's record of how far it read this log, a
    second witness; both are optional.

    THE WAY OUT. A lost or unreadable log is recovered by `restart`, behind
    `PriorityDesk.reset`: the old file, if any, is kept under a new name, never deleted, and
    the new log's first line is a `reset` event naming the length it abandons. A watermark
    offset no greater than that is then about the abandoned log, not this one, and is set
    aside; `storm-evidence.py` re-bases on the same line and reports the gap (10.g).

    None of this stops the same uid rewriting the log AND the witness together (see
    `Authority`).
    """

    def __init__(self, path: Path, watermark: Path | None = None, key: str | None = None):
        self.path = path
        self.lock = path.with_name(path.name + ".lock")
        self.witness = path.with_name("." + path.name + ".witness")
        self.watermark = watermark
        self.key = key

    def events(self) -> list[dict[str, Any]]:
        # The log is created before its witness and never removed by this module, so "no
        # log" followed by "a witness" may be a writer creating both in between: look again
        # before calling the log lost.
        if not self.path.is_file():
            if self.existed() and not self.path.is_file():
                raise Unreadable(
                    f"{self.path} is missing, but it existed (its witness or the evidence "
                    f"watermark says so): the priority order is unknown; {RECOVER}"
                )
            return []
        try:
            with self.path.open("rb") as handle:
                # Shared lock: an append (exclusive) is never read half-written, and the
                # witness it writes is read under the same lock, against the size now.
                fcntl.flock(handle, fcntl.LOCK_SH)
                data = handle.read()
                size = os.fstat(handle.fileno()).st_size
                recorded = self.recorded_length()
            raw = data.decode("utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise Unreadable(f"{self.path}: {exc}; {RECOVER}") from exc
        if size < recorded:
            raise Unreadable(
                f"{self.path} is truncated: {size} bytes, but {recorded} were recorded; the "
                f"priority order is unknown; {RECOVER}"
            )
        events: list[dict[str, Any]] = []
        for number, line in enumerate(raw.splitlines(), 1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise Unreadable(
                    f"{self.path} line {number} is not JSON: {exc}; {RECOVER}"
                ) from exc
            fault = self._fault(event)
            if fault is None and event["action"] == "reset" and events:
                fault = "a reset anywhere but the first line"
            if fault is not None:
                raise Unreadable(f"{self.path} line {number} is malformed: {fault}; {RECOVER}")
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

    def named(self) -> list[str]:
        """The items pushed or bumped BY NAME and not since un-bumped, first named first. A
        recorded no-op names nothing: it asked for an item with nothing left to run."""
        named: list[str] = []
        for event in self.events():
            if event["action"] in ("push", "bump") and "noop" not in event:
                if event["slug"] not in named:
                    named.append(event["slug"])
            elif event["action"] == "unbump" and event["slug"] in named:
                named.remove(event["slug"])
        return named

    def append(self, event: dict[str, Any]) -> None:
        """Append one line and record the new length. Never creates a log that existed, and
        never appends to one shorter than recorded or whose witness cannot be read: either
        would re-witness the damaged log as whole. In those cases nothing is written."""
        if not self.path.is_file() and self.existed() and not self.path.is_file():
            raise Unreadable(
                f"{self.path} is missing, but it existed: nothing is appended to a fresh one, "
                f"so the order stays unknown; {RECOVER}"
            )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            # Exclusive for the check, the write and the witness, against `events()`' shared
            # lock. `recorded_length` raises `Unreadable` for an empty or corrupt witness.
            fcntl.flock(handle, fcntl.LOCK_EX)
            size = os.fstat(handle.fileno()).st_size
            recorded = self.recorded_length()
            if size < recorded:
                raise Unreadable(
                    f"{self.path} is truncated: {size} bytes, but {recorded} were recorded; "
                    f"nothing is appended to it, so the order stays unknown; {RECOVER}"
                )
            handle.write(json.dumps({"v": VERSION, **event}, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
            self._witness(os.fstat(handle.fileno()).st_size, event.get("at"))

    def restart(self, event: dict[str, Any]) -> Path | None:
        """Start a new log whose first line is `event` (a `reset`), keeping the old file, if
        any, under a new name -- never deleting it. Returns where the old file went."""
        aside: Path | None = None
        if self.path.exists():
            stamp = str(event.get("at", "")).replace(":", "")
            aside = self.path.with_name(f"{self.path.name}.abandoned-{stamp}")
            number = 1
            while aside.exists():
                number += 1
                aside = self.path.with_name(f"{self.path.name}.abandoned-{stamp}-{number}")
            self.path.rename(aside)
            self._sync_directory()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("x", encoding="utf-8") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            handle.write(json.dumps({"v": VERSION, **event}, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
            self._witness(os.fstat(handle.fileno()).st_size, event.get("at"))
        return aside

    def recorded_length(self) -> int:
        """The longest length recorded for the log -- by its witness, or by the evidence
        watermark unless the log now begins with a `reset` that abandoned at least that
        much. 0 when nothing has recorded anything."""
        lengths = [0]
        try:
            text = self.witness.read_text()
        except FileNotFoundError:
            text = None
        except OSError as exc:
            raise Unreadable(f"{self.witness} could not be read: {exc}; {RECOVER}") from exc
        if text is not None:
            try:
                lengths.append(int(json.loads(text)["length"]))
            except (ValueError, KeyError, TypeError) as exc:
                raise Unreadable(
                    f"{self.witness} is empty or unreadable ({exc}), so the log's length is "
                    f"unknown; {RECOVER}"
                ) from exc
        offset = self._watermark_offset()
        if offset:
            head = self._head()
            if head is None or head.get("action") != "reset" or head.get("abandons", -1) < offset:
                lengths.append(offset)
        return max(lengths)

    def abandonable(self) -> int:
        """What a reset abandons, read without trusting anything: the largest of the log's
        current size, the witness's record and the watermark's offset that can be read."""
        lengths = [self.path.stat().st_size if self.path.is_file() else 0]
        # An unreadable witness is exactly what a reset recovers from: read what can be.
        with suppress(OSError, ValueError, KeyError, TypeError):
            lengths.append(int(json.loads(self.witness.read_text())["length"]))
        lengths.append(self._watermark_offset())
        return max(lengths)

    def existed(self) -> bool:
        """True when the witness or the evidence watermark says the log was written."""
        return self.witness.is_file() or self.recorded_length() > 0

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

    def _witness(self, length: int, at: object) -> None:
        pending = self.witness.with_name(self.witness.name + ".new")
        with pending.open("w", encoding="utf-8") as handle:
            handle.write(json.dumps({"log": self.path.name, "length": length, "at": at}))
            handle.flush()
            os.fsync(handle.fileno())
        pending.replace(self.witness)
        self._sync_directory()

    def _sync_directory(self) -> None:
        """A rename is durable only once its directory is: fsync the directory too."""
        descriptor = os.open(self.path.parent, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def _watermark_offset(self) -> int:
        if self.watermark is None or self.key is None or not self.watermark.is_file():
            return 0
        try:
            return int(json.loads(self.watermark.read_text()).get("offsets", {}).get(self.key, 0))
        except (OSError, ValueError, AttributeError, TypeError):
            # The evidence job reports its own unreadable watermark (10.g).
            return 0

    def _head(self) -> dict[str, Any] | None:
        """The log's first event, if the first line parses as one; None otherwise."""
        try:
            with self.path.open("rb") as handle:
                first = json.loads(handle.readline())
        except (OSError, ValueError):
            return None
        return first if isinstance(first, dict) else None

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
        for field in ("by", "at"):
            if not isinstance(event.get(field), str):
                return f"no {field}"
        if action == "reset":
            abandons = event.get("abandons")
            if not isinstance(abandons, int) or isinstance(abandons, bool) or abandons < 0:
                return "a reset without the length it abandons"
            if not isinstance(event.get("reason"), str) or not event["reason"].strip():
                return "a reset without its reason"
            return None
        if not isinstance(event.get("slug"), str):
            return "no slug"
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
    state: str  # next | ready | waiting | blocked | running | finished | settled
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
            # The ledger decides, not lanes/: that is working material a machine can lose (10.h).
            if slug in integrated or slug in abandoned:
                which = "integrated" if slug in integrated else "abandoned"
                rows.append(Row(entry, prioritised, "settled", f"settled: {which}"))
                continue
            if self.ledger.finished(slug):
                unreviewed.append(slug)
                rows.append(Row(entry, prioritised, "finished", "finished, awaiting review"))
                continue
            if self.ledger.running(slug):
                # Still pending -- it has not finished -- so the storm is never "empty" while
                # a lane runs beside the runner; but never chosen again while it runs.
                pending += 1
                rows.append(Row(entry, prioritised, "running", "running now"))
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
            if ISSUE.fullmatch(issue) is None:
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

    def reset(self, reason: str, source: str | None) -> list[str]:
        """Start a new priority log after the old one was lost or became unreadable.

        The operator's alone -- the storm owner's uid, no lane marker, never a `--source` --
        and refused while the log is still readable: a reset never replaces a readable order.
        The new log's first line records the length it abandons and the reason, the old file
        is kept under a new name, and progress.log says in plain words that the prior
        priority order was abandoned."""
        by = self.authority.describe(source)
        try:
            if not reason.strip():
                raise Invalid("a reset needs a --reason saying why the old order was abandoned")
            if source is not None:
                raise Unauthorised(
                    by, "a reset is the operator's alone, never a --source's: run it yourself"
                )
            by = self.authority.authorise(None)
        except Refusal as refused:
            if isinstance(refused, Unauthorised):
                by = refused.principal
            self._refuse("reset", "", by, False, refused, lost_ok=True)
            raise
        with self.log.locked():
            try:
                self.log.events()
            except Unreadable as unknown:
                return self._restart(reason, by, unknown)
            readable = Invalid(
                "the priority log is readable, so there is nothing to recover: a reset never "
                "replaces a readable order (un-bump what should not run first)"
            )
            self._refuse("reset", "", by, True, readable)
            raise readable

    def _restart(self, reason: str, by: str, unknown: Unreadable) -> list[str]:
        abandons = self.log.abandonable()
        aside = self.log.restart(
            {
                "action": "reset",
                "reason": reason.strip(),
                "abandons": abandons,
                "by": by,
                "at": self._now(),
            }
        )
        where = (
            f"the old file is kept as {aside.name}" if aside else "the old file was already gone"
        )
        self._say(
            f"priority: {by} reset the priority log ({NAMES.quote(reason.strip())}): the prior "
            f"priority order was abandoned ({abandons} recorded byte(s); {where}); every lane "
            "runs in queue.txt order until it is pushed or bumped again"
        )
        return [
            f"reset the priority log by {by}: the prior priority order was abandoned "
            f"({abandons} recorded byte(s))",
            where,
            f"it was: {unknown}",
            "push or bump again whatever should run first",
        ]

    def _request(
        self,
        verb: str,
        slug: str,
        source: str | None,
        shape: Callable[[], None],
        act: Callable[[str], list[str]],
    ) -> list[str]:
        """Shape, then authority -- both before the lock, so a caller who may not write the
        storm is refused rather than crashing on a lock it cannot open -- then, under the
        lock, the lookups and the record. Every outcome is recorded where it can be."""
        authorised = False
        by = self.authority.describe(source)
        try:
            try:
                NAMES.check(slug, "slug")
                if source is not None:
                    NAMES.check(source, "source")
                shape()
                by = self.authority.authorise(source)
                authorised = True
            except Refusal as refused:
                if isinstance(refused, Unauthorised):
                    by = refused.principal
                self._refuse(verb, slug, by, authorised, refused)
                raise
            with self.log.locked():
                try:
                    return act(by)
                except Invalid as invalid:
                    self._refuse(verb, slug, by, True, invalid)
                    raise
        except Unreadable as unknown:
            if not unknown.reported:
                self._say(
                    f"priority: a {verb} of {NAMES.quote(slug)} from {by} was not carried out, "
                    f"order unknown: {unknown}"
                )
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
        finished = self._finished(slug)
        if finished is not None:
            # ADR-0054 item 7: prioritising a finished item is a recorded no-op, and a
            # settled slug is never queued again.
            return self._record("push", entry, by, [], [], [], lane, False, finished)
        moved, already, notes = self._pull(entry, known, lane)
        if appended:
            self.queue.append(entry)
        return self._record("push", entry, by, moved, already, notes, lane, appended)

    def _bump(self, slug: str, by: str) -> list[str]:
        lane = self.log.replay()
        known = {entry.slug: entry for entry in self.queue.entries()}
        entry = known.get(slug, QueueEntry(slug, ""))
        # Finished first: a settled lane `queue.txt` no longer carries is still a no-op.
        finished = self._finished(slug)
        if finished is not None:
            return self._record("bump", entry, by, [], [], [], lane, None, finished)
        if slug not in known:
            raise Invalid(f"{slug} is not in queue.txt; push it with its issue number")
        moved, already, notes = self._pull(entry, known, lane)
        return self._record("bump", entry, by, moved, already, notes, lane, None)

    def _unbump(self, slug: str, by: str) -> list[str]:
        """The derived rule, shared with vibey's job queue (ADR-0054 item 6): the priority
        lane is exactly the items pushed or bumped BY NAME and not since un-bumped, plus all
        their unfinished transitive dependencies. Un-bumping removes `slug` from the named
        set -- refused, naming them, while another named item depends on it -- and every
        lane no remaining named item requires leaves with it, so no orphan remains. The
        resulting `removed` list is recorded, so replay stays exact."""
        lane = self.log.replay()
        named = self.log.named()
        if slug not in lane and slug not in named:
            raise Invalid(f"{slug} is not prioritised; there is nothing to un-bump")
        known = {entry.slug: entry for entry in self.queue.entries()}
        integrated = self.ledger.integrated()
        remaining = [n for n in named if n != slug and self._finished(n) is None]
        dependents = [n for n in remaining if slug in self._needs(n, known, integrated)]
        if dependents:
            raise Invalid(
                f"{slug} is needed by {', '.join(dependents)}, bumped by name; un-bump "
                f"{'them' if len(dependents) > 1 else 'it'} first"
            )
        required = set(remaining)
        for item in remaining:
            required |= self._needs(item, known, integrated)
        removed = [s for s in lane if s not in required]
        self.log.append(
            {"action": "unbump", "slug": slug, "removed": removed, "by": by, "at": self._now()}
        )
        self.ledger.say(
            f"priority: {by} un-bumped {slug}; returned to their queue.txt places: "
            f"{', '.join(removed) or 'nothing'}"
        )
        report = [
            f"unbumped {slug} by {by}; returned to their queue.txt places: "
            f"{', '.join(removed) or 'nothing'}"
        ]
        kept = [s for s in lane if s in required]
        if kept:
            report.append(
                f"still prioritised (bumped by name, or needed by an item that is): "
                f"{', '.join(kept)}"
            )
        return report

    def _refuse(
        self,
        verb: str,
        slug: str,
        by: str,
        authorised: bool,
        refused: Refusal,
        lost_ok: bool = False,
    ) -> None:
        """Record a refusal: the request as JSON in the log, escaped in progress.log.

        Two things can stop the record. A log that is lost (see `PriorityLog`) is never
        re-created: the refusal is said in progress.log and `Unreadable` raised (exit 3). A
        caller without write access -- another uid, a read-only storm -- cannot record
        anything: the refusal stands, marked `recorded = False` (exit 1 or 2, "could not be
        recorded"), rather than surfacing as a crash."""
        reason = str(refused)
        try:
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
        except Unreadable as unknown:
            self._say(
                f"priority: refused a {verb} of {NAMES.quote(slug)} from {by}: {reason}; not "
                f"recorded, order unknown: {unknown}"
            )
            if lost_ok:
                # A refused reset meets a lost log by its nature: still a refusal (1 or 2).
                refused.recorded = False
                refused.unrecorded = "the priority log is lost or unreadable, order unknown"
                return
            unknown.reported = True
            raise unknown from refused
        except OSError:
            refused.recorded = False
            self._say(f"priority: refused a {verb} of {NAMES.quote(slug)} from {by}: {reason}")
            return
        self._say(f"priority: refused a {verb} of {NAMES.quote(slug)} from {by}: {reason}")

    def _say(self, message: str) -> None:
        """`Ledger.say`, where progress.log can be written; a caller that cannot write it is
        still answered on stderr by the CLI."""
        try:
            self.ledger.say(message)
        except OSError:
            print(NAMES.printable(message), file=sys.stderr)

    def _pull(
        self, entry: QueueEntry, known: dict[str, QueueEntry], lane: list[str]
    ) -> tuple[list[str], list[str], list[str]]:
        """(moved, already prioritised, notes): `entry` and every dependency it still needs,
        in dependency order. Raises `Invalid` for a lane that can never run."""
        integrated, abandoned = self.ledger.integrated(), self.ledger.abandoned()
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

    def _finished(self, slug: str) -> str | None:
        """Why `slug` has nothing left to run (settled, or run and awaiting review), or None."""
        if slug in self.ledger.integrated():
            return "it is already settled (integrated)"
        if slug in self.ledger.abandoned():
            return "it is already settled (abandoned)"
        if self.ledger.finished(slug):
            return "it has already run and awaits review; delete its result.json to run it again"
        return None

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
        noop: str | None = None,
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
        done = "pushed" if verb == "push" else "bumped"
        label = f" (#{entry.issue})" if entry.issue else ""
        if noop is not None:
            event["noop"] = noop
            self.log.append(event)
            self.ledger.say(f"priority: {by} {done} {entry.slug}{label}; nothing to do: {noop}")
            return [f"{done} {entry.slug}{label} by {by}: nothing to do, {noop}"]
        self.log.append(event)
        self.ledger.say(
            f"priority: {by} {done} {entry.slug}{label}; moved to the front: "
            f"{', '.join(moved) or 'nothing new'}"
        )
        report = [f"{done} {entry.slug}{label} by {by}"]
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
