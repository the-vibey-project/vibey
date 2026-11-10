import discounts
import pytest
from discounts import DISCOUNT_RULES, apply_discount
from pricing import price_order


@pytest.mark.parametrize(
    ("code", "subtotal", "count", "expected"),
    [
        ("SAVE10", 4000, 6, 400),
        ("SAVE10", 999, 1, 99),
        ("save10", 1005, 1, 100),
        ("  Save10  ", 2000, 2, 200),
        ("SAVE25", 9999, 3, 0),
        ("SAVE25", 10000, 3, 2500),
        ("SAVE25", 10003, 3, 2500),
        ("BULK", 3000, 4, 0),
        ("BULK", 3000, 5, 500),
        ("BULK", 20000, 14, 1000),
        ("BULK", 300, 10, 300),
        ("FLAT5", 4000, 1, 500),
        ("FLAT5", 320, 1, 320),
        ("FLAT5", 0, 0, 0),
        ("HALFOFF", 3001, 1, 1500),
        ("HALFOFF", 4000, 1, 2000),
        ("HALFOFF", 90000, 1, 2000),
        ("HALFOFF", 1, 1, 0),
        ("NOPE", 4000, 2, 0),
        ("", 4000, 2, 0),
        (None, 4000, 2, 0),
    ],
)
def test_apply_discount_matches_the_old_behaviour(code, subtotal, count, expected):
    assert apply_discount(code, subtotal, count) == expected


def test_registry_holds_exactly_the_five_upper_case_codes():
    assert set(DISCOUNT_RULES) == {"SAVE10", "SAVE25", "BULK", "FLAT5", "HALFOFF"}
    assert DISCOUNT_RULES["SAVE10"](4000, 3) == 400
    assert DISCOUNT_RULES["BULK"](0, 12) == 1000


def test_rules_return_the_uncapped_amount_and_apply_discount_caps_it():
    assert DISCOUNT_RULES["FLAT5"](100, 1) == 500
    assert apply_discount("FLAT5", 100, 1) == 100


@pytest.mark.parametrize(
    ("items", "code", "tax", "expected"),
    [
        (
            [("pen", 250, 4), ("book", 1500, 2)],
            None,
            0,
            {"subtotal": 4000, "discount": 0, "tax": 0, "total": 4000},
        ),
        (
            [("pen", 250, 4), ("book", 1500, 2)],
            "save10",
            10,
            {"subtotal": 4000, "discount": 400, "tax": 360, "total": 3960},
        ),
        ([("x", 333, 3)], "SAVE10", 7, {"subtotal": 999, "discount": 99, "tax": 63, "total": 963}),
        ([("gum", 100, 2)], "FLAT5", 8, {"subtotal": 200, "discount": 200, "tax": 0, "total": 0}),
        (
            [("tv", 40000, 1)],
            " halfoff ",
            5,
            {"subtotal": 40000, "discount": 2000, "tax": 1900, "total": 39900},
        ),
        (
            [("nut", 120, 10)],
            "BULK",
            0,
            {"subtotal": 1200, "discount": 1000, "tax": 0, "total": 200},
        ),
        ([("nut", 120, 4)], "BULK", 0, {"subtotal": 480, "discount": 0, "tax": 0, "total": 480}),
        (
            [("a", 6000, 1), ("b", 4000, 1)],
            "SAVE25",
            20,
            {"subtotal": 10000, "discount": 2500, "tax": 1500, "total": 9000},
        ),
        ([], "SAVE10", 10, {"subtotal": 0, "discount": 0, "tax": 0, "total": 0}),
        ([("a", 100, 1)], "WHAT", 10, {"subtotal": 100, "discount": 0, "tax": 10, "total": 110}),
    ],
)
def test_price_order_is_unchanged(items, code, tax, expected):
    assert price_order(items, code, tax) == expected


def test_price_order_accepts_keywords_and_defaults():
    out = price_order([("a", 1000, 1)], code="FLAT5", tax_rate_pct=10)
    assert out == {"subtotal": 1000, "discount": 500, "tax": 50, "total": 550}
    assert price_order([("a", 1000, 1)])["total"] == 1000


def test_a_new_registry_entry_works_in_price_order(monkeypatch):
    monkeypatch.setitem(DISCOUNT_RULES, "TENOFF", lambda subtotal, count: 1000)
    out = price_order([("a", 5000, 1)], "tenoff", 10)
    assert out == {"subtotal": 5000, "discount": 1000, "tax": 400, "total": 4400}
    assert apply_discount("TENOFF", 600, 1) == 600


def test_removing_a_registry_entry_disables_the_code(monkeypatch):
    monkeypatch.delitem(DISCOUNT_RULES, "FLAT5")
    assert price_order([("a", 1000, 1)], "FLAT5")["discount"] == 0


def test_price_order_does_not_mutate_its_input():
    items = [("a", 100, 2)]
    price_order(items, "SAVE10")
    assert items == [("a", 100, 2)]
    assert discounts.DISCOUNT_RULES is DISCOUNT_RULES
