# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The chapter sanitizer: what counts as site chrome, and what XML will accept (#162).

The contract is XML's, not ours. A chapter that a browser renders perfectly is still an
invalid EPUB if one named entity in it is undefined, and `&para;` -- mkdocs' permalink
pilcrow -- is undefined in XHTML. Every assertion here is about output an XML parser
will read.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from vibey_gh.chapter_sanitizer import ChapterSanitizer


def test_chrome_is_the_listed_tags_and_the_listed_classes():
    s = ChapterSanitizer()
    assert s.is_chrome("nav", [])
    assert s.is_chrome("a", [("class", "headerlink"), ("href", "#x")])
    # a class list, not a class string: mkdocs writes more than one.
    assert s.is_chrome("a", [("class", "toclink headerlink")])
    assert not s.is_chrome("p", [("id", "x")])
    assert not s.is_chrome("p", [("class", "admonition")])
    # a value-less class attribute is not a match, and is not a crash either
    assert not s.is_chrome("p", [("class", None)])


def test_chrome_is_configuration_not_policy():
    """A theme that marks permalinks differently configures this; it does not fork it."""
    s = ChapterSanitizer(chrome_tags=frozenset({"footer"}), chrome_classes=frozenset({"pilcrow"}))
    assert s.is_chrome("footer", []) and s.is_chrome("span", [("class", "pilcrow")])
    assert not s.is_chrome("nav", []) and not s.is_chrome("a", [("class", "headerlink")])


def test_start_tags_are_rebuilt_so_xhtml_accepts_them():
    s = ChapterSanitizer()
    assert s.start_tag("p", []) == "<p>"
    # a value-less boolean attribute is illegal in XHTML; `open` becomes open="open"
    assert s.start_tag("details", [("class", "note"), ("open", None)]) == (
        '<details class="note" open="open">'
    )
    # an attribute value is escaped exactly once, whatever it arrived carrying
    assert s.start_tag("a", [("href", 'a&b"c<d')]) == '<a href="a&amp;b&quot;c&lt;d">'
    assert s.start_tag("br", []) == "<br/>"
    assert s.start_tag("img", [("src", "x")], self_closing=True) == '<img src="x"/>'
    assert s.start_tag("span", [], self_closing=True) == "<span/>"
    assert s.end_tag("p") == "</p>" and s.is_void("hr") and not s.is_void("p")


def test_character_data_is_escaped_for_xml():
    assert ChapterSanitizer().text("a & b < c > d") == "a &amp; b &lt; c &gt; d"


def test_named_entities_become_something_xml_defines():
    s = ChapterSanitizer()
    # the five XML predefines survive untouched
    assert s.entity_reference("amp") == "&amp;"
    assert s.entity_reference("lt") == "&lt;"
    # everything else resolves to the character it names -- `&para;` is the whole bug
    assert s.entity_reference("para") == "¶"
    assert s.entity_reference("rarr") == "→"
    # a resolved character that is itself markup is escaped on the way out
    assert s.entity_reference("LT") == "&lt;"
    # an ampersand followed by a word was never markup, and XML still refuses it bare
    assert s.entity_reference("notanentity") == "&amp;notanentity;"


def test_numeric_references_survive_unless_xml_forbids_the_character():
    s = ChapterSanitizer()
    assert s.character_reference("8594") == "&#8594;"
    assert s.character_reference("x2192") == "&#8594;"
    assert s.character_reference("X2192") == "&#8594;"
    # a form feed is not a character XML 1.0 has any legal spelling for, so it goes
    assert s.character_reference("12") == ""
    assert s.character_reference("99999999") == ""


def test_the_pieces_compose_into_something_an_xml_parser_reads():
    s = ChapterSanitizer()
    chapter = (
        s.start_tag("p", [("class", "x")])
        + s.text("caf & bar ")
        + s.entity_reference("para")
        + s.character_reference("8594")
        + s.start_tag("br", [])
        + s.end_tag("p")
    )
    assert ET.fromstring(chapter) is not None
