# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Site chrome out, XML-legal markup in -- what a chapter passes through on its way
from the built site into the book.

A rendered documentation page is HTML written for a browser, and a browser forgives
everything. An EPUB reader does not: a chapter is XHTML, an XML parser reads it, and XML
predefines exactly five entities. `&para;` is not one of them -- and `&para;` is what
mkdocs emits inside every `<a class="headerlink">` permalink, once per heading, on every
page. One undefined entity anywhere invalidates the whole package, so the book that was
built and shipped was never openable; the same pilcrows are also visible furniture in a
printed interior where nothing is clickable. Two symptoms, one cause, one fix.

What counts as chrome is configuration rather than policy baked in: a theme that marks
its permalinks with a different class hands its own class names to the constructor
instead of forking this file.
"""

from __future__ import annotations

import html as html_lib
from collections.abc import Iterable, Sequence
from html.entities import html5 as _HTML5_ENTITIES

Attributes = Sequence[tuple[str, str | None]]

#: Elements whose whole subtree is site furniture rather than chapter content.
DEFAULT_CHROME_TAGS: frozenset[str] = frozenset(
    {"script", "style", "nav", "aside", "form", "button"}
)

#: CSS classes marking an element as furniture. `headerlink` is mkdocs' permalink
#: anchor; the rest are what the other generators this family renders with emit.
DEFAULT_CHROME_CLASSES: frozenset[str] = frozenset(
    {"headerlink", "headeranchor", "anchorjs-link", "skip-link", "permalink"}
)

#: The HTML void elements, in full. A bare `<br>` every browser forgives is a hard
#: error on a Kindle, so each of these is re-emitted self-closed.
VOID_TAGS: frozenset[str] = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)

# The only five entity names XML defines without a DTD. Everything else has to be
# resolved to the character it names.
_XML_PREDEFINED: frozenset[str] = frozenset({"amp;", "lt;", "gt;", "quot;", "apos;"})

# The characters XML 1.0 permits at all. A reference to anything else cannot be written
# down legally in any form, so it is dropped rather than smuggled through.
_XML_CHARACTER_RANGES: tuple[tuple[int, int], ...] = (
    (0x9, 0x9),
    (0xA, 0xA),
    (0xD, 0xD),
    (0x20, 0xD7FF),
    (0xE000, 0xFFFD),
    (0x10000, 0x10FFFF),
)


class ChapterSanitizer:
    """Emits one rendered page's content as XHTML an EPUB reader will open."""

    def __init__(
        self,
        *,
        chrome_tags: Iterable[str] = DEFAULT_CHROME_TAGS,
        chrome_classes: Iterable[str] = DEFAULT_CHROME_CLASSES,
        void_tags: Iterable[str] = VOID_TAGS,
    ) -> None:
        self._chrome_tags = frozenset(chrome_tags)
        self._chrome_classes = frozenset(chrome_classes)
        self._void_tags = frozenset(void_tags)

    def is_void(self, tag: str) -> bool:
        return tag in self._void_tags

    def is_chrome(self, tag: str, attrs: Attributes) -> bool:
        if tag in self._chrome_tags:
            return True
        classes = {name for key, value in attrs if key == "class" for name in (value or "").split()}
        return bool(self._chrome_classes & classes)

    def start_tag(self, tag: str, attrs: Attributes, *, self_closing: bool = False) -> str:
        """Rebuilt from the parsed attributes, never copied from the source.

        Copying the source text carries its problems along: entities inside attribute
        values, a value-less boolean attribute, an unquoted value. Rebuilding escapes
        every value exactly once and writes `open` as `open="open"`, which is what
        XHTML requires and what the source will not reliably give.
        """
        rendered = "".join(
            f' {key}="{html_lib.escape(key if value is None else value, quote=True)}"'
            for key, value in attrs
        )
        closer = "/>" if self_closing or self.is_void(tag) else ">"
        return f"<{tag}{rendered}{closer}"

    def end_tag(self, tag: str) -> str:
        return f"</{tag}>"

    def text(self, data: str) -> str:
        return html_lib.escape(data, quote=False)

    def entity_reference(self, name: str) -> str:
        reference = f"{name};"
        if reference in _XML_PREDEFINED:
            return f"&{reference}"
        resolved = _HTML5_ENTITIES.get(reference)
        if resolved is None:
            # Not an entity at all, so it was never markup: an ampersand followed by a
            # word, which XML still refuses to read bare.
            return f"&amp;{name};"
        return self.text(resolved)

    def character_reference(self, name: str) -> str:
        codepoint = int(name[1:], 16) if name[:1].lower() == "x" else int(name)
        if not any(low <= codepoint <= high for low, high in _XML_CHARACTER_RANGES):
            return ""
        return f"&#{codepoint};"
