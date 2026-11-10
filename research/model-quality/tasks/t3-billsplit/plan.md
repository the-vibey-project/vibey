The repository in the current directory splits a restaurant bill between diners (billsplit.py), with an
optional tip (tip.py). One test fails: tests/test_billsplit.py::test_shares_add_up_to_the_total. Run it
with `python -m pytest -q tests/test_billsplit.py`.

Symptom: splitting 100 cents between 3 people returns [33, 33, 33], so one cent of the bill vanishes. Other
splits are wrong in the other direction: 10 cents between 4 people returns [3, 3, 3, 3], which is two cents
too many.

The rule the code is meant to follow: split_evenly(total_cents, people) returns one whole-cent share per
person; the shares always add up to exactly total_cents, no two shares differ by more than one cent, and
any leftover cents go one each to the first people in the list, so 100 between 3 is [34, 33, 33]. Money is
handled in integer cents, never floats. A people count below 1 raises ValueError.

Find the root cause in billsplit.py and fix it there. Do not edit anything under tests/. Run the whole
tests/ folder, then finish.
