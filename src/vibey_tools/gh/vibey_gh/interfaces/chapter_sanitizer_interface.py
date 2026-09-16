# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for turning a rendered documentation page into book-safe markup."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

Attributes = Sequence[tuple[str, str | None]]


@runtime_checkable
class ChapterSanitizerInterface(Protocol):
    """Decides what part of a rendered page is content, and emits it as XHTML.

    Both halves are one judgement. A browser forgives site chrome and HTML's named
    entities; an EPUB reader parses the same bytes as XML and forgives neither.
    """

    def canonical_name(self, name: str) -> str:
        """The XML spelling of a name HTML reported lowercased (SVG's `viewBox`)."""

    def is_void(self, tag: str) -> bool:
        """Whether this element has no end tag and must be emitted self-closed."""

    def is_chrome(self, tag: str, attrs: Attributes) -> bool:
        """Whether this element and its subtree are site furniture, not content."""

    def start_tag(self, tag: str, attrs: Attributes, *, self_closing: bool = False) -> str:
        """The element's start tag, rewritten so an XML parser accepts it."""

    def end_tag(self, tag: str) -> str:
        """The element's end tag."""

    def text(self, data: str) -> str:
        """Character data, escaped for XML."""

    def entity_reference(self, name: str) -> str:
        """A named HTML entity (`name` without its `&` or `;`), made XML-legal."""

    def character_reference(self, name: str) -> str:
        """A numeric character reference, made XML-legal or dropped if it cannot be."""
