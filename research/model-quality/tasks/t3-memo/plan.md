The repository in the current directory has a small memoizing wrapper (memo.py) used by prices.py. One test
fails: tests/test_memo.py::test_different_keyword_values_are_different_calls. Run it with
`python -m pytest -q tests/test_memo.py`.

Symptom: calling a memoized function as f(2, scale=10) and then as f(2, scale=3) returns the first answer
both times, as if the second call had been remembered.

The rule the code is meant to follow: a call is a cache hit only when it has the same positional arguments
and the same keyword arguments with the same values. Keyword arguments given in a different order are the
same call. The hits and misses counters count each call exactly once, and clear() forgets everything,
counters included.

Find the root cause in memo.py and fix it there. Do not edit anything under tests/. Run the whole tests/
folder, then finish.
