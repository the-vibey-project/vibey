from booked import covered_length
from intervals import merge


def test_chain_of_touching_ranges() -> None:
    assert merge([(1, 2), (2, 3), (3, 4)]) == [(1, 4)]


def test_touching_ranges_given_out_of_order() -> None:
    assert merge([(5, 8), (1, 3), (3, 5)]) == [(1, 8)]


def test_touching_after_an_overlap() -> None:
    assert merge([(1, 4), (2, 6), (6, 9)]) == [(1, 9)]


def test_touching_at_zero_and_negative_points() -> None:
    assert merge([(-3, 0), (0, 2)]) == [(-3, 2)]


def test_degenerate_range_touching_a_neighbour() -> None:
    assert merge([(2, 2), (2, 5)]) == [(2, 5)]


def test_contained_range_is_absorbed() -> None:
    assert merge([(1, 10), (2, 3)]) == [(1, 10)]


def test_gap_of_one_stays_separate() -> None:
    assert merge([(1, 2), (3, 4)]) == [(1, 2), (3, 4)]


def test_empty_and_single() -> None:
    assert merge([]) == []
    assert merge([(4, 9)]) == [(4, 9)]


def test_unsorted_disjoint_input_is_sorted() -> None:
    assert merge([(10, 12), (1, 2), (5, 6)]) == [(1, 2), (5, 6), (10, 12)]


def test_input_is_not_modified() -> None:
    data = [(3, 5), (1, 3)]
    merge(data)
    assert data == [(3, 5), (1, 3)]


def test_covered_length_of_touching_ranges() -> None:
    assert covered_length([(0, 2), (2, 5), (7, 9)]) == 7


def test_covered_length_counts_overlap_once() -> None:
    assert covered_length([(0, 5), (3, 8)]) == 8
