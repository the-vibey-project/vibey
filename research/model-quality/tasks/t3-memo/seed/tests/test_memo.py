from memo import Memo


def test_same_call_is_a_hit() -> None:
    calls: list[int] = []

    def square(x: int) -> int:
        calls.append(x)
        return x * x

    f = Memo(square)
    assert f(3) == 9
    assert f(3) == 9
    assert calls == [3]
    assert (f.hits, f.misses) == (1, 1)


def test_different_keyword_values_are_different_calls() -> None:
    f = Memo(lambda x, scale=1: x * scale)
    assert f(2, scale=10) == 20
    assert f(2, scale=3) == 6
