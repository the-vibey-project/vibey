"""A discovered Candidate carries its provenance, in the intake's own vocabulary.

Provenance is never lost (runbook 21): every source yields candidates with a source link.
Every field is outside text and data (SD-01 §4); an offer is recorded verbatim, never
parsed as a payment instruction (doctrine 10.b).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vibey_explorer.interfaces.candidate_interface import (
        CandidateInterface,
    )

SOURCE_KINDS: tuple[str, ...] = (
    "forge-issue",
    "help-wanted",
    "bounty",
    "proposal",
    "other",
)

_URL_RE = re.compile(r"^https?://\S+$")
_REPO_RE = re.compile(r"^[^/\s]+/[^/\s]+$")


@dataclass(frozen=True, slots=True)
class Candidate:
    """A candidate discovered from an external source, carrying its full provenance."""

    source_url: str
    source_kind: str
    title: str
    asks: str
    offer: str = ""
    repository: str = ""
    found_at: datetime | None = None

    def __post_init__(self) -> None:
        self._validate_source_url(self.source_url)
        self._validate_source_kind(self.source_kind)
        self._validate_title(self.title)
        self._validate_asks(self.asks)
        self._validate_offer(self.offer)
        self._validate_repository(self.repository)
        self._validate_found_at(self.found_at)

    # ------------------------------------------------------------------ validators

    @staticmethod
    def _validate_source_url(url: str) -> None:
        if not _URL_RE.match(url) or re.search(r"\s", url):
            raise ValueError(f"candidate source_url must be an http(s) URL: {url!r}")
        if len(url) > 2048:
            raise ValueError("candidate source_url is longer than 2048 characters")

    @staticmethod
    def _validate_source_kind(kind: str) -> None:
        if kind not in SOURCE_KINDS:
            raise ValueError(
                f"candidate source_kind must be one of {', '.join(SOURCE_KINDS)}: {kind!r}"
            )

    @staticmethod
    def _validate_title(title: str) -> None:
        stripped = title.strip()
        if not stripped:
            raise ValueError("candidate title is empty")
        if len(stripped) > 300:
            raise ValueError("candidate title is longer than 300 characters")

    @staticmethod
    def _validate_asks(asks: str) -> None:
        if len(asks) > 2000:
            raise ValueError("candidate asks is longer than 2000 characters")

    @staticmethod
    def _validate_offer(offer: str) -> None:
        if len(offer) > 500:
            raise ValueError("candidate offer is longer than 500 characters")

    @staticmethod
    def _validate_repository(repository: str) -> None:
        if not repository:
            return
        if not _REPO_RE.match(repository) or " " in repository:
            raise ValueError(
                f"candidate repository must be a forge namespace such as 'owner/name': {repository!r}"
            )

    @staticmethod
    def _validate_found_at(dt: datetime | None) -> None:
        if dt is not None and dt.tzinfo is None:
            raise ValueError("candidate found_at must be timezone-aware")

    # --------------------------------------------------------------- intake bridge

    def intake_arguments(self) -> tuple[str, ...]:
        """Return the exact ``vibey new`` flags that would recreate this candidate."""
        args: list[str] = [
            "--source-url",
            self.source_url,
            "--source-kind",
            self.source_kind,
        ]
        if self.offer:
            args.extend(["--offer", self.offer])
        return tuple(args)


# Conformance: a real instance must satisfy the Protocol.
_CONFORMS: CandidateInterface = Candidate(
    "https://example.org/", "other", "t", "a"
)
