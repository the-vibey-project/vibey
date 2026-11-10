import pytest
from roman import from_roman, to_roman


def test_simple_values():
    assert to_roman(1) == "I"
    assert to_roman(3) == "III"
    assert to_roman(8) == "VIII"
    assert to_roman(3999) == "MMMCMXCIX"


def test_subtractive_forms():
    assert [to_roman(n) for n in (4, 9, 40, 90, 400, 900)] == ["IV", "IX", "XL", "XC", "CD", "CM"]


def test_example():
    assert to_roman(1994) == "MCMXCIV"
    assert to_roman(2024) == "MMXXIV"


@pytest.mark.parametrize("n", [0, -5, 4000, 10000])
def test_to_roman_out_of_range(n):
    with pytest.raises(ValueError):
        to_roman(n)


def test_from_roman_basic():
    assert from_roman("XIV") == 14
    assert from_roman("MCMXCIV") == 1994
    assert from_roman("MMMCMXCIX") == 3999


def test_from_roman_lowercase():
    assert from_roman("mcmxciv") == 1994
    assert from_roman("xiv") == 14


@pytest.mark.parametrize(
    "s", ["IIII", "VX", "IC", "MMMM", "", "ABC", "IIX", "VV", "XM", "IXI", "X I"]
)
def test_from_roman_rejects_non_canonical(s):
    with pytest.raises(ValueError):
        from_roman(s)


def test_round_trip_every_value():
    for n in range(1, 4000):
        assert from_roman(to_roman(n)) == n
