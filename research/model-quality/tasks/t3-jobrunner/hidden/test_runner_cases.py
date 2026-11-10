import pytest
from lock import Lock
from runner import process


def collect() -> tuple[list[object], object]:
    seen: list[object] = []
    return seen, seen.append


def test_none_first_handles_nothing_and_frees_the_lock() -> None:
    lock = Lock()
    seen, handler = collect()
    assert process([None, 1, 2], lock, handler) == 0  # type: ignore[arg-type]
    assert seen == []
    assert not lock.held


def test_none_in_the_middle_skips_the_rest() -> None:
    lock = Lock()
    seen, handler = collect()
    assert process(["a", "b", None, "c"], lock, handler) == 2  # type: ignore[arg-type]
    assert seen == ["a", "b"]
    assert not lock.held


def test_empty_batch() -> None:
    lock = Lock()
    seen, handler = collect()
    assert process([], lock, handler) == 0  # type: ignore[arg-type]
    assert not lock.held
    assert lock.acquisitions == 1


def test_handler_error_propagates_and_frees_the_lock() -> None:
    lock = Lock()

    def boom(item: object) -> None:
        if item == 2:
            raise ValueError("bad item")

    with pytest.raises(ValueError, match="bad item"):
        process([1, 2, 3], lock, boom)
    assert not lock.held


def test_lock_can_be_reused_after_an_error() -> None:
    lock = Lock()

    def boom(item: object) -> None:
        raise KeyError(item)

    with pytest.raises(KeyError):
        process([1], lock, boom)
    seen, handler = collect()
    assert process([5, 6], lock, handler) == 2  # type: ignore[arg-type]
    assert lock.acquisitions == 2


def test_repeated_stopped_batches_never_wedge_the_lock() -> None:
    lock = Lock()
    seen, handler = collect()
    for _ in range(3):
        assert process([1, None], lock, handler) == 1  # type: ignore[arg-type]
    assert lock.acquisitions == 3


def test_full_batch_returns_count_and_releases() -> None:
    lock = Lock()
    seen, handler = collect()
    assert process(list(range(5)), lock, handler) == 5  # type: ignore[arg-type]
    assert seen == [0, 1, 2, 3, 4]
    assert not lock.held


def test_a_held_lock_is_refused() -> None:
    lock = Lock()
    lock.acquire()
    seen, handler = collect()
    with pytest.raises(RuntimeError):
        process([1], lock, handler)  # type: ignore[arg-type]
    assert lock.held
