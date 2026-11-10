import dataclasses

import pytest
from library.pagination import Page, paginate
from library.repository import BookRepository


def _repo(count: int) -> BookRepository:
    repo = BookRepository()
    for n in range(1, count + 1):
        repo.add(f"Title {n}", f"Author {n}")
    return repo


def test_first_page_of_a_list() -> None:
    page = paginate(list(range(10)), 1, 4)
    assert page.items == [0, 1, 2, 3]
    assert (page.page, page.page_size, page.total) == (1, 4, 10)
    assert page.total_pages == 3
    assert page.has_next is True
    assert page.has_prev is False


def test_last_partial_page() -> None:
    page = paginate(list(range(10)), 3, 4)
    assert page.items == [8, 9]
    assert page.has_next is False
    assert page.has_prev is True


def test_exact_multiple_has_no_extra_page() -> None:
    page = paginate(list(range(8)), 2, 4)
    assert page.items == [4, 5, 6, 7]
    assert page.total_pages == 2
    assert page.has_next is False


def test_empty_list() -> None:
    page = paginate([], 1, 5)
    assert page.items == []
    assert page.total == 0
    assert page.total_pages == 0
    assert page.has_next is False
    assert page.has_prev is False


def test_page_beyond_the_end_is_empty_not_an_error() -> None:
    page = paginate([1, 2, 3], 9, 2)
    assert page.items == []
    assert page.page == 9
    assert page.total == 3
    assert page.total_pages == 2
    assert page.has_next is False
    assert page.has_prev is True


def test_page_must_be_at_least_one() -> None:
    with pytest.raises(ValueError):
        paginate([1], 0, 5)
    with pytest.raises(ValueError):
        paginate([1], -3, 5)


@pytest.mark.parametrize("size", [0, -1, 101])
def test_page_size_bounds(size: int) -> None:
    with pytest.raises(ValueError):
        paginate([1, 2, 3], 1, size)


def test_page_size_limits_are_inclusive() -> None:
    assert paginate([1], 1, 1).items == [1]
    assert paginate(list(range(150)), 1, 100).total_pages == 2


def test_page_is_a_frozen_dataclass() -> None:
    page = paginate([1], 1, 1)
    assert isinstance(page, Page)
    assert dataclasses.is_dataclass(page)
    with pytest.raises(dataclasses.FrozenInstanceError):
        page.page = 2  # type: ignore[misc]


def test_paginate_does_not_mutate_input() -> None:
    items = [3, 1, 2]
    paginate(items, 1, 2)
    assert items == [3, 1, 2]


def test_repository_page_defaults() -> None:
    page = _repo(25).page()
    assert [book.id for book in page.items] == list(range(1, 11))
    assert page.total == 25
    assert page.total_pages == 3
    assert page.page_size == 10


def test_repository_page_two() -> None:
    page = _repo(25).page(page=3, page_size=10)
    assert [book.id for book in page.items] == [21, 22, 23, 24, 25]
    assert page.has_next is False


def test_repository_page_filters_by_title() -> None:
    repo = BookRepository()
    repo.add("Dune", "Herbert")
    repo.add("Emma", "Austen")
    repo.add("Dune Messiah", "Herbert")
    repo.add("DUNE Children", "Herbert")
    page = repo.page(page=1, page_size=2, title_contains="dune")
    assert [book.title for book in page.items] == ["Dune", "Dune Messiah"]
    assert page.total == 3
    assert page.total_pages == 2
    second = repo.page(page=2, page_size=2, title_contains="dune")
    assert [book.title for book in second.items] == ["DUNE Children"]


def test_repository_page_no_match() -> None:
    page = _repo(3).page(title_contains="zzz")
    assert page.items == []
    assert page.total == 0
    assert page.total_pages == 0


def test_repository_page_propagates_validation() -> None:
    with pytest.raises(ValueError):
        _repo(3).page(page_size=0)


def test_existing_repository_behaviour_is_unchanged() -> None:
    repo = _repo(3)
    assert repo.get(2).title == "Title 2"
    assert [b.id for b in repo.all()] == [1, 2, 3]
    assert [b.id for b in repo.search_title("TITLE 3")] == [3]
    with pytest.raises(KeyError):
        repo.get(99)
