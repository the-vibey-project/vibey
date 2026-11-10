from moneyfmt import format_money


def test_default():
    assert format_money(123456) == "$1,234.56"


def test_parens_and_euro():
    assert format_money(-123456, "EUR", negative_style="parens") == "(€1,234.56)"


def test_no_symbol_appends_the_code():
    assert format_money(5, symbol=False) == "0.05 USD"


def test_width_pads_on_the_left():
    assert format_money(100, width=8) == "   $1.00"
