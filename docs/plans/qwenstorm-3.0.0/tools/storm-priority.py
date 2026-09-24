"""Push a lane to the front of the storm, so it runs next after the lane running now.

    python3 storm-priority.py push SLUG ISSUE [--deps a,b]   # new or queued; prioritise it
    python3 storm-priority.py bump SLUG                      # a queued lane; prioritise it
    python3 storm-priority.py unbump SLUG                    # back to its queue.txt place
    python3 storm-priority.py list                           # the order the storm will run

Automation adds `--source NAME`, and only a NAME listed in `storm.toml` `[priority] sources`
is accepted. Without `--source`, the caller is the operator -- and must be the account that
owns the storm. Anything else is refused, recorded in the priority log and progress.log, and
reported here with exit 1 (sub-doctrine 12.j). The contract is ADR-0054; the rules, the log
format and the one resolver `storm-queue.sh` also asks are in `storm_queue.py`.

Every request is recorded, whatever its outcome. Exit:

    0  done (including a request that moved nothing)
    1  refused: the caller may not change the priority lane
    2  refused: the request cannot be carried out (a bad name, an unknown or abandoned
       dependency, a lane another prioritised lane still needs, ...)
    3  the priority order is unknown: the log cannot be replayed, or it is missing after it
       existed
    4  crashed: an OSError, a malformed storm.toml, anything unexpected -- not a refusal
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import storm_paths
from storm_queue import Invalid, PriorityDesk, Resolver, Unauthorised, Unreadable


class PriorityCli:
    """The operator's commands, each a thin call into `storm_queue`. Declared in
    `interfaces/storm_queue_interface.py` (ADR-0016)."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="storm-priority.py", description="the storm's priority lane (ADR-0054)"
        )
        verbs = parser.add_subparsers(dest="verb", required=True)
        push = verbs.add_parser("push", help="prioritise a lane, queueing it first if new")
        push.add_argument("slug")
        push.add_argument("issue")
        push.add_argument("--deps", default="", help="comma-separated dependency slugs")
        for name, text in (
            ("bump", "prioritise a queued lane"),
            ("unbump", "return a lane to its queue.txt position"),
        ):
            verbs.add_parser(name, help=text).add_argument("slug")
        for sub in verbs.choices.values():
            sub.add_argument("--source", help="the declared automation making this change")
        verbs.add_parser("list", help="the effective order the storm will run")
        return parser

    def run(self, argv: list[str]) -> int:
        args = self.parser().parse_args(argv)
        try:
            if args.verb == "list":
                return self.show()
            desk = PriorityDesk.at(self.root)
            if args.verb == "push":
                deps = tuple(d for d in args.deps.replace(",", " ").split())
                report = desk.push(args.slug, args.issue, deps, args.source)
            elif args.verb == "bump":
                report = desk.bump(args.slug, args.source)
            else:
                report = desk.unbump(args.slug, args.source)
        except Unauthorised as refused:
            print(f"refused, and recorded: {refused}", file=sys.stderr)
            return 1
        except Invalid as invalid:
            print(f"not done: {invalid}", file=sys.stderr)
            return 2
        except Unreadable as unreadable:
            print(f"the priority order is unknown: {unreadable}", file=sys.stderr)
            return 3
        except (Exception, SystemExit) as crash:  # storm_paths raises SystemExit on bad TOML
            print(f"crashed: {type(crash).__name__}: {crash}", file=sys.stderr)
            return 4
        print("\n".join(report))
        return 0

    def show(self) -> int:
        plan = Resolver.at(self.root).plan()
        verdict, *rest = plan.decision.split()
        if verdict == "run":
            print(f"next: {rest[0]} #{rest[1]}")
        else:
            why = {
                "empty": "the queue is empty",
                "review": "finished lanes await review: " + " ".join(rest),
                "wait": "no pending lane has all its dependencies integrated",
            }[verdict]
            print(f"next: nothing ({why})")
        for number, row in enumerate(plan.rows, 1):
            mark = " [priority]" if row.prioritised else ""
            print(f"{number}. {row.entry.slug} #{row.entry.issue}{mark}  {row.status}")
        if plan.stray:
            print("prioritised but not in queue.txt (ignored): " + ", ".join(plan.stray))
        for warning in plan.warnings:
            print(warning)
        return 0


def main() -> int:
    """The `__main__` entry point: the one bare function (ADR-0016)."""
    return PriorityCli(storm_paths.storm(__file__)).run(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
