from lock import Lock
from runner import process


def test_a_full_batch_is_handled() -> None:
    lock = Lock()
    seen: list[int] = []
    assert process([1, 2, 3], lock, seen.append) == 3
    assert seen == [1, 2, 3]
    assert not lock.held


def test_the_lock_is_free_after_a_stopped_batch() -> None:
    lock = Lock()
    seen: list[int] = []
    assert process([1, None, 3], lock, seen.append) == 1
    assert seen == [1]
    assert not lock.held
    assert process([4], lock, seen.append) == 1
