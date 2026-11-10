The repository in the current directory is a tiny pagination helper (pager.py, summary.py). One test fails:
tests/test_pager.py::test_a_single_leftover_item_gets_its_own_page. Run it with
`python -m pytest -q tests/test_pager.py`.

Symptom: with 11 items and a page size of 10, the eleventh item can never be shown. Asking for page 2
raises IndexError, and the summary line says "1 page" when it should say "2 pages".

The rule the code is meant to follow: page_count(total, size) is the number of pages needed so that every
item appears on some page, with at most `size` items per page; zero items need zero pages. get_page(items,
page, size) takes a 1-based page number and raises IndexError for any page outside 1..page_count.

Find the root cause in pager.py and fix it there. Do not edit anything under tests/. Run the whole
tests/ folder, then finish.
