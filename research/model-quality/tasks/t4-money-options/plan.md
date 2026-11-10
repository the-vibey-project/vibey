Replace the argument pile in moneyfmt.py with an options object. Behaviour must not change:
format_money must give exactly the strings it gives today, including for amounts that round to
zero, for a "." thousands separator, and for currencies it has no symbol for.

1. Add a frozen dataclass MoneyFormat to moneyfmt.py with the fields, in this order and with these
   defaults: currency="USD", symbol=True, thousands=",", decimals=2, negative_style="minus",
   width=0. MoneyFormat does no validation itself.
2. Add format_amount(amount_cents: int, options: MoneyFormat | None = None) -> str. It does the
   formatting that format_money does today, using a default MoneyFormat() when options is None.
   It raises ValueError for a bad decimals or negative_style exactly as format_money does today.
3. format_money keeps its current name, parameters (positional and keyword) and defaults, and is
   now a thin wrapper that builds a MoneyFormat and calls format_amount.

Keep the existing tests in test_moneyfmt.py passing. Run them with `python -m pytest -q`, and fix
anything until they pass. Then finish.
