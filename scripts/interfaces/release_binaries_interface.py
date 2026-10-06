# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts `scripts/release_binaries.py` implements. Interfaces declare; they never consume.

A *catalogue* reads the declared targets: every user interface on every platform, and what
each one is (built, waiting for a credential, or not supported, with the reason). A
*planner* turns the catalogue into the release workflow's matrix for one release. A
*workflow checker* proves the workflow file still builds exactly what the catalogue
declares. A *renderer* writes the catalogue into the downloads page's GENERATED block. A
*PyPI fetcher* fetches the files the package index serves for one version, digest-checked.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol


class TargetCatalogueInterface(Protocol):
    """The declared targets, expanded per architecture, with their versions read."""

    def targets(self) -> Sequence[Any]:
        """Every target, in declaration order, each with its version and asset names."""
        ...

    def builders(self) -> Sequence[str]:
        """The builder of every target that is built or waits for a credential, in order."""
        ...


class MatrixPlannerInterface(Protocol):
    """The release workflow's plan for one run."""

    def plan(self, *, mode: str, target: str, tag: str) -> Mapping[str, Any]:
        """The mode, the commit, the tag, one matrix per builder and the expected assets."""
        ...


class WorkflowCheckerInterface(Protocol):
    """Holds the workflow file to the catalogue, so neither can drift from the other."""

    def problems(self, workflow: Mapping[Any, Any]) -> list[str]:
        """Each way the parsed workflow disagrees with the catalogue; empty when it agrees."""
        ...


class DownloadsRendererInterface(Protocol):
    """Writes the catalogue as the downloads table."""

    def render(self) -> str:
        """The Markdown between the downloads page's GENERATED markers."""
        ...


class HttpFetcherInterface(Protocol):
    """Fetches one URL; the one place this script touches the network."""

    def get(self, url: str) -> bytes:
        """The response body; raises on any HTTP or network failure."""
        ...


class PypiFetcherInterface(Protocol):
    """Fetches the files the index serves for one project version, digest-checked."""

    def fetch(self, project: str, version: str, out: Path) -> list[Path]:
        """Every file of that release, written under `out`; raises when one is missing or
        its SHA-256 differs from the digest the index records."""
        ...


class NightlyScheduleInterface(Protocol):
    """Says whether the rolling nightly prerelease is due a rebuild."""

    def due(self, changed: Sequence[str] | None) -> bool:
        """True when any changed path lies under a declared nightly path, or when there is no
        nightly yet (`changed` is None: nothing to compare against)."""
        ...
