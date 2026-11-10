import ast
from pathlib import Path

import pytest
import report
import textstats
import tokenizer


def _imports(module) -> set[str]:
    tree = ast.parse(Path(module.__file__).read_text())
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def test_the_two_new_modules_do_not_import_each_other():
    assert "report" not in _imports(tokenizer)
    assert "tokenizer" not in _imports(report)


@pytest.mark.parametrize("name", ["STOPWORDS", "tokenize", "word_counts", "top_words"])
def test_textstats_reexports_the_very_same_tokenizer_objects(name):
    assert getattr(textstats, name) is getattr(tokenizer, name)


@pytest.mark.parametrize("name", ["render_table", "render_csv"])
def test_textstats_reexports_the_very_same_report_objects(name):
    assert getattr(textstats, name) is getattr(report, name)


def test_summary_stays_in_textstats():
    assert textstats.summary.__module__ == "textstats"
    assert callable(textstats.summary)


def test_stopwords_value():
    assert frozenset({"the", "a", "an", "and", "of", "to", "in", "is"}) == tokenizer.STOPWORDS


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Hello, World!", ["hello", "world"]),
        ("Don't stop; 'quoted' words' end", ["don't", "stop", "quoted", "words", "end"]),
        ("rock'n'roll it's 3'4", ["rock'n'roll", "it's", "3'4"]),
        ("Café au lait", ["caf", "au", "lait"]),
        ("snake_case-and-kebab", ["snake", "case", "and", "kebab"]),
        ("   ", []),
        ("", []),
    ],
)
def test_tokenize(text, expected):
    assert tokenizer.tokenize(text) == expected


def test_word_counts_keep_first_seen_order_and_optionally_drop_stopwords():
    text = "the cat and The dog and THE cat"
    assert list(tokenizer.word_counts(text).items()) == [
        ("the", 3),
        ("cat", 2),
        ("and", 2),
        ("dog", 1),
    ]
    assert tokenizer.word_counts(text, True) == {"cat": 2, "dog": 1}
    assert tokenizer.word_counts(text, drop_stopwords=True) == {"cat": 2, "dog": 1}
    assert tokenizer.word_counts("") == {}


def test_top_words_ranking_and_limits():
    text = "pear apple fig pear apple kiwi kiwi fig plum"
    assert tokenizer.top_words(text, 3) == [("apple", 2), ("fig", 2), ("kiwi", 2)]
    assert tokenizer.top_words(text, 99)[-2:] == [("pear", 2), ("plum", 1)]
    assert tokenizer.top_words(text, 0) == []
    assert tokenizer.top_words(text, -4) == []
    assert tokenizer.top_words("a an the of", 3) == []
    assert tokenizer.top_words("the the cat", 3, drop_stopwords=False) == [("the", 2), ("cat", 1)]
    assert tokenizer.top_words("x y x")[0] == ("x", 2)  # default n is 3


def test_render_table_widths_follow_the_longest_cell():
    rows = [("elephant", 12), ("ox", 3)]
    assert report.render_table(rows) == (
        "word     | count\n---------+------\nelephant |    12\nox       |     3"
    )


def test_render_table_with_no_rows_is_just_the_header():
    assert report.render_table([]) == "word | count\n-----+------"


def test_render_table_wide_count_column():
    assert report.render_table([("a", 1234567)]) == (
        "word |   count\n-----+--------\na    | 1234567"
    )


def test_render_csv_quotes_only_when_needed_and_ends_with_a_newline():
    rows = [("plain", 2), ("a,b", 1), ('say "hi"', 1), ("it's", 4)]
    assert report.render_csv(rows) == ('word,count\nplain,2\n"a,b",1\n"say ""hi""",1\nit\'s,4\n')
    assert report.render_csv([]) == "word,count\n"


def test_summary_formats():
    text = "apple apple pear the the the"
    assert (
        textstats.summary(text, 2) == "word  | count\n------+------\napple |     2\npear  |     1"
    )
    assert textstats.summary(text, 2, "csv") == "word,count\napple,2\npear,1\n"
    assert textstats.summary(text, fmt="csv") == "word,count\napple,2\npear,1\n"
    assert textstats.summary("", 3, "csv") == "word,count\n"
    assert textstats.summary("", 3) == "word | count\n-----+------"
    with pytest.raises(ValueError, match="unknown format: xml"):
        textstats.summary("x", 1, "xml")
    with pytest.raises(ValueError):
        textstats.summary("x", 1, "TABLE")
