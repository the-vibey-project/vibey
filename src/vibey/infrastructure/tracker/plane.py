# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Plane adapter implementing the Tracker port (ADR-0042).

Self-hosted Plane (sovereign ticketing default) over stdlib urllib.
"""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request

from vibey.application.interfaces.tracker import IssueTrackerPort


class PlaneTrackerAdapter(IssueTrackerPort):
    def __init__(
        self,
        *,
        url: str,
        token: str,
        workspace_slug: str,
        project_id: str,
        opener: object | None = None,
    ) -> None:
        self._url = url.rstrip("/")
        self._token = token
        self._workspace_slug = workspace_slug
        self._project_id = project_id
        self._opener = opener if opener is not None else urllib.request.urlopen

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _work_items_url(self) -> str:
        # Plane's work-item routes are workspace-scoped (verified against the
        # API reference): /api/v1/workspaces/{workspace_slug}/projects/
        # {project_id}/work-items/. The field is `name`, per the same docs.
        return (
            f"{self._url}/api/v1/workspaces/{self._workspace_slug}"
            f"/projects/{self._project_id}/work-items/"
        )

    async def create_ticket(self, title: str, description: str) -> str:
        return await asyncio.to_thread(self._create_sync, title, description)

    def _create_sync(self, title: str, description: str) -> str:
        payload = json.dumps({"name": title, "description": description}).encode("utf-8")
        req = urllib.request.Request(  # nosec B310 - https-only endpoints are config
            self._work_items_url(),
            data=payload,
            headers=self._headers(),
            method="POST",
        )
        try:
            with self._opener(req) as resp:  # type: ignore[operator]
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Plane API error {exc.code}: {exc.reason}") from exc
        return str(data["id"])

    async def get_ticket_status(self, ticket_id: str) -> str:
        return await asyncio.to_thread(self._status_sync, ticket_id)

    def _status_sync(self, ticket_id: str) -> str:
        req = urllib.request.Request(  # nosec B310 - https-only endpoints are config
            f"{self._work_items_url()}{ticket_id}/",
            headers=self._headers(),
            method="GET",
        )
        try:
            with self._opener(req) as resp:  # type: ignore[operator]
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise KeyError(f"ticket {ticket_id!r} not found") from exc
            raise RuntimeError(f"Plane API error {exc.code}: {exc.reason}") from exc
        state = data.get("state") or data.get("name") or "unknown"
        if isinstance(state, dict):
            state = state.get("name") or "unknown"
        return str(state)
