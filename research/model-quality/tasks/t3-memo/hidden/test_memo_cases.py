from memo import Memo
from prices import quote


def make() -> tuple[Memo, list[tuple[int, int]]]:
    log: list[tuple[int, int]] = []

    def work(a: int, b: int = 0, *, c: int = 0) -> int:
        log.append((a, b))
        return a * 100 + b * 10 + c

    return Memo(work), log


def test_keyword_value_changes_the_result() -> None:
    f, _ = make()
    assert f(1, c=1) == 101
    assert f(1, c=2) == 102


def test_two_keywords_one_changes() -> None:
    f, log = make()
    assert f(1, b=2, c=3) == 123
    assert f(1, b=2, c=4) == 124
    assert f(1, b=5, c=3) == 153
    assert len(log) == 3


def test_keyword_order_is_irrelevant() -> None:
    f, log = make()
    assert f(1, b=2, c=3) == 123
    assert f(1, c=3, b=2) == 123
    assert len(log) == 1
    assert (f.hits, f.misses) == (1, 1)


def test_positional_arguments_still_distinguish_calls() -> None:
    f, log = make()
    f(1)
    f(2)
    f(1)
    assert log == [(1, 0), (2, 0)]
    assert (f.hits, f.misses) == (1, 2)


def test_repeat_with_same_keywords_hits() -> None:
    f, log = make()
    f(7, c=1)
    f(7, c=1)
    f(7, c=1)
    assert len(log) == 1
    assert (f.hits, f.misses) == (2, 1)


def test_clear_resets_cache_and_counters() -> None:
    f, log = make()
    f(1, c=1)
    f(1, c=1)
    f.clear()
    assert (f.hits, f.misses) == (0, 0)
    f(1, c=1)
    assert len(log) == 2


def test_quote_discount_changes_the_price() -> None:
    quote.clear()
    assert quote("apple", qty=10) == 400
    assert quote("apple", qty=10, discount=25) == 300
    assert quote("apple", qty=2, discount=25) == 60


def test_quote_repeat_is_served_from_the_cache() -> None:
    quote.clear()
    quote("pear", qty=2)
    quote("pear", qty=2)
    assert (quote.hits, quote.misses) == (1, 1)
