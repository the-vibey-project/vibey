import limiter


def setup_function(_fn):
    limiter.configure(3, 60)
    limiter.reset()


def test_blocks_after_the_limit():
    assert [limiter.allow("a", t) for t in (0, 1, 2, 3)] == [True, True, True, False]


def test_keys_are_independent():
    for t in (0, 1, 2):
        limiter.allow("a", t)
    assert limiter.allow("b", 3) is True


def test_window_expires_hits():
    for t in (0, 1, 2):
        limiter.allow("a", t)
    assert limiter.allow("a", 61) is True


def test_remaining():
    limiter.allow("a", 0)
    assert limiter.remaining("a", 1) == 2
