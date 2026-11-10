import dataclasses

import pytest
from moneyfmt import MoneyFormat, format_amount, format_money


def test_money_format_defaults_and_field_order():
    fields = [(f.name, f.default) for f in dataclasses.fields(MoneyFormat)]
    assert fields == [
        ("currency", "USD"),
        ("symbol", True),
        ("thousands", ","),
        ("decimals", 2),
        ("negative_style", "minus"),
        ("width", 0),
    ]


def test_money_format_is_frozen_and_comparable():
    a = MoneyFormat(currency="EUR")
    assert a == MoneyFormat("EUR")
    assert a != MoneyFormat()
    with pytest.raises(dataclasses.FrozenInstanceError):
        a.width = 3  # type: ignore[misc]


def test_money_format_does_not_validate_on_construction():
    bad = MoneyFormat(decimals=7, negative_style="weird")
    assert bad.decimals == 7
    with pytest.raises(ValueError):
        format_amount(100, bad)


def test_format_amount_default_options():
    assert format_amount(123456) == "$1,234.56"
    assert format_amount(123456, None) == "$1,234.56"
    assert format_amount(123456, MoneyFormat()) == "$1,234.56"
    assert format_amount(0) == "$0.00"


@pytest.mark.parametrize(
    ("amount", "options", "expected"),
    [
        (-123456, MoneyFormat("EUR", negative_style="parens"), "(€1,234.56)"),
        (-4, MoneyFormat(decimals=0), "-$0"),
        (4, MoneyFormat(decimals=0), "$0"),
        (-4, MoneyFormat(decimals=0, negative_style="parens"), "($0)"),
        (50, MoneyFormat(decimals=0), "$1"),
        (-250, MoneyFormat(decimals=0), "-$3"),
        (149, MoneyFormat(decimals=1), "$1.5"),
        (155, MoneyFormat(decimals=1), "$1.6"),
        (99999, MoneyFormat(decimals=1), "$1,000.0"),
        (999999, MoneyFormat(decimals=0), "$10,000"),
        (123456789, MoneyFormat("EUR", thousands="."), "€1.234.567,89"),
        (123456789, MoneyFormat("gbp", symbol=False, thousands="."), "1.234.567,89 GBP"),
        (123456789, MoneyFormat("JPY"), "JPY 1,234,567.89"),
        (123456789, MoneyFormat("jpy", symbol=False, thousands=""), "1234567.89 JPY"),
        (5, MoneyFormat(thousands=""), "$0.05"),
        (-5, MoneyFormat("usd", negative_style="parens", width=12), "     ($0.05)"),
        (100000, MoneyFormat(thousands=" ", decimals=0), "$1 000"),
        (-1, MoneyFormat(width=6), "-$0.01"),
        (12345678, MoneyFormat("CHF", False, ",", 0, "parens", 15), "    123,457 CHF"),
        (100, MoneyFormat(width=3), "$1.00"),
    ],
)
def test_format_amount_matches_the_old_output(amount, options, expected):
    assert format_amount(amount, options) == expected


@pytest.mark.parametrize("decimals", [-1, 3, 5])
def test_bad_decimals_raise_value_error(decimals):
    with pytest.raises(ValueError):
        format_amount(1, MoneyFormat(decimals=decimals))
    with pytest.raises(ValueError):
        format_money(1, decimals=decimals)


@pytest.mark.parametrize("style", ["", "paren", "MINUS"])
def test_bad_negative_style_raises_even_for_positive_amounts(style):
    with pytest.raises(ValueError):
        format_amount(1, MoneyFormat(negative_style=style))
    with pytest.raises(ValueError):
        format_money(1, negative_style=style)


def test_format_money_still_takes_the_seven_arguments_positionally():
    assert format_money(12345678, "CHF", False, ",", 0, "parens", 15) == "    123,457 CHF"
    assert format_money(-123456, "EUR", True, ".", 2, "parens", 14) == "(€1.234,56)".rjust(14)


def test_format_money_keywords_and_defaults():
    assert format_money(123456) == "$1,234.56"
    assert format_money(5, symbol=False) == "0.05 USD"
    assert format_money(100, width=8) == "   $1.00"
    assert format_money(-5, currency="usd", negative_style="parens", width=12) == "     ($0.05)"
    assert format_money(-4, decimals=0) == "-$0"
    assert format_money(123456789, thousands=".") == "$1.234.567,89"


def test_format_money_agrees_with_format_amount():
    options = MoneyFormat("GBP", True, ",", 1, "parens", 11)
    assert format_money(-987654, "GBP", True, ",", 1, "parens", 11) == format_amount(
        -987654, options
    )
