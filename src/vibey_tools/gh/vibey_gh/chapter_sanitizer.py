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
import re
from collections.abc import Iterable, Sequence
from html.entities import html5 as _HTML5_ENTITIES

Attributes = Sequence[tuple[str, str | None]]

#: Elements whose whole subtree is site furniture rather than chapter content.
DEFAULT_CHROME_TAGS: frozenset[str] = frozenset(
    {"script", "style", "nav", "aside", "form", "button"}
)

#: CSS classes marking an element as furniture. `headerlink` is mkdocs' permalink
#: anchor; the rest are what the other generators this family renders with emit.
#: `permalink` is deliberately absent. It is an ordinary English word a page may carry on
#: genuine content, and a default that silently drops a whole subtree is worse than the
#: pilcrow it would have removed -- the pilcrow now resolves to a character either way,
#: so validity never depended on it and only the cosmetics are at stake. A theme that
#: really does mark its permalinks that way hands the class to the constructor.
DEFAULT_CHROME_CLASSES: frozenset[str] = frozenset(
    {"headerlink", "headeranchor", "anchorjs-link", "skip-link"}
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

#: Names HTML parses case-insensitively and lowercases, but XML reads literally. These
#: are the SVG (and MathML) camelCase element and attribute names from the HTML parsing
#: specification's foreign-content adjustment tables: `viewBox` lowercased to `viewbox`
#: is an attribute an SVG renderer does not know, so an inline diagram scales wrong or
#: disappears. Overridable like every other set here (ADR-0018) -- a generator emitting
#: some other case-sensitive vocabulary declares it rather than forking this file.
_CASE_SENSITIVE_NAME_SOURCE = """
altGlyph altGlyphDef altGlyphItem animateColor animateMotion animateTransform clipPath
feBlend feColorMatrix feComponentTransfer feComposite feConvolveMatrix feDiffuseLighting
feDisplacementMap feDistantLight feFlood feFuncA feFuncB feFuncG feFuncR feGaussianBlur
feImage feMerge feMergeNode feMorphology feOffset fePointLight feSpecularLighting
feSpotLight feTile feTurbulence foreignObject glyphRef linearGradient radialGradient
textPath attributeName attributeType baseFrequency baseProfile calcMode clipPathUnits
diffuseConstant edgeMode filterUnits gradientTransform gradientUnits kernelMatrix
kernelUnitLength keyPoints keySplines keyTimes lengthAdjust limitingConeAngle
markerHeight markerUnits markerWidth maskContentUnits maskUnits numOctaves pathLength
patternContentUnits patternTransform patternUnits pointsAtX pointsAtY pointsAtZ
preserveAlpha preserveAspectRatio primitiveUnits refX refY repeatCount repeatDur
requiredExtensions requiredFeatures specularConstant specularExponent spreadMethod
startOffset stdDeviation stitchTiles surfaceScale systemLanguage tableValues targetX
targetY textLength viewBox viewTarget xChannelSelector yChannelSelector zoomAndPan
"""

DEFAULT_CASE_SENSITIVE_NAMES: frozenset[str] = frozenset(_CASE_SENSITIVE_NAME_SOURCE.split())

# An attribute name XML will read: an XML Name, minus the colon. A colon makes a
# namespace prefix, and a chapter is a fragment inside an XHTML document that declares no
# prefix, so `xlink:href` is an unbound-prefix error rather than a stray attribute --
# dropping the attribute costs a link, keeping it costs the whole package. A duplicated
# name is the same class of fatal error, so only the first occurrence is written.
_XML_ATTRIBUTE_NAME = re.compile(r"[A-Za-z_][\w.-]*\Z")

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


def _is_xml_character(codepoint: int) -> bool:
    return any(low <= codepoint <= high for low, high in _XML_CHARACTER_RANGES)


def _without_forbidden_characters(data: str) -> str:
    """Drop the code points XML 1.0 cannot carry in any form.

    Not escapable and not representable as a reference either -- `&#0;` is as illegal as
    a literal NUL -- so removal is the only thing that leaves a parseable document. Fast
    path first because chapter text almost never contains one.
    """
    if all(_is_xml_character(ord(character)) for character in data):
        return data
    return "".join(c for c in data if _is_xml_character(ord(c)))


class ChapterSanitizer:
    """Emits one rendered page's content as XHTML an EPUB reader will open."""

    def __init__(
        self,
        *,
        chrome_tags: Iterable[str] = DEFAULT_CHROME_TAGS,
        chrome_classes: Iterable[str] = DEFAULT_CHROME_CLASSES,
        void_tags: Iterable[str] = VOID_TAGS,
        case_sensitive_names: Iterable[str] = DEFAULT_CASE_SENSITIVE_NAMES,
    ) -> None:
        self._chrome_tags = frozenset(chrome_tags)
        self._chrome_classes = frozenset(chrome_classes)
        self._void_tags = frozenset(void_tags)
        self._case_sensitive_names = {name.lower(): name for name in case_sensitive_names}

    def canonical_name(self, name: str) -> str:
        """The spelling XML needs for a name HTML handed over lowercased.

        HTML parsing is case-insensitive and `html.parser` reports every tag and
        attribute name folded down; XML is not, and SVG's vocabulary is camelCase.
        Anything outside the table is returned untouched.
        """
        return self._case_sensitive_names.get(name.lower(), name)

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

        What rebuilding costs is the source's casing, which `html.parser` has already
        folded away -- so the case-sensitive table puts `viewBox` back, on the tag name
        and on every attribute name, and `end_tag` applies the same table so the two
        halves always agree. A name XML cannot read, and a name written twice, are both
        dropped rather than handed to a parser that would reject the whole package.
        """
        written: dict[str, str] = {}
        for key, value in attrs:
            name = self.canonical_name(key)
            if name in written or not _XML_ATTRIBUTE_NAME.fullmatch(name):
                continue
            written[name] = name if value is None else value
        if tag == "svg" and "xmlns" not in written:
            written["xmlns"] = "http://www.w3.org/2000/svg"
        rendered = "".join(
            f' {name}="{html_lib.escape(value, quote=True)}"' for name, value in written.items()
        )
        closer = "/>" if self_closing or self.is_void(tag) else ">"
        return f"<{self.canonical_name(tag)}{rendered}{closer}"

    def end_tag(self, tag: str) -> str:
        return f"</{self.canonical_name(tag)}>"

    def text(self, data: str) -> str:
        # Escaping handles the three characters that are MARKUP; it does nothing about
        # the ones XML forbids outright. `character_reference` already drops a numeric
        # reference to U+0000 or U+000C, but a LITERAL one sitting in the built HTML
        # reached the output untouched and made `ET.fromstring` reject the chapter --
        # and with it the package. Same predicate, applied to character data.
        return html_lib.escape(_without_forbidden_characters(data), quote=False)

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
        if not _is_xml_character(codepoint):
            return ""
        return f"&#{codepoint};"
