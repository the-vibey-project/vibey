import pytest
from billsplit import split_evenly


def test_even_split() -> None:
    assert split_evenly(90, 3) == [30, 30, 30]


def test_shares_add_up_to_the_total() -> None:
    assert split_evenly(100, 3) == [34, 33, 33]


def test_zero_people_is_rejected() -> None:
    with pytest.raises(ValueError):
        split_evenly(100, 0)
