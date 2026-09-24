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
   names everything that moved. Eligibility is unchanged: a lane starts only when every
   dependency is in `integrated.txt`, whatever its place in the lane.
4. AUTHORISATION. Only the operator -- the account that owns the storm, running the CLI
   locally -- or a source declared in `storm.toml` `[priority] sources` may push, bump or
   un-bump. Anything else is refused, and the refusal is recorded and reported (12.j).
   Nothing here reads the forge: no label, issue or comment reaches the lane. Priority never
   bypasses admission either -- `storm_trust.py admit` still judges a pushed issue's author
   and edit history at the moment its lane starts, and `lane-verify.py` still refuses
   forbidden paths at publish.
5. RECORDED, APPEND-ONLY, VISIBLE. Every push, bump, un-bump and refusal is one JSON line
   appended to the priority log -- `[priority] log` in storm.toml, beside the ledgers when
   undeclared -- plus a plain-words line in `progress.log`. Nothing is edited in place: the
   lane order is `PriorityLog.replay()` of that log, every time, and `storm-evidence.py`
   consumes the log by byte offset like the other ledgers (10.g).
6. REVERSIBLE. An un-bump takes an item out of the lane, and it runs at its `queue.txt`
   position again -- recorded the same way.
7. A NEW ITEM is appended to `queue.txt`, with its dependencies, and prioritised in one step.

WHY ONE RESOLVER
----------------
`storm-queue.sh` used to decide what was next in shell, over `queue.txt` alone. A second
decider in the priority CLI would agree with it until the day it did not, and the operator
would be told "runs next" about a lane the storm then skipped. So the shell asks this module
(`python3 storm_queue.py next`) and the CLI lists from the same `Resolver`; there is one
answer and one place to change it. The rules are the shell's own, kept exactly: a settled
lane is skipped, a finished one awaits review and (unless `UNATTENDED`) holds the storm, and
a lane met before the next one whose dependency was abandoned is marked blocked.

THE LOG FORMAT
--------------
One JSON object per line, `v` 1:

    {"action": "push",   "slug": S, "issue": N, "deps": [..], "moved": [..], "appended": B, "by": P, "at": T}
    {"action": "bump",   "slug": S, "issue": N, "deps": [..], "moved": [..], "by": P, "at": T}
    {"action": "unbump", "slug": S, "by": P, "at": T}
    {"action": "refused", "requested": VERB, "slug": S, "by": P, "reason": R, "at": T}

Replay: `push`/`bump` append each of `moved` not already in the lane, in order; `unbump`
removes its slug; `refused` changes nothing. A line that does not parse, or names an action
this version does not know, makes the whole log unreadable: the order is then unknown, and
an unknown order is reported, never guessed at as "no priority" (10.f).

Classes, each declared in `interfaces/storm_queue_interface.py` (ADR-0016, 9.b). The one bare
function is `main`, the entry point a script run by path must have.

CLI, for `storm-queue.sh`:

    python3 storm_queue.py next    # run SLUG ISSUE | review SLUG.. | wait [SLUG..] | empty
"""

from __future__ import annotations

import fcntl
import getpass
import json
import os
import sys
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import storm_paths

VERSION = 1
ACTIONS = frozenset({"push", "bump", "unbump", "refused"})


class Invalid(Exception):
    """The request cannot be carried out as asked; nothing was changed or recorded."""


class Unreadable(Exception):
    """The priority log cannot be replayed, so the priority order is unknown."""


class Unauthorised(Exception):
    """The caller may not change the priority lane. Always recorded before it is raised."""

    def __init__(self, principal: str, reason: str) -> None:
        super().__init__(reason)
        self.principal = principal


@dataclass(frozen=True)
class QueueEntry:
    """One `queue.txt` line: `<slug> <issue> [dep1,dep2,...]`."""

    slug: str
    issue: str
    deps: tuple[str, ...] = ()

    def line(self) -> str:
        return " ".join([self.slug, self.issue, *([",".join(self.deps)] if self.deps else [])])


class QueueFile:
    """`queue.txt`, read the way `read -r slug issue deps` splits it."""

    NAME = "queue.txt"

    def __init__(self, root: Path) -> None:
        self.path = root / self.NAME

    def entries(self) -> list[QueueEntry]:
        """Every entry in file order. A slug listed twice keeps its first line -- the one a
        top-to-bottom scan reaches first. Dependencies split on commas and whitespace, as
        the shell's `${deps//,/ }` did."""
        if not self.path.is_file():
            return []
        found: dict[str, QueueEntry] = {}
        for line in self.path.read_text(encoding="utf-8").splitlines():
            fields = line.split(maxsplit=2)
            if not fields or fields[0] in found:
                continue
            issue = fields[1] if len(fields) > 1 else ""
            deps = tuple(fields[2].replace(",", " ").split()) if len(fields) > 2 else ()
            found[fields[0]] = QueueEntry(fields[0], issue, deps)
        return list(found.values())

    def append(self, entry: QueueEntry) -> None:
        """A whole line, even onto a file whose last line has no newline -- `read` never
        returns a final line without one, so the shell silently dropped such a line."""
        existing = self.path.read_bytes() if self.path.is_file() else b""
        separator = b"\n" if existing and not existing.endswith(b"\n") else b""
        with self.path.open("ab") as handle:
            handle.write(separator + (entry.line() + "\n").encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())


