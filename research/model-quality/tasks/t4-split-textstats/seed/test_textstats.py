import textstats


def test_tokenize_lowercases_and_keeps_apostrophes():
    assert textstats.tokenize("Don't STOP, believing!") == ["don't", "stop", "believing"]


def test_top_words_ties_are_alphabetical():
    assert textstats.top_words("pear fig pear fig kiwi", 2) == [("fig", 2), ("pear", 2)]


def test_stopwords_are_dropped_by_default_in_top_words():
    assert textstats.top_words("the cat and the hat", 5) == [("cat", 1), ("hat", 1)]


def test_summary_table():
    out = textstats.summary("apple apple pear", 2)
    assert out == "word  | count\n------+------\napple |     2\npear  |     1"


def test_summary_rejects_unknown_format():
    try:
        textstats.summary("x", 1, "xml")
    except ValueError as exc:
        assert "xml" in str(exc)
    else:
        raise AssertionError("expected ValueError")
