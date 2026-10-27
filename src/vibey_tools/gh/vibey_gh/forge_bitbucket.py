# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The Bitbucket Cloud forge adapter: the forge-neutral verbs, spoken as REST 2.0 API calls (#298).

Implements `vibey_gh.interfaces.forge_adapter_interface` on the `BitbucketTransport`. The
repository is `workspace/slug`, and every path below is relative to `/2.0/`.

Bitbucket Cloud has no equivalent for a few verbs, and each of them answers with a
`NotSupported` problem that names the verb and the reason rather than an empty value, because
a forge that cannot be asked must never read as a forge that answered "nothing":

- **releases and labels.** Bitbucket has neither object. A tag is the nearest thing to a release.
- **an administrator merge.** Bitbucket has no way to merge past a failing branch restriction.

The transport follows a listing's `next` links to the end, so a verb that is asked for `limit`
rows takes the first `limit` of what came back; it never reports a truncated list as whole.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from typing import Any
from urllib.parse import quote

from vibey_gh.bitbucket_transport import BitbucketTransport
from vibey_gh.forge import (
    ChangeRequest,
    ForgeComment,
    ForgeIssue,
    ForgeKind,
    ForgeRelease,
    ForgeReview,
    NotSupported,
)
from vibey_gh.interfaces.forge_adapter_interface import ForgeAdapterInterface
from vibey_gh.interfaces.forge_transport_interface import ForgeTransportInterface, WorkingDirectory

# Forge-neutral merge methods to Bitbucket's `merge_strategy` values.
MERGE_STRATEGIES = {"squash": "squash", "merge": "merge_commit", "rebase": "fast_forward"}

# Bitbucket's commit-status states to the neutral `conclusion`. A state not named here is still
# running, and an unfinished check is never a passing one, so it reads as empty.
CHECK_CONCLUSIONS = {"SUCCESSFUL": "success", "FAILED": "failure", "STOPPED": "cancelled"}

# The branch-restriction kinds that stop a branch from being rewritten. A protected ref has both.
REWRITE_KINDS = ("force", "delete")

# Every state of a pull request, because Bitbucket lists only the open ones unless it is asked.
ALL_PULL_REQUEST_STATES = "&".join(
    f"state={state}" for state in ("OPEN", "MERGED", "DECLINED", "SUPERSEDED")
)

# Why a listing of an object Bitbucket does not have is not an empty list.
_NO_OBJECT = {
    "release": "Bitbucket has no release object; a tag is the nearest thing",
    "label": "Bitbucket has no labels on issues or pull requests",
}


