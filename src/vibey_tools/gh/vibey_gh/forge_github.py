# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The GitHub forge adapter: the forge-neutral verbs, spoken as `gh` command lines.

Implements `vibey_gh.interfaces.forge_adapter_interface` on the `gh` transport. Every
command line here is one that already ran before the adapter existed, moved rather than
rewritten, with the same argv and the same working directory: the adapter's job is to
translate the answer into `vibey_gh.forge` nouns, not to ask a different question. The
proof is in `test/test_forge_github.py`, which drives the code as it stood and the code as
it stands through one fake `gh` and requires the same invocations and the same report.

`gh` runs in the repository's clone, as it always has, so it finds the repository from
the clone's own remote rather than from anything this process tells it.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any
from urllib.parse import urlencode

from vibey_gh.forge import (
    ChangeRequest,
    ForgeComment,
    ForgeIssue,
    ForgeRelease,
    ForgeReview,
)
from vibey_gh.gh_transport import GhTransport
from vibey_gh.interfaces.forge_adapter_interface import ForgeAdapterInterface
from vibey_gh.interfaces.gh_transport_interface import GhTransportInterface, WorkingDirectory

# The host `gh` talks to when nothing names another. Naming it changes nothing, so a
# `[platform] host` equal to it is not exported to the client (see `GhTransport.host`).
GH_DEFAULT_HOST = "github.com"


