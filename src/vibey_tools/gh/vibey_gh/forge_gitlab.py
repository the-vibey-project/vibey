# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The GitLab forge adapter: the forge-neutral verbs, spoken as REST API calls.

Implements `vibey_gh.interfaces.forge_adapter_interface` on the `GitLabTransport`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from typing import Any
from urllib.parse import quote

from vibey_gh.forge import (
    ChangeRequest,
    ForgeComment,
    ForgeIssue,
    ForgeRelease,
    ForgeReview,
)
from vibey_gh.gitlab_transport import GitLabTransport
from vibey_gh.interfaces.forge_adapter_interface import ForgeAdapterInterface
from vibey_gh.interfaces.forge_transport_interface import ForgeTransportInterface, WorkingDirectory


@dataclass(frozen=True)
class GitLabForge(ForgeAdapterInterface):
    """One GitLab repository, reached through `GitLabTransport`."""

    root: WorkingDirectory
    repository: str = ""
    transport: ForgeTransportInterface = field(default_factory=GitLabTransport)

    def for_repository(self, repository: str) -> GitLabForge:
        return replace(self, repository=repository)

    def list_artifacts(
        self,
        forge_class: str,
        since: str | None = None,
        page: int = 1,
        limit: int = 100,
    ) -> tuple[list[dict[str, Any]], str]:
        paths = {
            "issue": f"projects/{self._project()}/issues",
            "change-request": f"projects/{self._project()}/merge_requests",
            "release": f"projects/{self._project()}/releases",
            "label": f"projects/{self._project()}/labels",
        }
        path = paths.get(forge_class)
        if path is None:
            return [], f"GitLab adapter does not support artifact class {forge_class!r}"
        query = f"?page={page}&per_page={limit}"
        if since:
            query += f"&updated_after={since}"
        value, problem = self.transport.survey([path + query], cwd=self.root)
        if problem:
            return [], problem
        if not isinstance(value, list):
            return [], "Expected list of artifacts"
        return [item for item in value if isinstance(item, dict)], ""

    def open_change_request_heads(self, *, limit: int) -> tuple[frozenset[str], str]:
        # GitLab: /projects/:id/merge_requests
        pulls, problem = self.transport.survey(
            [f"projects/{self._project()}/merge_requests?state=opened&per_page={limit}"],
            cwd=self.root,
        )
        heads = frozenset(
            head
            for pull in pulls
            if isinstance(pull, dict) and isinstance(head := pull.get("source_branch"), str)
        )
        return heads, problem

    def releases(self, *, limit: int) -> tuple[tuple[ForgeRelease, ...], str]:
        # GitLab: /projects/:id/releases
        rows, problem = self.transport.survey(
            [f"projects/{self._project()}/releases?per_page={limit}"], cwd=self.root
        )
        releases = tuple(
            ForgeRelease(
                tag=str(row.get("tag_name", "")),
                name=str(row.get("name", "")),
                draft=False,  # GitLab releases don't have a simple 'draft' flag like GH
            )
            for row in rows
            if isinstance(row, dict)
        )
        return releases, problem

    def get_change_request(self, number: int) -> tuple[ChangeRequest | None, str]:
        val, problem = self.transport.survey(
            [f"projects/{self._project()}/merge_requests/{number}"], cwd=self.root
        )
        if problem:
            return None, problem
        if not isinstance(val, dict):
            return None, f"Expected object for MR {number}"
        return (
            ChangeRequest(
                number=int(val.get("iid", 0)),
                head_ref=str(val.get("source_branch", "")),
                head_sha=str(val.get("sha", "")),
                base_ref=str(val.get("target_branch", "")),
                title=str(val.get("title", "")),
                body=str(val.get("description", "")),
                state=str(val.get("state", "")),
            ),
            "",
        )

    def get_issue(self, number: int) -> tuple[ForgeIssue | None, str]:
        val, problem = self.transport.survey(
            [f"projects/{self._project()}/issues/{number}"], cwd=self.root
        )
        if problem:
            return None, problem
        if not isinstance(val, dict):
            return None, f"Expected object for issue {number}"
        return (
            ForgeIssue(
                number=int(val.get("iid", 0)),
                title=str(val.get("title", "")),
                body=str(val.get("description", "")),
                state=str(val.get("state", "")),
            ),
            "",
        )

    def get_issue_thread(self, number: int) -> tuple[tuple[ForgeComment, ...], str]:
        # Issues and MRs have separate comment endpoints in GitLab
        # We try issues first, then MRs
        val, problem = self.transport.survey(
            [f"projects/{self._project()}/issues/{number}/notes"], cwd=self.root
        )
        if problem:
            val, problem = self.transport.survey(
                [f"projects/{self._project()}/merge_requests/{number}/notes"], cwd=self.root
            )

        if problem:
            return (), problem
        if not isinstance(val, list):
            return (), "Comments field is not a list"
        return (
            tuple(
                ForgeComment(
                    id=str(c.get("id", "")),
                    author=str(c.get("author", {}).get("username", "")),
                    body=str(c.get("body", "")),
                )
                for c in val
                if isinstance(c, dict)
            ),
            "",
        )

    def get_reviews(self, number: int) -> tuple[tuple[ForgeReview, ...], str]:
        # GitLab reviews are "Approvals" or "Discussions"
        val, problem = self.transport.survey(
            [f"projects/{self._project()}/merge_requests/{number}/approvals"], cwd=self.root
        )
        if problem:
            return (), problem
        # Simplification: map approved status to a review verdict
        if not isinstance(val, dict):
            return (), "Approvals response is not an object"
        return (
            (
                ForgeReview(
                    id="approval",
                    author="system",
                    verdict="APPROVED",
                    body="Approved via GitLab approvals",
                ),
            )
            if val.get("approved", False)
            else ()
        ), ""

    def get_check_results(self, head_sha: str) -> tuple[tuple[Any, ...], str]:
        # GitLab: /projects/:id/commits/:sha/statuses
        val, problem = self.transport.survey(
            [f"projects/{self._project()}/commits/{head_sha}/statuses"], cwd=self.root
        )
        if problem:
            return (), problem
        if not isinstance(val, list):
            return (), "Check results are not a list"
        return (
            tuple(
                {"name": r.get("name", ""), "head_sha": head_sha, "conclusion": r.get("status", "")}
                for r in val
                if isinstance(r, dict)
            ),
            "",
        )

    def create_comment(self, number: int, body: str) -> tuple[ForgeComment | None, str]:
        # We'll try creating on issue, then MR
        _, problem = self.transport.survey(
            [f"projects/{self._project()}/issues/{number}/notes", "POST", body], cwd=self.root
        )
        if problem:
            _, problem = self.transport.survey(
                [f"projects/{self._project()}/merge_requests/{number}/notes", "POST", body],
                cwd=self.root,
            )
        if problem:
            return None, problem
        return ForgeComment(id="unknown", author="system", body=body), ""

    def update_change_request(
        self, number: int, title: str | None = None, body: str | None = None
    ) -> tuple[ChangeRequest | None, str]:
        payload = {}
        if title:
            payload["title"] = title
        if body:
            payload["description"] = body
        _, problem = self.transport.survey(
            [f"projects/{self._project()}/merge_requests/{number}", "PUT", json.dumps(payload)],
            cwd=self.root,
        )
        if problem:
            return None, problem
        return self.get_change_request(number)

    def merge_change_request(
        self, number: int, method: str = "squash", admin: bool = False
    ) -> tuple[bool, str]:
        # GitLab: POST /projects/:id/merge_requests/:iid/merge
        # method: squash is handled via a different API or project setting
        _, problem = self.transport.survey(
            [f"projects/{self._project()}/merge_requests/{number}/merge", "POST", ""],
            cwd=self.root,
        )
        if problem:
            return False, problem
        return True, ""

    def create_release(
        self, tag: str, name: str, body: str, draft: bool = False
    ) -> tuple[ForgeRelease | None, str]:
        payload = {"tag_name": tag, "name": name, "description": body}
        _, problem = self.transport.survey(
            [f"projects/{self._project()}/releases", "POST", json.dumps(payload)], cwd=self.root
        )
        if problem:
            return None, problem
        return ForgeRelease(tag=tag, name=name, draft=draft), ""

    def set_protected_ref(self, ref: str, protected: bool) -> tuple[bool, str]:
        # GitLab: /projects/:id/protected_branches
        if protected:
            _, problem = self.transport.survey(
                [
                    f"projects/{self._project()}/protected_branches",
                    "POST",
                    json.dumps({"name": ref}),
                ],
                cwd=self.root,
            )
        else:
            _, problem = self.transport.survey(
                [f"projects/{self._project()}/protected_branches/{ref}", "DELETE", ""],
                cwd=self.root,
            )
        if problem:
            return False, problem
        return True, ""

    def get_protected_refs(self) -> tuple[frozenset[str], str]:
        val, problem = self.transport.survey(
            [f"projects/{self._project()}/protected_branches"], cwd=self.root
        )
        if problem:
            return frozenset(), problem
        if not isinstance(val, list):
            return frozenset(), "Expected list of protected branches"
        return frozenset(str(b.get("name", "")) for b in val if isinstance(b, dict)), ""

    def _project(self) -> str:
        return quote(self.repository, safe="")
