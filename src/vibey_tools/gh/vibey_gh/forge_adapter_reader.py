# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A forge reader that uses a forge adapter to walk artifact classes.

This implements `vibey_gh.interfaces.forge_snapshot_interface.ForgeReaderInterface` by
delegating to a `vibey_gh.interfaces.forge_adapter_interface.ForgeAdapterInterface`.
The adapter handles the platform-specific listing and fetching, while the reader
handles the paging and resume logic.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from vibey_gh.forge_snapshot import ForgeClass
from vibey_gh.interfaces.forge_adapter_interface import ForgeAdapterInterface
from vibey_gh.interfaces.forge_snapshot_interface import (
    ForgeRead,
    ForgeReaderInterface,
    Observation,
)

__all__ = ["ForgeAdapterReader"]


def moment(value: str) -> datetime:
    """Read an ISO 8601 moment; one with no offset is taken to be UTC."""
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def stamp(value: datetime) -> str:
    """Write a moment the way forges do: UTC, to the second, `Z`-suffixed."""
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass(frozen=True)
class ForgeAdapterReader(ForgeReaderInterface):
    """Reads a forge's artifact classes through an adapter.

    The adapter provides the raw listings, and the reader implements the walking
    logic (paging, filtering by update time, and high-water marking).
    """

    forge: str
    repository: str
    adapter: ForgeAdapterInterface
    per_page: int = 100

    def read(self, forge_class: str, since: str | None) -> ForgeRead:
        spec = ForgeClass.named(forge_class)

        if spec.name == "review":
            return self._reviews(spec, since)

        # Walk the artifact class using the adapter's list_artifacts verb.
        items: list[dict[str, Any]] = []
        page = 1
        while True:
            # The adapter handles pagination and the `since` filter.
            page_items, problem = self.adapter.list_artifacts(
                forge_class=spec.name,
                since=since,
                page=page,
                limit=self.per_page,
            )
            if problem:
                return ForgeRead(spec.name, spec.native_class, problem=problem)

            if not page_items:
                break

            items.extend(page_items)
            if len(page_items) < self.per_page:
                break
            page += 1

        return self._observed(spec, items)

    def _reviews(self, spec: ForgeClass, since: str | None) -> ForgeRead:
        # Reviews are walked through change requests.
        # 1. Walk change requests filtered by since.
        # Note: we need a way to list change requests via the adapter.
        # We'll use a dummy call to `list_artifacts("change-request", since=since)`
        # to get the IDs of the PRs/MRs to walk.

        pr_read = self.read("change-request", since)
        if pr_read.problem:
            return ForgeRead(
                spec.name,
                spec.native_class,
                problem=f"the change requests these reviews belong to could not be listed: {pr_read.problem}",
            )

        items: list[dict[str, Any]] = []
        for native_id, payload in pr_read.observations:
            number = payload.get("number")
            if not isinstance(number, int):
                continue

            reviews, problem = self.adapter.get_reviews(number)
            if problem:
                # We treat a problem with one PR's reviews as a failure for the whole class.
                return ForgeRead(spec.name, spec.native_class, problem=problem)

            # The adapter returns ForgeReview objects, but the reader needs raw JSON (Observations).
            # We map them back to raw shapes for the snapshot store.
            for rev in reviews:
                items.append(
                    {
                        "id": rev.id,
                        "author": rev.author,
                        "verdict": rev.verdict,
                        "body": rev.body,
                    }
                )

        return self._observed(spec, items, pr_read.high_water)

    @staticmethod
    def _observed(
        spec: ForgeClass, items: Sequence[dict[str, Any]], high_water: str | None = None
    ) -> ForgeRead:
        observations: list[Observation] = []
        for item in items:
            native_id = item.get(spec.id_field)
            if (
                not isinstance(native_id, (int, str))
                or isinstance(native_id, bool)
                or native_id == ""
            ):
                return ForgeRead(
                    spec.name,
                    spec.native_class,
                    problem=f"the forge listed a {spec.native_class} with no `{spec.id_field}`",
                )
            observations.append((str(native_id), item))
        return ForgeRead(spec.name, spec.native_class, tuple(observations), high_water)
