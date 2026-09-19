# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The Forgejo forge adapter: the forge-neutral verbs, spoken as REST API calls.

Implements `vibey_gh.interfaces.forge_adapter_interface` on the `ForgejoTransport`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from vibey_gh.forge import (
    ChangeRequest,
    ForgeComment,
    ForgeIssue,
    ForgeRelease,
    ForgeReview,
)
from vibey_gh.forgejo_transport import ForgejoTransport
from vibey_gh.interfaces.forge_adapter_interface import ForgeAdapterInterface
from vibey_gh.interfaces.forge_transport_interface import ForgeTransportInterface, WorkingDirectory


@dataclass(frozen=True)
class ForgejoForge(ForgeAdapterInterface):
    """One Forgejo repository, reached through `ForgejoTransport`."""

    root: WorkingDirectory
    transport: ForgeTransportInterface = field(default_factory=ForgejoTransport)

    def list_artifacts(
        self,
        forge_class: str,
        since: str | None = None,
        page: int = 1,
        limit: int = 100,
    ) -> tuple[list[dict[str, Any]], str]:
        paths = {
            "issue": "repos/{{repo}}/issues",
            "change-request": "repos/{{repo}}/pulls",
            "release": "repos/{{repo}}/releases",
            "label": "repos/{{repo}}/labels",
        }
        path = paths.get(forge_class)
        if path is None:
            return [], f"Forgejo adapter does not support artifact class {forge_class!r}"
        query = f"?page={page}&limit={limit}"
        if since:
            query += f"&updated_after={since}"
        value, problem = self.transport.survey([path + query], cwd=self.root)
        if problem:
            return [], problem
        if not isinstance(value, list):
            return [], "Expected list of artifacts"
        return [item for item in value if isinstance(item, dict)], ""

    def open_change_request_heads(self, *, limit: int) -> tuple[frozenset[str], str]:
        # Forgejo/Gitea: /repos/{owner}/{repo}/pulls
        pulls, problem = self.transport.survey(
            ["repos/{{repo}}/pulls?state=open&limit=" + str(limit)], cwd=self.root
        )
        heads = frozenset(
            head
            for pull in pulls
            if isinstance(pull, dict)
            and isinstance(head := pull.get("head", {}).get("branch", ""), str)
        )
        return heads, problem

    def releases(self, *, limit: int) -> tuple[tuple[ForgeRelease, ...], str]:
        # Forgejo/Gitea: /repos/{owner}/{repo}/releases
        rows, problem = self.transport.survey(
            ["repos/{{repo}}/releases?limit=" + str(limit)], cwd=self.root
        )
        releases = tuple(
            ForgeRelease(
                tag=str(row.get("tag_name", "")),
                name=str(row.get("name", "")),
                draft=False,
            )
            for row in rows
            if isinstance(row, dict)
        )
        return releases, problem

    def get_change_request(self, number: int) -> tuple[ChangeRequest | None, str]:
        val, problem = self.transport.survey(["repos/{{repo}}/pulls/" + str(number)], cwd=self.root)
        if problem:
            return None, problem
        if not isinstance(val, dict):
            return None, f"Expected object for PR {number}"
        return ChangeRequest(
            number=int(val.get("id", 0)),
            head_ref=str(val.get("head", {}).get("branch", "")),
            head_sha=str(val.get("head", {}).get("sha", "")),
            base_ref=str(val.get("base", {}).get("ref", "")),
            title=str(val.get("title", "")),
            body=str(val.get("body", "")),
            state=str(val.get("state", "")),
        ), ""

    def get_issue(self, number: int) -> tuple[ForgeIssue | None, str]:
        val, problem = self.transport.survey(
            ["repos/{{repo}}/issues/" + str(number)], cwd=self.root
        )
        if problem:
            return None, problem
        if not isinstance(val, dict):
            return None, f"Expected object for issue {number}"
        return ForgeIssue(
            number=int(val.get("id", 0)),
            title=str(val.get("title", "")),
            body=str(val.get("body", "")),
            state=str(val.get("state", "")),
        ), ""

    def get_issue_thread(self, number: int) -> tuple[tuple[ForgeComment, ...], str]:
        # Forgejo: /repos/{owner}/{repo}/issues/{id}/comments
        val, problem = self.transport.survey(
            ["repos/{{repo}}/issues/" + str(number) + "/comments"], cwd=self.root
        )
        if problem:
            val, problem = self.transport.survey(
                ["repos/{{repo}}/pulls/" + str(number) + "/comments"], cwd=self.root
            )

        if problem:
            return (), problem
        if not isinstance(val, list):
            return (), "Comments field is not a list"
        return tuple(
            ForgeComment(
                id=str(c.get("id", "")),
                author=str(c.get("user", {}).get("username", "")),
                body=str(c.get("body", "")),
            )
            for c in val
            if isinstance(c, dict)
        ), ""

    def get_reviews(self, number: int) -> tuple[tuple[ForgeReview, ...], str]:
        # Forgejo reviews are simpler; we can check for approval status
        _, problem = self.transport.survey(["repos/{{repo}}/pulls/" + str(number)], cwd=self.root)
        if problem:
            return (), problem
        # Simplification: use the PR state or specific approval fields if available
        return (), ""

    def get_check_results(self, head_sha: str) -> tuple[tuple[Any, ...], str]:
        val, problem = self.transport.survey(
            ["repos/{{repo}}/commits/" + head_sha + "/statuses"], cwd=self.root
        )
        if problem:
            return (), problem
        if not isinstance(val, list):
            return (), "Check results are not a list"
        return tuple(
            {"name": r.get("context", ""), "head_sha": head_sha, "conclusion": r.get("state", "")}
            for r in val
            if isinstance(r, dict)
        ), ""

    def create_comment(self, number: int, body: str) -> tuple[ForgeComment | None, str]:
        # Try issues then PRs
        _, problem = self.transport.survey(
            ["repos/{{repo}}/issues/" + str(number) + "/comments", "POST", body], cwd=self.root
        )
        if problem:
            _, problem = self.transport.survey(
                ["repos/{{repo}}/pulls/" + str(number) + "/comments", "POST", body], cwd=self.root
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
            payload["body"] = body
        _, problem = self.transport.survey(
            ["repos/{{repo}}/pulls/" + str(number), "PATCH", json.dumps(payload)], cwd=self.root
        )
        if problem:
            return None, problem
        return self.get_change_request(number)

    def merge_change_request(
        self, number: int, method: str = "squash", admin: bool = False
    ) -> tuple[bool, str]:
        # Forgejo: POST /repos/{owner}/{repo}/pulls/{id}/merge
        _, problem = self.transport.survey(
            ["repos/{{repo}}/pulls/" + str(number) + "/merge", "POST", ""], cwd=self.root
        )
        if problem:
            return False, problem
        return True, ""

    def create_release(
        self, tag: str, name: str, body: str, draft: bool = False
    ) -> tuple[ForgeRelease | None, str]:
        payload = {"tag_name": tag, "name": name, "note": body}
        _, problem = self.transport.survey(
            ["repos/{{repo}}/releases", "POST", json.dumps(payload)], cwd=self.root
        )
        if problem:
            return None, problem
        return ForgeRelease(tag=tag, name=name, draft=draft), ""

    def set_protected_ref(self, ref: str, protected: bool) -> tuple[bool, str]:
        if protected:
            _, problem = self.transport.survey(
                ["repos/{{repo}}/branch_protections", "POST", json.dumps({"branch": ref})],
                cwd=self.root,
            )
        else:
            _, problem = self.transport.survey(
                ["repos/{{repo}}/branch_protections/" + ref, "DELETE", ""], cwd=self.root
            )
        if problem:
            return False, problem
        return True, ""

    def get_protected_refs(self) -> tuple[frozenset[str], str]:
        val, problem = self.transport.survey(["repos/{{repo}}/branch_protections"], cwd=self.root)
        if problem:
            return frozenset(), problem
        if not isinstance(val, list):
            return frozenset(), "Expected list of protected branches"
        return frozenset(str(b.get("branch", "")) for b in val if isinstance(b, dict)), ""
