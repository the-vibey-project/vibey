import pytest
from pager import get_page, page_count
from summary import describe


@pytest.mark.parametrize(
    ("total", "size", "expected"),
    [
        (0, 10, 0),
        (1, 10, 1),
        (9, 10, 1),
        (10, 10, 1),
        (11, 10, 2),
        (21, 10, 3),
        (22, 10, 3),
        (7, 1, 7),
        (5, 2, 3),
        (1, 1, 1),
    ],
)
def test_page_count(total: int, size: int, expected: int) -> None:
    assert page_count(total, size) == expected


def test_last_page_with_one_item_is_reachable() -> None:
    items = list("abcde")
    assert get_page(items, 3, 2) == ["e"]


def test_every_item_appears_exactly_once() -> None:
    items = list(range(23))
    seen: list[int] = []
    for page in range(1, page_count(len(items), 5) + 1):
        seen.extend(get_page(items, page, 5))
    assert seen == items


def test_page_beyond_the_last_is_rejected() -> None:
    with pytest.raises(IndexError):
        get_page(list(range(11)), 3, 10)


def test_empty_list_has_no_valid_page() -> None:
    with pytest.raises(IndexError):
        get_page([], 1, 10)


def test_full_middle_page() -> None:
    assert get_page(list(range(25)), 2, 10) == list(range(10, 20))


def test_non_positive_size_is_rejected() -> None:
    with pytest.raises(ValueError):
        page_count(5, 0)


def test_describe_uses_the_singular_for_one_page() -> None:
    assert describe(3, 10) == "3 items, 1 page"


def test_describe_counts_a_leftover_item() -> None:
    assert describe(31, 10) == "31 items, 4 pages"
