Refactor the promo-code handling in pricing.py. Behaviour must not change: every existing call to
price_order must return exactly what it returns today, including for edge cases.

1. Create discounts.py, a new module, containing:
   - DISCOUNT_RULES: a dict mapping each upper-case promo code to a rule function. A rule takes
     (subtotal_cents: int, item_count: int) and returns the discount in cents.
   - apply_discount(code: str | None, subtotal_cents: int, item_count: int) -> int, which returns
     the discount in cents for a code (0 for None or an unknown code). It finds the rule by looking
     the code up in DISCOUNT_RULES, and it is the only place that caps a discount at the subtotal.
2. Replace the if/elif chain in price_order (pricing.py) with a call to apply_discount. Adding a
   new entry to DISCOUNT_RULES must be enough to make that code work in price_order.
3. price_order keeps its name, signature and return value, and stays in pricing.py.

Keep the existing tests in test_pricing.py passing. Run them with `python -m pytest -q`, and fix
anything until they pass. Then finish.