@dataclass(frozen=True)
class GitHubForge(ForgeAdapterInterface):
    """One GitHub repository, reached through `gh` run in its clone at `root`."""

    root: WorkingDirectory
    repository: str = ""
    transport: GhTransportInterface = field(default_factory=GhTransport)

    def for_repository(self, repository: str) -> GitHubForge:
        return replace(self, repository=repository)

    def list_artifacts(
        self,
        forge_class: str,
        since: str | None = None,
        page: int = 1,
        limit: int = 100,
    ) -> tuple[list[dict[str, Any]], str]:
        # Map neutral class name to gh endpoint
        mapping = {
            "issue": f"repos/{self._repository()}/issues?state=all&sort=updated&direction=asc",
            "comment": f"repos/{self._repository()}/issues/comments?sort=updated&direction=asc",
            "change-request": f"repos/{self._repository()}/pulls?state=all&sort=updated&direction=desc",
            "review-comment": f"repos/{self._repository()}/pulls/comments?sort=updated&direction=asc",
            "label": f"repos/{self._repository()}/labels",
            "milestone": f"repos/{self._repository()}/milestones?state=all",
            "release": f"repos/{self._repository()}/releases",
            "tag": f"repos/{self._repository()}/tags",
        }
        path = mapping.get(forge_class)
        if not path:
            return [], f"GitHub adapter does not support artifact class {forge_class!r}"

        query = {"page": str(page), "per_page": str(limit)}
        if since and forge_class in {"issue", "comment", "review-comment"}:
            query["since"] = since
        separator = "&" if "?" in path else "?"
        val, problem = self.transport.survey(
            ["api", path + separator + urlencode(query)], cwd=self.root
        )
        if problem:
            return [], problem
        if not isinstance(val, list):
            return [], "Expected list of artifacts"
        return [item for item in val if isinstance(item, dict)], ""

    def open_change_request_heads(self, *, limit: int) -> tuple[frozenset[str], str]:
        pulls, problem = self._listing("pr", "list", "--json", "headRefName", "--limit", str(limit))
        heads = frozenset(
            head
            for pull in pulls
            if isinstance(pull, dict) and isinstance(head := pull.get("headRefName", ""), str)
        )
        return heads, problem

    def releases(self, *, limit: int) -> tuple[tuple[ForgeRelease, ...], str]:
        rows, problem = self._listing(
            "release", "list", "--json", "tagName,name,isDraft", "--limit", str(limit)
        )
        releases = tuple(
            ForgeRelease(
                tag=str(row.get("tagName") or ""),
                name=str(row.get("name") or ""),
                draft=bool(row.get("isDraft")),
            )
            for row in rows
            if isinstance(row, dict)
        )
        return releases, problem

    def get_change_request(self, number: int) -> tuple[ChangeRequest | None, str]:
        val, problem = self.transport.survey(
            [
                "pr",
                "view",
                str(number),
                "--json",
                "number,headRefName,headRefOid,baseRefName,title,body,state",
            ],
            cwd=self.root,
        )
        if problem:
            return None, problem
        if not isinstance(val, dict):
            return None, f"Expected object for PR {number}"
        return (
            ChangeRequest(
                number=int(val.get("number", 0)),
                head_ref=str(val.get("headRefName", "")),
                head_sha=str(val.get("headRefOid", "")),
                base_ref=str(val.get("baseRefName", "")),
                title=str(val.get("title", "")),
                body=str(val.get("body", "")),
                state=str(val.get("state", "")),
            ),
            "",
        )

    def get_issue(self, number: int) -> tuple[ForgeIssue | None, str]:
        val, problem = self.transport.survey(
            ["issue", "view", str(number), "--json", "number,title,body,state"], cwd=self.root
        )
        if problem:
            return None, problem
        if not isinstance(val, dict):
            return None, f"Expected object for issue {number}"
        return (
            ForgeIssue(
                number=int(val.get("number", 0)),
                title=str(val.get("title", "")),
                body=str(val.get("body", "")),
                state=str(val.get("state", "")),
            ),
            "",
        )

    def get_issue_thread(self, number: int) -> tuple[tuple[ForgeComment, ...], str]:
        val, problem = self.transport.survey(
            ["issue", "view", str(number), "--json", "comments"], cwd=self.root
        )
        if problem:
            return (), problem
        if not isinstance(val, dict):
            return (), f"Expected object for issue {number}"
        comments = val.get("comments", [])
        if not isinstance(comments, list):
            return (), "Comments field is not a list"
        return (
            tuple(
                ForgeComment(
                    id=str(c.get("id", "")),
                    author=str(c.get("author", "")),
                    body=str(c.get("body", "")),
                )
                for c in comments
                if isinstance(c, dict)
            ),
            "",
        )

    def get_reviews(self, number: int) -> tuple[tuple[ForgeReview, ...], str]:
        val, problem = self.transport.survey(
            ["api", f"repos/{self._repository()}/pulls/{number}/reviews"], cwd=self.root
        )
        if problem:
            return (), problem
        if not isinstance(val, list):
            return (), "Expected list of reviews"
        return (
            tuple(
                ForgeReview(
                    id=str(r.get("id", "")),
                    author=str(r.get("user", {}).get("login", "")),
                    verdict=str(r.get("state", "")),
                    body=str(r.get("body", "")),
                )
                for r in val
                if isinstance(r, dict)
            ),
            "",
        )

    def get_check_results(self, head_sha: str) -> tuple[tuple[Any, ...], str]:
        val, problem = self.transport.survey(
            ["api", f"repos/{self._repository()}/commits/{head_sha}/check-runs"], cwd=self.root
        )
        if problem:
            return (), problem
        if not isinstance(val, dict):
            return (), "Expected object for check-runs"
        runs = val.get("check_runs", [])
        if not isinstance(runs, list):
            return (), "check_runs field is not a list"
        return (
            tuple(
                {
                    "name": r.get("name", ""),
                    "head_sha": head_sha,
                    "conclusion": r.get("conclusion", ""),
                }
                for r in runs
                if isinstance(r, dict)
            ),
            "",
        )

    def create_comment(self, number: int, body: str) -> tuple[ForgeComment | None, str]:
        _, problem = self.transport.survey(
            ["issue", "comment", str(number), "--body", body], cwd=self.root
        )
        if problem:
            return None, problem
        return ForgeComment(id="unknown", author="system", body=body), ""

    def update_change_request(
        self, number: int, title: str | None = None, body: str | None = None
    ) -> tuple[ChangeRequest | None, str]:
        args = ["pr", "edit", str(number)]
        if title:
            args += ["-t", title]
        if body:
            args += ["-b", body]
        _, problem = self.transport.survey(args, cwd=self.root)
        if problem:
            return None, problem
        return self.get_change_request(number)

    def merge_change_request(
        self, number: int, method: str = "squash", admin: bool = False
    ) -> tuple[bool, str]:
        args = ["pr", "merge", str(number), f"--{method}"]
        if admin:
            args += ["--admin"]
        _, problem = self.transport.survey(args, cwd=self.root)
        if problem:
            return False, problem
        return True, ""

    def create_release(
        self, tag: str, name: str, body: str, draft: bool = False
    ) -> tuple[ForgeRelease | None, str]:
        args = ["release", "create", tag, "-t", name, "-b", body]
        if draft:
            args += ["--draft"]
        _, problem = self.transport.survey(args, cwd=self.root)
        if problem:
            return None, problem
        return ForgeRelease(tag=tag, name=name, draft=draft), ""

    def set_protected_ref(self, ref: str, protected: bool) -> tuple[bool, str]:
        method = "PUT" if protected else "DELETE"
        _, problem = self.transport.survey(
            ["api", f"repos/{self._repository()}/branches/{ref}/protection", "--method", method],
            cwd=self.root,
        )
        if problem:
            return False, problem
        return True, ""

    def get_protected_refs(self) -> tuple[frozenset[str], str]:
        val, problem = self.transport.survey(
            ["api", f"repos/{self._repository()}/branches"], cwd=self.root
        )
        if problem:
            return frozenset(), problem
        if not isinstance(val, list):
            return frozenset(), "Expected list of branches"
        protected = {
            str(b.get("name", "")) for b in val if isinstance(b, dict) and b.get("protected", False)
        }
        return frozenset(protected), ""

    def _listing(self, *args: str) -> tuple[list[Any], str]:
        value, problem = self.transport.survey(args, cwd=self.root)
        if problem:
            return [], problem
        if not isinstance(value, list):
            label = " ".join((self.transport.executable, *args[:2]))
            return [], f"`{label}` returned a JSON object where a listing was expected"
        return value, ""

    def _repository(self) -> str:
        return self.repository
