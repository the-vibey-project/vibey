from booked import covered_length
from intervals import merge


def test_overlapping_ranges_are_merged() -> None:
    assert merge([(1, 4), (3, 6)]) == [(1, 6)]


def test_ranges_that_touch_are_merged() -> None:
    assert merge([(1, 3), (3, 5)]) == [(1, 5)]
    assert covered_length([(1, 3), (3, 5)]) == 4


def test_a_gap_keeps_ranges_apart() -> None:
    assert merge([(1, 2), (4, 5)]) == [(1, 2), (4, 5)]
