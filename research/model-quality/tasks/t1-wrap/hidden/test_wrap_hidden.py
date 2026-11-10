import pytest
from wrap import wrap_text


def test_example():
    assert wrap_text("the quick brown fox", 9) == ["the quick", "brown fox"]


def test_empty_and_whitespace():
    assert wrap_text("", 10) == []
    assert wrap_text("  \n\t ", 10) == []


def test_invalid_width():
    with pytest.raises(ValueError):
        wrap_text("hello", 0)
    with pytest.raises(ValueError):
        wrap_text("hello", -3)


def test_whitespace_collapsed():
    assert wrap_text("  a   b\n\nc\td  ", 20) == ["a b c d"]


def test_exact_fit():
    assert wrap_text("abc def", 7) == ["abc def"]
    assert wrap_text("abc def", 6) == ["abc", "def"]


def test_long_word_split():
    assert wrap_text("abcdefgh", 3) == ["abc", "def", "gh"]
    assert wrap_text("abcdef", 3) == ["abc", "def"]


def test_long_word_starts_new_line():
    assert wrap_text("a abcdefgh bc", 5) == ["a", "abcde", "fgh", "bc"]


def test_last_chunk_takes_following_words():
    assert wrap_text("a abcdefgh bc", 6) == ["a", "abcdef", "gh bc"]


def test_width_one():
    assert wrap_text("ab c", 1) == ["a", "b", "c"]


def test_no_trailing_spaces():
    for line in wrap_text("one two three four five six seven", 8):
        assert line == line.strip()
        assert len(line) <= 8


def test_greedy_many_words():
    text = "the rain in spain stays mainly in the plain"
    assert wrap_text(text, 12) == ["the rain in", "spain stays", "mainly in", "the plain"]
