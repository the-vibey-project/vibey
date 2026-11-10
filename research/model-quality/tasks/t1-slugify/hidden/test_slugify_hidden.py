import pytest
from slugify import slugify


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Hello,  World!", "hello-world"),
        ("  Already-slug  ", "already-slug"),
        ("A_B c", "a-b-c"),
        ("---", ""),
        ("Python 3.12", "python-3-12"),
        ("", ""),
    ],
)
def test_slugify(text: str, expected: str) -> None:
    assert slugify(text) == expected
