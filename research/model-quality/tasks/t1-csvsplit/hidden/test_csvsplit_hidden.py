import pytest
from csvsplit import split_csv_line


def test_plain():
    assert split_csv_line("a,b,c") == ["a", "b", "c"]


def test_empty_fields():
    assert split_csv_line("a,,c") == ["a", "", "c"]
    assert split_csv_line("a,b,") == ["a", "b", ""]
    assert split_csv_line(",a") == ["", "a"]
    assert split_csv_line(",") == ["", ""]


def test_empty_line():
    assert split_csv_line("") == [""]


def test_quoted_comma():
    assert split_csv_line('"a,b",c') == ["a,b", "c"]


def test_escaped_quote():
    assert split_csv_line('"say ""hi"""') == ['say "hi"']
    assert split_csv_line('x,"a""b",y') == ["x", 'a"b', "y"]


def test_quoted_empty():
    assert split_csv_line('""') == [""]
    assert split_csv_line('a,"",b') == ["a", "", "b"]


def test_spaces_preserved():
    assert split_csv_line("a, b ,c") == ["a", " b ", "c"]
    assert split_csv_line('" a ",b') == [" a ", "b"]


def test_quote_inside_unquoted_field_is_literal():
    assert split_csv_line('ab"c,d') == ['ab"c', "d"]


def test_quoted_last_field():
    assert split_csv_line('a,"b,c"') == ["a", "b,c"]


def test_trailing_empty_after_quoted():
    assert split_csv_line('"a",') == ["a", ""]


def test_unterminated_quote():
    with pytest.raises(ValueError):
        split_csv_line('a,"b')
    with pytest.raises(ValueError):
        split_csv_line('"')


def test_text_after_closing_quote():
    with pytest.raises(ValueError):
        split_csv_line('"a"b,c')
