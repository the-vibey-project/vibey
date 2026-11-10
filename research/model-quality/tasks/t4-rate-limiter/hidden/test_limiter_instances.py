import limiter
import pytest
from limiter import DEFAULT_LIMITER, RateLimiter


@pytest.fixture(autouse=True)
def _fresh_default():
    DEFAULT_LIMITER.configure(3, 60)
    DEFAULT_LIMITER.reset()
    yield
    DEFAULT_LIMITER.configure(3, 60)
    DEFAULT_LIMITER.reset()


def test_defaults_are_three_per_sixty_seconds():
    rl = RateLimiter()
    assert [rl.allow("k", t) for t in (0, 1, 2, 3)] == [True, True, True, False]
    assert rl.allow("k", 60) is True  # the hit at 0 is exactly 60 old: expired


def test_window_boundary_is_exclusive():
    rl = RateLimiter(1, 10)
    assert rl.allow("k", 100) is True
    assert rl.allow("k", 109.5) is False
    assert rl.allow("k", 110) is True


def test_rejected_hits_are_not_recorded():
    rl = RateLimiter(2, 10)
    assert rl.allow("k", 0) and rl.allow("k", 1)
    assert [rl.allow("k", t) for t in (2, 3, 4, 5)] == [False] * 4
    # Only the hits at 0 and 1 count, so at 10.5 one slot has freed up, then it is full again.
    assert rl.allow("k", 10.5) is True
    assert rl.allow("k", 10.6) is False


def test_remaining_counts_down_and_never_goes_negative():
    rl = RateLimiter(2, 10)
    assert rl.remaining("k", 0) == 2
    rl.allow("k", 0)
    assert rl.remaining("k", 1) == 1
    rl.allow("k", 1)
    assert rl.remaining("k", 2) == 0
    rl.allow("k", 2)
    assert rl.remaining("k", 3) == 0
    assert rl.remaining("k", 10) == 1
    assert rl.remaining("never-seen", 0) == 2


def test_remaining_does_not_consume():
    rl = RateLimiter(1, 10)
    for _ in range(5):
        assert rl.remaining("k", 0) == 1
    assert rl.allow("k", 0) is True


def test_instances_do_not_share_hits():
    a, b = RateLimiter(1, 10), RateLimiter(1, 10)
    assert a.allow("k", 0) is True
    assert a.allow("k", 1) is False
    assert b.allow("k", 1) is True


def test_instances_do_not_share_settings():
    a, b = RateLimiter(1, 10), RateLimiter(5, 100)
    a.configure(2, 20)
    assert [b.allow("k", t) for t in range(6)] == [True] * 5 + [False]
    assert [a.allow("k", t) for t in (0, 1, 2)] == [True, True, False]


def test_instances_do_not_touch_the_default_limiter():
    rl = RateLimiter(1, 10)
    rl.allow("k", 0)
    assert limiter.remaining("k", 0) == 3
    assert limiter.allow("k", 0) is True
    assert rl.remaining("k", 0) == 0


def test_configure_keeps_existing_hits():
    rl = RateLimiter(3, 10)
    rl.allow("k", 0)
    rl.allow("k", 1)
    rl.configure(2, 10)
    assert rl.remaining("k", 2) == 0
    assert rl.allow("k", 2) is False
    rl.configure(2, 1.5)  # a shorter window expires the older hits at once
    assert rl.allow("k", 2) is True


@pytest.mark.parametrize("args", [(0, 10), (-1, 10), (1, 0), (1, -5)])
def test_invalid_settings_raise_value_error(args):
    with pytest.raises(ValueError):
        RateLimiter(*args)
    rl = RateLimiter(2, 10)
    with pytest.raises(ValueError):
        rl.configure(*args)
    # A failed configure leaves the old settings in place.
    assert [rl.allow("k", t) for t in (0, 1, 2)] == [True, True, False]


def test_reset_one_key_or_all():
    rl = RateLimiter(1, 10)
    rl.allow("a", 0)
    rl.allow("b", 0)
    rl.reset("a")
    assert rl.allow("a", 1) is True
    assert rl.allow("b", 1) is False
    rl.reset()
    assert rl.allow("b", 2) is True
    rl.reset("missing")  # unknown key is not an error


def test_module_functions_delegate_to_the_default_limiter():
    limiter.configure(2, 30)
    assert limiter.allow("k", 0) is True
    assert DEFAULT_LIMITER.remaining("k", 1) == 1
    DEFAULT_LIMITER.allow("k", 2)
    assert limiter.allow("k", 3) is False
    assert limiter.remaining("k", 3) == 0
    limiter.reset("k")
    assert limiter.remaining("k", 3) == 2
    limiter.reset()
    assert DEFAULT_LIMITER.remaining("other", 0) == 2


def test_module_configure_validates():
    with pytest.raises(ValueError):
        limiter.configure(0, 5)
    assert isinstance(DEFAULT_LIMITER, RateLimiter)
