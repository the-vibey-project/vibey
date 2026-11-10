from pricing import price_order

ITEMS = [("pen", 250, 4), ("book", 1500, 2)]  # 1000 + 3000 = 4000


def test_no_code():
    assert price_order(ITEMS) == {"subtotal": 4000, "discount": 0, "tax": 0, "total": 4000}


def test_save10_with_tax():
    out = price_order(ITEMS, "save10", 10)
    assert out == {"subtotal": 4000, "discount": 400, "tax": 360, "total": 3960}


def test_unknown_code_is_ignored():
    assert price_order(ITEMS, "NOPE")["discount"] == 0


def test_flat5_is_capped_at_subtotal():
    assert price_order([("gum", 100, 2)], "FLAT5")["total"] == 0
