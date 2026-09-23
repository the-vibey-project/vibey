# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The declared seams of the research-paper exporter."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class PaperErrorInterface(Protocol):
    """The actionable exception surface exposed by the paper exporter."""

    @property
    def args(self) -> tuple[object, ...]: ...


@runtime_checkable
class PaperDocumentInterface(Protocol):
    """The parsed paper document consumed by the LaTeX and DOCX renderers."""

    title: str
    abstract: list[str]
    body: list[str]
    bibliography: list[str]


@runtime_checkable
class PaperProvenanceInterface(Protocol):
    """What a submitted article states about itself: who wrote it, from which revision, when.

    Every field is a fact the renderer places in the byline, the first-page note and the
    provenance paragraph; none is invented by the renderer. Empty strings are omitted.
    """

    author: str
    email: str
    affiliation: str
    author_url: str
    site_url: str
    repository_url: str
    revision: str
    committed_at: str
    committed_unix: int
    rendered_at: str
    rendered_unix: int


@runtime_checkable
class RevisionReaderInterface(Protocol):
    """Reads the identity and commit time of the revision a paper is rendered from."""

    def read(self, revision: str = "HEAD") -> tuple[str, str, int]:
        """The full SHA, its commit time as ISO-8601 UTC, and the same as Unix time."""
        ...


@runtime_checkable
class PaperFigureInterface(Protocol):
    """One figure of the paper as its ```latex fence declares it."""

    label: str
    environment: str
    caption: str
    picture: str
    fence: str
