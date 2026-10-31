# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The error catalog: a validated table of permanent codes, looked up by exact type (#1691)."""

from __future__ import annotations

import pytest

from vibey.cli.error_catalog import ErrorCatalog
from vibey.cli.interfaces.error_catalog_interface import ErrorCatalogInterface, ErrorEntry
from vibey.domain.errors import UnknownGate, UnknownProject, VibeyError


def entry(**changes) -> ErrorEntry:
    base = dict(
        qualname="vibey.domain.errors.UnknownProject",
        title="No project has that id",
        cause="No project exists.",
        fix="List them.",
        code="E0001",
    )
    return ErrorEntry(**(base | changes))


def test_the_catalog_honours_its_interface_and_looks_entries_up_exactly() -> None:
    catalog = ErrorCatalog([entry()])
    assert isinstance(catalog, ErrorCatalogInterface)
    assert catalog.entry_for(UnknownProject) == entry()
    # No inheritance fallback: a subclass or sibling without its own entry has none.
    assert catalog.entry_for(UnknownGate) is None
    assert catalog.entry_for(VibeyError) is None
    assert [e.code for e in catalog.entries()] == ["E0001"]


def test_a_code_is_found_whatever_its_case_or_padding() -> None:
    catalog = ErrorCatalog([entry()])
    assert catalog.by_code(" e0001 ") == entry()
    assert catalog.by_code("E0002") is None


def test_an_abstract_base_has_no_code_and_is_never_found_by_one() -> None:
    base = entry(qualname="vibey.domain.errors.VibeyError", code=None, abstract=True, fix="")
    catalog = ErrorCatalog([base])
    assert catalog.entry_for(VibeyError) == base
    assert catalog.by_code("") is None


@pytest.mark.parametrize(
    "entries, message",
    [
        ([entry(), entry(code="E0002")], "is listed twice"),
        ([entry(), entry(qualname="a.B")], "code E0001 is used twice"),
        ([entry(code="E1")], "needs a code of the form"),
        ([entry(code=None)], "needs a code of the form"),
        ([entry(cause=" ")], "needs a cause and a fix"),
        ([entry(fix="")], "needs a cause and a fix"),
        ([entry(title="")], "needs a title"),
        ([entry(abstract=True)], "abstract and so has no code"),
    ],
)
def test_a_malformed_table_is_refused_naming_the_entry(entries, message) -> None:
    with pytest.raises(ValueError, match=message):
        ErrorCatalog(entries)


def test_a_table_loads_from_toml_and_a_missing_key_is_named() -> None:
    text = (
        '[[error]]\ncode = "E0001"\nclass = "a.B"\ntitle = "t"\ncause = "c"\nfix = "f"\n'
        '[[error]]\nclass = "a.Base"\ntitle = "t"\nabstract = true\ncause = "c"\n'
    )
    catalog = ErrorCatalog.from_toml(text)
    assert [e.qualname for e in catalog.entries()] == ["a.B", "a.Base"]
    assert catalog.by_code("E0001") is not None
    with pytest.raises(ValueError, match="no 'title'"):
        ErrorCatalog.from_toml('[[error]]\nclass = "a.B"\ncause = "c"\n')
    assert ErrorCatalog.from_toml("").entries() == ()


def test_retired_is_read_from_the_table() -> None:
    text = '[[error]]\ncode = "E0009"\nclass = "a.Gone"\ntitle = "t"\ncause = "c"\nfix = "f"\nretired = true\n'
    assert ErrorCatalog.from_toml(text).by_code("E0009").retired is True  # type: ignore[union-attr]


def test_the_shipped_table_loads_and_is_cached() -> None:
    assert ErrorCatalog.shipped() is ErrorCatalog.shipped()
    assert ErrorCatalog.shipped().by_code("E0001") is not None