class Ledger:
    """The storm's settled and finished state, and the two records the queue writes."""

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
        message = f"blocked {entry.slug} #{entry.issue}: dependency {dep} was abandoned"
        self.say(message)
        # stderr: stdout is the decision the shell reads.
        print(f"{self.stamp(self.now())} {message}", file=sys.stderr)

    def say(self, message: str) -> None:
        with (self.root / "progress.log").open("a", encoding="utf-8") as handle:
            handle.write(f"{self.stamp(self.now())} {message}\n")

    def _lines(self, name: str) -> frozenset[str]:
        # Whole lines, exactly: the shell asked `grep -qx`.
        path = self.root / name
        return frozenset(path.read_text().splitlines()) if path.is_file() else frozenset()


class PriorityLog:
    """The append-only priority log, and the lane order its replay gives."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def events(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                # Shared lock: a line being appended is never read half-written.
                fcntl.flock(handle, fcntl.LOCK_SH)
                raw = handle.read()
        except OSError as exc:
            raise Unreadable(f"{self.path}: {exc}") from exc
        events = []
        for number, line in enumerate(raw.splitlines(), 1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise Unreadable(f"{self.path} line {number} is not JSON: {exc}") from exc
            if not self._valid(event):
                raise Unreadable(f"{self.path} line {number} is not an event this reads: {line}")
            events.append(event)
        return events

    def replay(self) -> list[str]:
        lane: list[str] = []
        for event in self.events():
            if event["action"] in ("push", "bump"):
                for slug in event["moved"]:
                    if slug not in lane:
                        lane.append(slug)
            elif event["action"] == "unbump" and event["slug"] in lane:
                lane.remove(event["slug"])
        return lane

    def append(self, event: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            # Exclusive for the write alone, against `events()`' shared lock: a reader never
            # sees half a line. The change as a whole is serialised by `locked()`.
            fcntl.flock(handle, fcntl.LOCK_EX)
            handle.write(json.dumps({"v": VERSION, **event}, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    @contextmanager
    def locked(self) -> Iterator[None]:
        """Exclusive: one change at a time, from reading the order to recording the change.

        On a lock file beside the log, not the log itself: flock is per open file, so a
        change holding the log exclusively would deadlock on its own `replay()`."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.with_name(self.path.name + ".lock").open("a") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    @staticmethod
    def _valid(event: Any) -> bool:
        if not isinstance(event, dict) or event.get("action") not in ACTIONS:
            return False
        if not isinstance(event.get("slug"), str):
            return False
        if event["action"] in ("push", "bump"):
            moved = event.get("moved")
            return isinstance(moved, list) and all(isinstance(s, str) for s in moved)
        return True


class Authority:
    """Who may change the priority lane: the operator, or a source storm.toml declares.

    The operator is the account that owns the storm, running the CLI on this machine -- a
    tangible check (SD-01 §2), not a claim: the uid of the process against the owner of
    `queue.txt`. Automation names itself with `--source`, and only a name listed in
    `[priority] sources` is accepted. No name comes from the forge, so a label or an issue
    opened by anyone else has no way in (12.j).
    """

    def __init__(
        self,
        root: Path,
        sources: Sequence[str],
        uid: int | None = None,
        user: str | None = None,
    ) -> None:
        self.root = root
        self.sources = tuple(sources)
        self.uid = os.getuid() if uid is None else uid
        self.user = user or self._account(self.uid)

    @classmethod
    def declared(cls, root: Path) -> Authority:
        return cls(root, storm_paths.declared_list(root, "priority", "sources") or ())

    def authorise(self, source: str | None) -> str:
        """The principal a change is recorded under, or `Unauthorised`."""
        if source is None:
            anchor = self.root / QueueFile.NAME
            owner = (anchor if anchor.exists() else self.root).stat().st_uid
            if self.uid != owner:
                raise Unauthorised(
                    f"account:{self.user}",
                    f"the account {self.user} does not own the storm at {self.root}, so it is "
                    "not the operator; automation must name a source declared in "
                    "[priority] sources",
                )
            return f"operator:{self.user}"
        if source not in self.sources:
            declared = ", ".join(self.sources) or "none"
            raise Unauthorised(
                f"source:{source}",
                f"source {source!r} is not declared in storm.toml [priority] sources "
                f"(declared: {declared})",
            )
        return f"source:{source}"

    @staticmethod
    def _account(uid: int) -> str:
        try:
            return getpass.getuser()
        except (KeyError, OSError):
            return f"uid {uid}"


@dataclass(frozen=True)
class Row:
    """One lane in the effective order, and what the storm will do with it."""

    entry: QueueEntry
    prioritised: bool
    state: str  # next | ready | waiting | blocked | finished | settled
    status: str