@dataclass(frozen=True)
class BitbucketForge(ForgeAdapterInterface):
    """One Bitbucket Cloud repository, reached through `BitbucketTransport`."""

    root: WorkingDirectory
    repository: str = ""
    transport: ForgeTransportInterface = field(default_factory=BitbucketTransport)

    def for_repository(self, repository: str) -> BitbucketForge:
        return replace(self, repository=repository)

    def list_artifacts(
        self,
        forge_class: str,
        since: str | None = None,
        page: int = 1,
        limit: int = 100,
    ) -> tuple[list[dict[str, Any]], str]:
        if forge_class in ("release", "label"):
            return [], self._unsupported(f"{forge_class} listing", _NO_OBJECT[forge_class])
        paths = {
            "issue": f"{self._base()}/issues",
            "change-request": f"{self._base()}/pullrequests?{ALL_PULL_REQUEST_STATES}",
        }
        path = paths.get(forge_class)
        if path is None:
            return [], f"Bitbucket adapter does not support artifact class {forge_class!r}"
        query = f"page={page}&pagelen={limit}"
        if since:
            query += "&q=" + quote(f'updated_on>"{since}"', safe="")
        value, problem = self.transport.survey(
            [path + ("&" if "?" in path else "?") + query], cwd=self.root
        )
        if problem:
            return [], problem
        if not isinstance(value, list):
            return [], "Expected list of artifacts"
        return [item for item in value if isinstance(item, dict)][:limit], ""

    def open_change_request_heads(self, *, limit: int) -> tuple[frozenset[str], str]:
        pulls, problem = self.transport.survey(
            [f"{self._base()}/pullrequests?state=OPEN&pagelen={limit}"], cwd=self.root
        )
        if problem:
            return frozenset(), problem
        if not isinstance(pulls, list):
            return frozenset(), "Expected list of pull requests"
        heads = (
            BitbucketForge._name(pull.get("source"), "branch", "name")
            for pull in pulls[:limit]
            if isinstance(pull, dict)
        )
        return frozenset(head for head in heads if head), ""

    def releases(self, *, limit: int) -> tuple[tuple[ForgeRelease, ...], str]:
        return (), self._unsupported("releases", _NO_OBJECT["release"])

    def get_change_request(self, number: int) -> tuple[ChangeRequest | None, str]:
        value, problem = self.transport.survey(
            [f"{self._base()}/pullrequests/{number}"], cwd=self.root
        )
        if problem:
            return None, problem
        if not isinstance(value, dict):
            return None, f"Expected object for PR {number}"
        source = value.get("source")
        destination = value.get("destination")
        return (
            ChangeRequest(
                number=int(value.get("id", 0)),
                head_ref=BitbucketForge._name(source, "branch", "name"),
                head_sha=BitbucketForge._name(source, "commit", "hash"),
                base_ref=BitbucketForge._name(destination, "branch", "name"),
                title=str(value.get("title", "")),
                body=str(value.get("description", "")),
                state=str(value.get("state", "")),
            ),
            "",
        )

    def get_issue(self, number: int) -> tuple[ForgeIssue | None, str]:
        value, problem = self.transport.survey([f"{self._base()}/issues/{number}"], cwd=self.root)
        if problem:
            return None, problem
        if not isinstance(value, dict):
            return None, f"Expected object for issue {number}"
        return (
            ForgeIssue(
                number=int(value.get("id", 0)),
                title=str(value.get("title", "")),
                body=BitbucketForge._name(value, "content", "raw"),
                state=str(value.get("state", "")),
            ),
            "",
        )

    def get_issue_thread(self, number: int) -> tuple[tuple[ForgeComment, ...], str]:
        value, problem = self.transport.survey(
            [f"{self._base()}/issues/{number}/comments"], cwd=self.root
        )
        if problem:
            value, problem = self.transport.survey(
                [f"{self._base()}/pullrequests/{number}/comments"], cwd=self.root
            )
        if problem:
            return (), problem
        if not isinstance(value, list):
            return (), "Comments field is not a list"
        return tuple(BitbucketForge._comment(row) for row in value if isinstance(row, dict)), ""

    def get_reviews(self, number: int) -> tuple[tuple[ForgeReview, ...], str]:
        value, problem = self.transport.survey(
            [f"{self._base()}/pullrequests/{number}"], cwd=self.root
        )
        if problem:
            return (), problem
        if not isinstance(value, dict):
            return (), f"Expected object for PR {number}"
        participants = value.get("participants", [])
        if not isinstance(participants, list):
            return (), "Participants field is not a list"
        reviews = []
        for row in participants:
            if not isinstance(row, dict) or row.get("role") != "REVIEWER":
                continue
            verdict = BitbucketForge._verdict(row)
            if verdict:
                user = row.get("user")
                reviews.append(
                    ForgeReview(
                        id=BitbucketForge._name(user, "account_id")
                        or BitbucketForge._name(user, "uuid"),
                        author=BitbucketForge._author(user),
                        verdict=verdict,
                    )
                )
        return tuple(reviews), ""

    def get_check_results(self, head_sha: str) -> tuple[tuple[Any, ...], str]:
        value, problem = self.transport.survey(
            [f"{self._base()}/commit/{quote(head_sha, safe='')}/statuses"], cwd=self.root
        )
        if problem:
            return (), problem
        if not isinstance(value, list):
            return (), "Check results are not a list"
        return (
            tuple(
                {
                    "name": str(row.get("name") or row.get("key", "")),
                    "head_sha": head_sha,
                    "conclusion": CHECK_CONCLUSIONS.get(str(row.get("state", "")), ""),
                }
                for row in value
                if isinstance(row, dict)
            ),
            "",
        )

    def create_comment(self, number: int, body: str) -> tuple[ForgeComment | None, str]:
        payload = json.dumps({"content": {"raw": body}})
        value, problem = self.transport.survey(
            [f"{self._base()}/pullrequests/{number}/comments", "POST", payload], cwd=self.root
        )
        if problem:
            value, problem = self.transport.survey(
                [f"{self._base()}/issues/{number}/comments", "POST", payload], cwd=self.root
            )
        if problem:
            return None, problem
        if isinstance(value, dict) and value.get("id") is not None:
            return BitbucketForge._comment(value), ""
        return ForgeComment(id="unknown", author="system", body=body), ""

    def update_change_request(
        self, number: int, title: str | None = None, body: str | None = None
    ) -> tuple[ChangeRequest | None, str]:
        payload: dict[str, str] = {}
        if title:
            payload["title"] = title
        if body:
            payload["description"] = body
        _, problem = self.transport.survey(
            [f"{self._base()}/pullrequests/{number}", "PUT", json.dumps(payload)], cwd=self.root
        )
        if problem:
            return None, problem
        return self.get_change_request(number)

    def merge_change_request(
        self, number: int, method: str = "squash", admin: bool = False
    ) -> tuple[bool, str]:
        if admin:
            return False, self._unsupported(
                "an administrator merge", "Bitbucket cannot merge past a failing branch restriction"
            )
        strategy = MERGE_STRATEGIES.get(method)
        if strategy is None:
            return False, f"Bitbucket has no merge method {method!r}"
        _, problem = self.transport.survey(
            [
                f"{self._base()}/pullrequests/{number}/merge",
                "POST",
                json.dumps({"merge_strategy": strategy}),
            ],
            cwd=self.root,
        )
        return (False, problem) if problem else (True, "")

    def create_release(
        self, tag: str, name: str, body: str, draft: bool = False
    ) -> tuple[ForgeRelease | None, str]:
        return None, self._unsupported("creating a release", _NO_OBJECT["release"])

    def set_protected_ref(self, ref: str, protected: bool) -> tuple[bool, str]:
        if protected:
            for kind in REWRITE_KINDS:
                payload = json.dumps({"kind": kind, "branch_match_kind": "glob", "pattern": ref})
                _, problem = self.transport.survey(
                    [f"{self._base()}/branch-restrictions", "POST", payload], cwd=self.root
                )
                if problem:
                    return False, problem
            return True, ""
        rows, problem = self.transport.survey(
            [f"{self._base()}/branch-restrictions"], cwd=self.root
        )
        if problem:
            return False, problem
        if not isinstance(rows, list):
            return False, "Expected list of branch restrictions"
        for row in rows:
            if (
                isinstance(row, dict)
                and row.get("pattern") == ref
                and row.get("kind") in REWRITE_KINDS
            ):
                _, problem = self.transport.survey(
                    [f"{self._base()}/branch-restrictions/{row.get('id')}", "DELETE", ""],
                    cwd=self.root,
                )
                if problem:
                    return False, problem
        return True, ""

    def get_protected_refs(self) -> tuple[frozenset[str], str]:
        rows, problem = self.transport.survey(
            [f"{self._base()}/branch-restrictions"], cwd=self.root
        )
        if problem:
            return frozenset(), problem
        if not isinstance(rows, list):
            return frozenset(), "Expected list of branch restrictions"
        return (
            frozenset(
                str(row["pattern"])
                for row in rows
                if isinstance(row, dict) and row.get("kind") in REWRITE_KINDS and row.get("pattern")
            ),
            "",
        )

    def _base(self) -> str:
        return f"repositories/{quote(self.repository, safe='/')}"

    @staticmethod
    def _unsupported(verb: str, reason: str) -> str:
        return NotSupported(ForgeKind.BITBUCKET, verb, reason).problem

    @staticmethod
    def _name(node: object, *path: str) -> str:
        """Walk `path` through nested objects; anything missing or not an object reads as empty."""
        for key in path:
            if not isinstance(node, dict):
                return ""
            node = node.get(key)
        return node if isinstance(node, str) else ""

    @staticmethod
    def _author(user: object) -> str:
        return BitbucketForge._name(user, "nickname") or BitbucketForge._name(user, "display_name")

    @staticmethod
    def _comment(row: dict[str, Any]) -> ForgeComment:
        return ForgeComment(
            id=str(row.get("id", "")),
            author=BitbucketForge._author(row.get("user")),
            body=BitbucketForge._name(row, "content", "raw"),
        )

    @staticmethod
    def _verdict(participant: dict[str, Any]) -> str:
        """A reviewer's neutral verdict, or empty while they have not given one."""
        if participant.get("state") == "changes_requested":
            return "CHANGES_REQUESTED"
        if participant.get("approved") is True or participant.get("state") == "approved":
            return "APPROVED"
        return ""
