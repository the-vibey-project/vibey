# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Durable automation state carried in exactly one GitHub comment.

Both pull-request and issue automation need the same three awkward things: a JSON payload
hidden in an HTML comment so a human reads prose instead of a blob, a way to find the one
comment holding it among ordinary conversation, and an update path that survives the three
shapes GitHub hands back a comment identity in. That last part is why this is shared code
rather than a copy in each module — the REST/GraphQL fallback below was written once in
response to a real 404 and is not worth getting subtly different twice.

Pull requests and issues are the same object to this API: `gh pr comment` and
`gh issue comment` create, and `repos/{repo}/issues/comments/{id}` edits either one.

Every `gh` call made here rides on `vibey_gh.gh_transport`, and so does every call made
through `gh_json`, `repository` and `upsert_comment` from the modules that share this state.
The argv and working directory are the ones this module built before the transport existed.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Sequence
from typing import Any, cast

from vibey_gh.gh_transport import GhTransport
from vibey_gh.interfaces.gh_transport_interface import GhTransportInterface

_transport: GhTransportInterface = GhTransport()


# Module-level rather than a method (vibey ADR-0016), like the other two `gh` entry points
# below: these three are a facade that six modules call by name, that `pr_automation` binds
# once at import, and that their tests replace by attribute. Keeping the names where they
# are is what lets the transport underneath change without any of those callers noticing.
def gh_json(*args: str) -> Any:
    return _transport.json(args)


def marker_pattern(marker: str) -> re.Pattern[str]:
    """The regex that finds one automation's state payload and nothing else's."""
    return re.compile(r"<!-- " + re.escape(marker) + r":(\{.*?\}) -->", re.DOTALL)


def parse_payload(
    comments: Sequence[dict[str, Any] | str], pattern: re.Pattern[str]
) -> dict[str, Any] | None:
    """The newest valid payload, ignoring ordinary or malformed comments."""
    for item in reversed(comments):
        body = item if isinstance(item, str) else str(item.get("body", ""))
        match = pattern.search(body)
        if not match:
            continue
        try:
            # The pattern captures a brace-delimited group, so successful JSON here is
            # always an object; a malformed one belongs to some other comment entirely.
            return cast(dict[str, Any], json.loads(match.group(1)))
        except json.JSONDecodeError:
            continue
    return None


def render_body(marker: str, payload: dict[str, Any], heading: str, summary: str) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"<!-- {marker}:{encoded} -->\n## {heading}\n\n{summary.strip()}\n"


# Module-level: part of the facade described above `gh_json`.
def repository() -> str:
    """The `owner/name` every `gh` call is given explicitly rather than inferring."""
    name = os.environ.get("GH_REPO")
    if not name:
        name = str(gh_json("repo", "view", "--json", "nameWithOwner")["nameWithOwner"])
    return name


# Module-level: part of the facade described above `gh_json`.
def upsert_comment(
    number: int,
    body: str,
    comments: Sequence[dict[str, Any]],
    pattern: re.Pattern[str],
    *,
    subject: str = "pr",
    error: str = "could not persist automation state",
) -> None:
    """Create the state comment, or edit the existing one in place."""
    repository_name = repository()
    existing: dict[str, Any] | None = None
    for comment in reversed(comments):
        if pattern.search(str(comment.get("body", ""))):
            existing = comment
            break
    if existing is None:
        run = _transport.run(
            [subject, "comment", str(number), "--repo", repository_name, "--body", body]
        )
    elif existing.get("databaseId") is not None:
        comment_id = existing["databaseId"]
        run = _transport.run(
            [
                "api",
                f"repos/{repository_name}/issues/comments/{comment_id}",
                "--method",
                "PATCH",
                "--field",
                f"body={body}",
            ]
        )
    else:
        # GraphQL comments sometimes expose only an opaque `IC_...` node ID. Passing
        # that value to the REST issues/comments endpoint produces a misleading 404.
        comment_id = existing.get("id")
        if not comment_id:
            raise RuntimeError(f"{error}: comment has no ID")
        mutation = (
            "mutation($id:ID!,$body:String!){updateIssueComment(input:{id:$id,body:$body})"
            "{issueComment{id}}}"
        )
        run = _transport.run(
            [
                "api",
                "graphql",
                "--field",
                f"query={mutation}",
                "--field",
                f"id={comment_id}",
                "--field",
                f"body={body}",
            ]
        )
    if run.returncode:
        raise RuntimeError(f"{error}: {run.stderr.strip()}")
