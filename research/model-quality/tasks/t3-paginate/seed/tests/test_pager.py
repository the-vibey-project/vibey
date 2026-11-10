import pytest
from pager import get_page, page_count
from summary import describe


def test_exact_multiple_of_the_page_size() -> None:
    assert page_count(20, 10) == 2


def test_a_single_leftover_item_gets_its_own_page() -> None:
    items = list(range(11))
    assert page_count(11, 10) == 2
    assert get_page(items, 2, 10) == [10]
    assert describe(11, 10) == "11 items, 2 pages"


def test_page_zero_is_rejected() -> None:
    with pytest.raises(IndexError):
        get_page([1, 2, 3], 0, 2)
