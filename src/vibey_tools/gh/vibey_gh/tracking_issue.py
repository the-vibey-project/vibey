# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One tracking issue per condition, opened, kept current and closed by automation.

A condition that nobody is told about is a condition nobody fixes: develop stayed red for
a day while four pull requests merged over it, and an optional publishing channel with no
credential failed a whole release run instead of saying so somewhere it would be read.
Both want the same thing -- exactly one open issue while the condition holds, closed with
a note when it clears -- and that is what this provides, keyed by a marker in the body.

`vibey-gh tracking-issue raise|resolve` exposes it to workflows that decide the condition
themselves; `vibey_gh.branch_health` uses it directly.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence
from typing import Any

from vibey_gh import github_state
from vibey_gh.gh_transport import GhTransport
from vibey_gh.interfaces.gh_transport_interface import GhTransportInterface
from vibey_gh.interfaces.tracking_issue_interface import TrackingIssueInterface

__all__ = ["TrackingIssue"]

_MARKER = "vibey-gh:tracking"
_EVENT_MARKER = "vibey-gh:tracking-event"


class TrackingIssue(TrackingIssueInterface):
    """Implements `TrackingIssueInterface` over the forge's REST API."""

    def __init__(
        self,
        *,
        transport: GhTransportInterface | None = None,
        repository: Callable[[], str] = github_state.repository,
    ) -> None:
        self._transport: GhTransportInterface = transport or GhTransport()
        self._repository = repository

    @staticmethod
    def marker(key: str) -> str:
        """The hidden line that names an issue's condition."""
        return f"<!-- {_MARKER}:{key} -->"

    def find(self, key: str) -> int | None:
        marker = self.marker(key)
        found = [
            int(issue["number"])
            for issue in self._list(f"repos/{self._repository()}/issues?state=open&per_page=100")
            if "pull_request" not in issue and marker in str(issue.get("body") or "")
        ]
        # The oldest, if a race ever opened two: it is the one people have already seen.
        return min(found) if found else None

    def raise_issue(
        self,
        key: str,
        title: str,
        body: str,
        *,
        event: str = "",
        event_key: str = "",
        labels: Sequence[str] = (),
    ) -> tuple[int, bool]:
        repository = self._repository()
        full_body = f"{self.marker(key)}\n{body.strip()}\n"
        number = self.find(key)
        created = number is None
        if number is None:
            payload: dict[str, Any] = {"title": title, "body": full_body}
            if labels:
                payload["labels"] = list(labels)
            number = int(self._send(f"repos/{repository}/issues", "POST", payload)["number"])
        else:
            self._send(
                f"repos/{repository}/issues/{number}", "PATCH", {"title": title, "body": full_body}
            )
        if event and event_key:
            self._comment_once(number, event, event_key)
        return number, created

    def resolve(self, key: str, comment: str) -> int | None:
        number = self.find(key)
        if number is None:
            return None
        repository = self._repository()
        self._send(f"repos/{repository}/issues/{number}/comments", "POST", {"body": comment})
        self._send(
            f"repos/{repository}/issues/{number}",
            "PATCH",
            {"state": "closed", "state_reason": "completed"},
        )
        return number

    # ------------------------------------------------------------------ forge calls

    def _comment_once(self, number: int, text: str, event_key: str) -> None:
        marker = f"<!-- {_EVENT_MARKER}:{event_key} -->"
        path = f"repos/{self._repository()}/issues/{number}/comments?per_page=100"
        if any(marker in str(comment.get("body") or "") for comment in self._list(path)):
            return
        self._send(
            f"repos/{self._repository()}/issues/{number}/comments",
            "POST",
            {"body": f"{marker}\n{text.strip()}\n"},
        )

    def _list(self, path: str) -> list[dict[str, Any]]:
        run = self._transport.run(["api", "--paginate", path])
        if run.returncode:
            raise RuntimeError(f"gh api {path}: {run.stderr.strip()}")
        return self.decode_pages(run.stdout)

    def _send(self, path: str, method: str, payload: dict[str, Any]) -> Any:
        return self._transport.json(
            ["api", path, "--method", method, "--input", "-"], stdin=json.dumps(payload)
        )

    @staticmethod
    def decode_pages(text: str) -> list[dict[str, Any]]:
        """Every object in `gh api --paginate` output, which is one merged JSON array on
        current releases of the client and concatenated arrays (`[...][...]`) on older
        ones; decoding value by value reads both."""
        decoder = json.JSONDecoder()
        items: list[dict[str, Any]] = []
        index = 0
        while True:
            while index < len(text) and text[index].isspace():
                index += 1
            if index == len(text):
                return items
            page, index = decoder.raw_decode(text, index)
            if not isinstance(page, list):
                raise TypeError("a paginated listing must be a JSON array")
            items.extend(item for item in page if isinstance(item, dict))

    # ------------------------------------------------------------------ the command

    @staticmethod
    def declare(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        actions = parser.add_subparsers(dest="tracking_action", required=True)
        raise_ = actions.add_parser("raise", help="open or update the issue for a condition")
        raise_.add_argument("--key", required=True, help="the condition's stable identifier")
        raise_.add_argument("--title", required=True)
        raise_.add_argument("--body", required=True, help="the issue body, kept current")
        raise_.add_argument("--event", default="", help="a comment added once per --event-key")
        raise_.add_argument("--event-key", default="")
        raise_.add_argument("--label", action="append", default=[], help="an existing label")
        resolve = actions.add_parser("resolve", help="comment on and close the issue, if open")
        resolve.add_argument("--key", required=True)
        resolve.add_argument("--comment", required=True)
        return parser

    @classmethod
    def dispatch(cls, args: argparse.Namespace) -> int:
        tracker = cls()
        try:
            if args.tracking_action == "raise":
                number, created = tracker.raise_issue(
                    args.key,
                    args.title,
                    args.body,
                    event=args.event,
                    event_key=args.event_key,
                    labels=args.label,
                )
                print(f"vibey-gh: {'opened' if created else 'updated'} #{number} for {args.key}")
                return 0
            closed = tracker.resolve(args.key, args.comment)
        except (RuntimeError, TypeError, ValueError) as exc:
            print(f"vibey-gh: {exc}")
            return 1
        print(
            f"vibey-gh: closed #{closed} for {args.key}"
            if closed is not None
            else f"vibey-gh: nothing open for {args.key}"
        )
        return 0
