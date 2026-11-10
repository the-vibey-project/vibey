import pytest
from billsplit import split_evenly
from tip import add_tip, split_with_tip


def test_leftover_goes_to_the_first_people() -> None:
    assert split_evenly(10, 4) == [3, 3, 2, 2]


def test_two_people_odd_total() -> None:
    assert split_evenly(7, 2) == [4, 3]


def test_more_people_than_cents() -> None:
    assert split_evenly(3, 5) == [1, 1, 1, 0, 0]


def test_zero_total() -> None:
    assert split_evenly(0, 3) == [0, 0, 0]


def test_single_person_pays_everything() -> None:
    assert split_evenly(1234, 1) == [1234]


def test_large_even_split_is_exact() -> None:
    assert sum(split_evenly(10**15 + 3, 7)) == 10**15 + 3


@pytest.mark.parametrize(
    ("total", "people"), [(100, 3), (999, 7), (1, 2), (5000, 6), (101, 100), (58, 9)]
)
def test_shares_sum_and_spread(total: int, people: int) -> None:
    shares = split_evenly(total, people)
    assert len(shares) == people
    assert sum(shares) == total
    assert max(shares) - min(shares) <= 1
    assert shares == sorted(shares, reverse=True)


def test_negative_people_rejected() -> None:
    with pytest.raises(ValueError):
        split_evenly(100, -2)


def test_add_tip_rounds_half_up() -> None:
    assert add_tip(1000, 18) == 1180
    assert add_tip(250, 10) == 275
    assert add_tip(5, 10) == 6


def test_split_with_tip_adds_up() -> None:
    shares = split_with_tip(1000, 3, 15)
    assert sum(shares) == add_tip(1000, 15) == 1150
    assert shares == [384, 383, 383]
