# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`UntrustedText`: one rule for every piece of hub text an ACP client renders (SP-ACP).

Module-level test functions rather than a class with an interface beside it (ADR-0016)."""

import pytest

from vibey.domain.acp.interfaces.untrusted_text_interface import UntrustedTextInterface
from vibey.domain.acp.untrusted_text import UNTRUSTED_TEXT, UntrustedText

TEXT = UntrustedText()


def test_the_helper_satisfies_its_interface() -> None:
    assert isinstance(UNTRUSTED_TEXT, UntrustedTextInterface)


@pytest.mark.parametrize(
    ("raw", "shown"),
    [
        ("    indented code", "indented code"),  # no indented code block
        ("- a list item", "\\- a list item"),
        ("+ another", "\\+ another"),
        ("=====", "\\====="),  # no setext underline
        ("12. ordered", "12\\. ordered"),
        ("3) ordered", "3\\) ordered"),
        ("> quote", "\\> quote"),
        ("# heading", "\\# heading"),
        ("plain words", "plain words"),
        ("-x is not a list but stays escaped", "\\-x is not a list but stays escaped"),
    ],
)
def test_a_line_is_safe_at_the_start_of_a_line(raw: str, shown: str) -> None:
    # Review 2, O3: nothing a caller puts first can make a list, a quote, a heading or code.
    assert TEXT.line(raw, limit=400) == shown


def test_a_block_keeps_its_lines_as_hard_breaks_and_paragraphs() -> None:
    shown = TEXT.block("1. [approval] Ship?\n  - details\n\nnext", limit=400)

    assert shown == "1\\. \\[approval\\] Ship?\\\n\\- details\n\nnext"


def test_a_block_cannot_define_a_link_reference() -> None:
    # A gate prompt quoted in the hub's reply could add `[build]: https://...`, which would turn
    # every later `[build]` in the client's message into a link.
    shown = TEXT.block("Ship it?\n   [build]: https://evil.example/x", limit=400)

    assert shown == "Ship it?\\\n\\[build\\]: https\\[:\\]//evil.example/x"


def test_a_block_is_cut_to_its_limit() -> None:
    shown = TEXT.block("a" * 30 + "\n" + "b" * 30, limit=40)

    assert shown == "a" * 30 + "\\\n" + "b" * 6 + "..."  # the line break counts too


def test_a_block_has_no_control_or_bidi_characters() -> None:
    shown = TEXT.block("ok\u202erev\x1b[2J\nnext\u2028line", limit=400)

    assert all(ch.isprintable() or ch == "\n" for ch in shown)
    # A line separator is a line break in a block (kept as a hard break); everything else
    # non-printable is a space.
    assert shown == "ok rev \\[2J\\\nnext\\\nline"


@pytest.mark.parametrize(
    ("raw", "fence"),
    [
        ('{"a": 1}', "```"),
        ('{"a": "``` closes?"}', "````"),
        ('{"a": "`````"}', "``````"),
    ],
)
def test_code_is_fenced_longer_than_any_backtick_run_inside(raw: str, fence: str) -> None:
    assert TEXT.code(raw, limit=400) == f"{fence}\n{raw}\n{fence}"


def test_code_keeps_indentation_and_markdown_as_written() -> None:
    raw = '{\n  "link": "[x](https://e.example)",\n  "head": "# h"\n}'

    assert TEXT.code(raw, limit=400) == f"```\n{raw}\n```"


def test_code_is_cut_and_has_no_control_characters() -> None:
    assert (
        TEXT.code("ab\x1bcd\u202eef" * 10, limit=10) == "```\nab cd e...\n```"
    )  # 7 characters, then "..."


def test_escape_defangs_and_escapes_without_cutting() -> None:
    assert TEXT.escape("www.e.x [a]_b") == "www\\[.\\]e.x \\[a\\]\\_b"


def test_one_line_reads_none_as_a_question_mark() -> None:
    assert TEXT.one_line(None) == "?" and TEXT.one_line("a\nb") == "a b"
