# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Text from the open web, made safe to print: no escape sequence, control or format character
survives, and words, tabs and newlines are left as they were."""

import pytest

from vibey.infrastructure.web.interfaces import UntrustedTextInterface
from vibey.infrastructure.web.untrusted_text import UntrustedText


def test_the_class_honours_its_interface() -> None:
    assert isinstance(UntrustedText(), UntrustedTextInterface)


@pytest.mark.parametrize(
    ("dirty", "clean"),
    [
        ("copy\x1b]52;c;ZXZpbA==\x07me", "copyme"),  # OSC 52, BEL-terminated: clipboard write
        ("a\x1b]0;title\x1b\\b", "ab"),  # OSC, ST-terminated: window title
        ("a\x1b]8;;https://evil\x1b\\link\x1b]8;;\x1b\\b", "alinkb"),  # hidden hyperlink
        ("a\x1b[2Jb\x1b[31;1mc", "abc"),  # CSI: clear screen, colour
        ("a\x9b2Jb", "ab"),  # 8-bit CSI
        ("a\x9d0;t\x9cb", "ab"),  # 8-bit OSC with 8-bit ST
        ("a\x1bPq#0\x1b\\b", "ab"),  # DCS
        ("a\x1b(Bb\x1bc", "ab"),  # charset switch, full reset
        ("a\x1b", "a"),  # a lone escape
        ("a\x00b\x07c\x7fd\x85e", "abcde"),  # NUL, BEL, DEL, NEL (C1)
        ("abc‮def​", "abcdef"),  # bidirectional override, zero-width space
        ("tab\there\nnewline", "tab\there\nnewline"),
        ("plain words, café, 日本語", "plain words, café, 日本語"),
    ],
)
def test_terminal_control_is_removed_and_words_are_kept(dirty: str, clean: str) -> None:
    assert UntrustedText.clean(dirty) == clean


@pytest.mark.parametrize(
    ("url", "clean"),
    [
        ("https://a.example/path?q=1", True),
        ("https://a.example/\x1b]8;;x\x07", False),
        ("https://a.example/a b", False),
        ("https://a.example/‮", False),
        ("https://a.example/\n", False),
    ],
)
def test_a_url_is_clean_only_with_no_control_format_or_space(url: str, clean: bool) -> None:
    assert UntrustedText.is_clean_url(url) is clean