@dataclass(frozen=True)
class Plan:
    """The effective order, the decision the shell acts on, and the lanes to mark blocked."""

    rows: tuple[Row, ...]
    decision: str
    blocked: tuple[tuple[QueueEntry, str], ...]
    stray: tuple[str, ...]  # prioritised slugs `queue.txt` does not carry


class Resolver:
    """What runs next: the priority lane first, then `queue.txt`, by the shell's rules."""

    def __init__(self, queue: QueueFile, ledger: Ledger, log: PriorityLog) -> None:
        self.queue = queue
        self.ledger = ledger
        self.log = log

    @classmethod
    def at(cls, root: Path) -> Resolver:
        return cls(QueueFile(root), Ledger(root), PriorityLog(storm_paths.priority_log(root)))

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
        known = {entry.slug for entry in self.queue.entries()}
        stray = tuple(slug for slug in self.log.replay() if slug not in known)
        return Plan(tuple(rows), self._decide(pending, unreviewed, chosen), tuple(blocked), stray)

    def next(self) -> str:
        """The decision, after marking blocked the lanes the scan met before it -- the
        shell's own side effect, kept so a blocked lane is reported, never skipped."""
        plan = self.plan()
        for entry, dep in plan.blocked:
            self.ledger.block(entry, dep)
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


class PriorityDesk:
    """Push, bump and un-bump: authorised, validated, recorded, then reported."""

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
            PriorityLog(storm_paths.priority_log(root)),
            authority or Authority.declared(root),
        )

    def push(self, slug: str, issue: str, deps: Sequence[str], source: str | None) -> list[str]:
        """Prioritise `slug`, appending it to `queue.txt` first when it is new."""
        with self.log.locked():
            by = self._authorise("push", slug, source)
            lane = self.log.replay()
            self._token(slug, "slug")
            if not issue.isdigit():
                raise Invalid(f"the issue must be a number, not {issue!r}")
            for dep in deps:
                self._token(dep, "dependency")
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

    def bump(self, slug: str, source: str | None) -> list[str]:
        """Prioritise a lane `queue.txt` already carries."""
        with self.log.locked():
            by = self._authorise("bump", slug, source)
            lane = self.log.replay()
            known = {entry.slug: entry for entry in self.queue.entries()}
            if slug not in known:
                raise Invalid(f"{slug} is not in queue.txt; push it with its issue number")
            moved, already, notes = self._pull(known[slug], known, lane)
            return self._record("bump", known[slug], by, moved, already, notes, lane, None)

    def unbump(self, slug: str, source: str | None) -> list[str]:
        """Take `slug` out of the priority lane; it runs at its `queue.txt` position again."""
        with self.log.locked():
            by = self._authorise("unbump", slug, source)
            lane = self.log.replay()
            if slug not in lane:
                raise Invalid(f"{slug} is not prioritised; there is nothing to un-bump")
            self.log.append({"action": "unbump", "slug": slug, "by": by, "at": self._now()})
            entries = self.queue.entries()
            place = next((i for i, e in enumerate(entries, 1) if e.slug == slug), None)
            where = f"position {place} of {len(entries)}" if place else "no position (not queued)"
            self.ledger.say(f"priority: {by} returned {slug} to its queue.txt place ({where})")
            report = [f"unbumped {slug} by {by}: it runs at its queue.txt {where} again"]
            known = {entry.slug: entry for entry in entries}
            empty = QueueEntry(slug, "")
            still = [d for d in known.get(slug, empty).deps if d in lane]
            if still:
                report.append(
                    f"its dependencies stay prioritised: {', '.join(still)} -- un-bump them "
                    "too if they should wait"
                )
            waiting = [s for s in lane if s != slug and slug in known.get(s, empty).deps]
            if waiting:
                report.append(f"prioritised {', '.join(waiting)} depend on it and will wait for it")
            return report

    def _authorise(self, verb: str, slug: str, source: str | None) -> str:
        """The principal, or a refusal recorded in both logs before it is raised (12.j)."""
        try:
            return self.authority.authorise(source)
        except Unauthorised as refused:
            self.log.append(
                {
                    "action": "refused",
                    "requested": verb,
                    "slug": slug,
                    "by": refused.principal,
                    "reason": str(refused),
                    "at": self._now(),
                }
            )
            self.ledger.say(f"priority: refused a {verb} of {slug} from {refused.principal}")
            raise

    def _pull(
        self, entry: QueueEntry, known: dict[str, QueueEntry], lane: list[str]
    ) -> tuple[list[str], list[str], list[str]]:
        """(moved, already prioritised, notes): `entry` and every dependency it still needs,
        in dependency order. Raises `Invalid` for a lane that cannot run however it is
        ordered."""
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

    @staticmethod
    def _token(value: str, what: str) -> None:
        if not value or any(c.isspace() or c == "," for c in value):
            raise Invalid(f"a {what} is one word with no commas, not {value!r}")


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
        print(f"the priority log could not be replayed, so the order is unknown: {exc}")
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
