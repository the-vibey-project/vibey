import pytest
from rle import decode, encode


def test_encode_example():
    assert encode("aaabccdddd") == "3a1b2c4d"


def test_encode_single_and_empty():
    assert encode("") == ""
    assert encode("z") == "1z"
    assert encode("abc") == "1a1b1c"


def test_encode_long_run():
    assert encode("x" * 12) == "12x"
    assert encode("y" * 100 + "z") == "100y1z"


def test_encode_spaces_and_punctuation():
    assert encode("  !!") == "2 2!"


def test_encode_rejects_digits():
    with pytest.raises(ValueError):
        encode("a1b")


def test_decode_basic():
    assert decode("3a1b2c4d") == "aaabccdddd"
    assert decode("") == ""


def test_decode_multi_digit():
    assert decode("12x") == "x" * 12
    assert decode("10a2b") == "a" * 10 + "bb"


def test_decode_space_char():
    assert decode("2 1!") == "  !"


@pytest.mark.parametrize("data", ["3a2", "a3b", "3", "01a", "0a", "5"])
def test_decode_malformed(data):
    with pytest.raises(ValueError):
        decode(data)


def test_round_trip():
    for text in ["", "a", "aab", "hello world", "zzzzzzzzzzzzzzzz!!", "ab" * 7]:
        assert decode(encode(text)) == text
