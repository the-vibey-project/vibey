The repository in the current directory merges booked time ranges (intervals.py) and totals them
(booked.py). One test fails: tests/test_intervals.py::test_ranges_that_touch_are_merged. Run it with
`python -m pytest -q tests/test_intervals.py`.

Symptom: merging (1, 3) and (3, 5) leaves two separate ranges, although they share the point 3, and the
covered total for such ranges is reported wrongly.

The rule the code is meant to follow: a range is a pair (start, end) with start <= end. Two ranges are
merged into one when they overlap or share an endpoint; ranges with a real gap between them stay separate.
The result is sorted by start, and the input list is never modified. covered_length is the sum of
(end - start) over the merged result.

Find the root cause in intervals.py and fix it there. Do not edit anything under tests/. Run the whole
tests/ folder, then finish.
