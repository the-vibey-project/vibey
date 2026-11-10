import pytest
from intervals import merge_intervals


def test_example():
    data = [(8, 10), (1, 3), (2, 6), (15, 18), (17, 20)]
    assert merge_intervals(data) == [(1, 6), (8, 10), (15, 20)]


def test_empty_and_single():
    assert merge_intervals([]) == []
    assert merge_intervals([(4, 4)]) == [(4, 4)]


def test_touching_merges():
    assert merge_intervals([(1, 3), (3, 5)]) == [(1, 5)]


def test_adjacent_integers_stay_separate():
    assert merge_intervals([(1, 2), (3, 4)]) == [(1, 2), (3, 4)]


def test_contained_interval():
    assert merge_intervals([(1, 10), (2, 3), (4, 5)]) == [(1, 10)]


def test_duplicates():
    assert merge_intervals([(1, 2), (1, 2), (1, 2)]) == [(1, 2)]


def test_unsorted_chain():
    assert merge_intervals([(5, 7), (1, 2), (2, 5), (9, 9)]) == [(1, 7), (9, 9)]


def test_negative_numbers():
    assert merge_intervals([(-5, -1), (-3, 2), (4, 6)]) == [(-5, 2), (4, 6)]


def test_invalid_interval_raises():
    with pytest.raises(ValueError):
        merge_intervals([(1, 2), (5, 3)])


def test_input_not_modified():
    data = [(5, 6), (1, 5)]
    merge_intervals(data)
    assert data == [(5, 6), (1, 5)]


def test_returns_tuples():
    result = merge_intervals([(1, 2)])
    assert result == [(1, 2)]
    assert all(isinstance(item, tuple) for item in result)
