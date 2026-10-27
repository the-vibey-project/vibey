# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""There is one paper source and one publishing book definition (ADR-0032, #155, #1601).

`docs/paper.md` is the paper and the root `properdocs.yml` is the book. A second copy of
either drifts from the first and publishes a different document under the same name, so the
tracked file set is checked, not the working tree: untracked and ignored files (the built
`site/`, `.paper-source.md`) must not fail it.

The tenants still track their own papers and book definitions. Those are recorded in
`tests/meta/single_source.toml` as debts that can only shrink: a new second source fails, and
so does a recorded exception whose file is gone, so the removal and the entry go together.

Module-level test functions rather than a class with an interface beside it (ADR-0016):
pytest collects `test_*` functions, and the rule is about production code. The one helper
class below holds the checks so they can be run on synthetic file lists.
"""

from __future__ import annotations

import subprocess
import tomllib
from collections.abc import Iterable
from pathlib import Path, PurePosixPath

REPO = Path(__file__).resolve().parents[2]
EXCEPTIONS = Path(__file__).with_name("single_source.toml")
ROOT_PAPER = "docs/paper.md"
ROOT_BOOK = "properdocs.yml"
PAPER_NAMES = ("paper.md",)
BOOK_NAMES = ("properdocs.yml", "mkdocs.yml")


class SingleSource:
    """What is wrong with a tracked file set, given the recorded exceptions."""

    def __init__(
        self, tracked: Iterable[str], legacy_papers: Iterable[str], legacy_books: Iterable[str]
    ) -> None:
        self.tracked = frozenset(tracked)
        self.legacy_papers = frozenset(legacy_papers)
        self.legacy_books = frozenset(legacy_books)

    @staticmethod
    def named(paths: Iterable[str], names: tuple[str, ...]) -> set[str]:
        return {path for path in paths if PurePosixPath(path).name in names}

    def extra_papers(self) -> list[str]:
        """Tracked `paper.md` files that are neither the root paper nor a recorded exception."""
        found = self.named(self.tracked, PAPER_NAMES)
        return sorted(found - {ROOT_PAPER} - self.legacy_papers)

    def extra_books(self) -> list[str]:
        """Tracked book definitions that are neither the root one nor a recorded exception."""
        found = self.named(self.tracked, BOOK_NAMES)
        return sorted(found - {ROOT_BOOK} - self.legacy_books)

    def missing_roots(self) -> list[str]:
        return [root for root in (ROOT_PAPER, ROOT_BOOK) if root not in self.tracked]

    def stale_exceptions(self) -> list[str]:
        """Recorded exceptions whose file is no longer tracked: the entry must go with it."""
        return sorted((self.legacy_papers | self.legacy_books) - self.tracked)

    def root_named_as_exception(self) -> list[str]:
        return sorted({ROOT_PAPER, ROOT_BOOK} & (self.legacy_papers | self.legacy_books))


def tracked_files() -> list[str]:
    listed = subprocess.run(
        ["git", "ls-files", "-z"], cwd=REPO, check=True, capture_output=True, text=True
    ).stdout.split("\0")
    return [path for path in listed if path]


def recorded() -> tuple[list[str], list[str]]:
    table = tomllib.loads(EXCEPTIONS.read_text(encoding="utf-8"))
    return list(table["legacy_papers"]), list(table["legacy_book_definitions"])


def committed() -> SingleSource:
    papers, books = recorded()
    return SingleSource(tracked_files(), papers, books)


# ------------------------------------------------------------------- the repository


def test_one_paper_source_is_tracked() -> None:
    assert committed().extra_papers() == [], (
        "a second paper source is tracked; ADR-0032 keeps one (docs/paper.md). Remove it, "
        "or record it in tests/meta/single_source.toml with the issue that will remove it"
    )


def test_one_publishing_book_definition_is_tracked() -> None:
    assert committed().extra_books() == [], (
        "a second book definition is tracked; ADR-0032 keeps one (the root properdocs.yml). "
        "Remove it, or record it in tests/meta/single_source.toml with the issue that will remove it"
    )


def test_the_root_sources_exist() -> None:
    assert committed().missing_roots() == []


def test_every_recorded_exception_is_still_tracked() -> None:
    assert committed().stale_exceptions() == [], (
        "these files are gone: delete their entries from tests/meta/single_source.toml"
    )


def test_no_exception_names_the_root() -> None:
    assert committed().root_named_as_exception() == []


# ------------------------------------------------ the checks themselves, on synthetic lists


def checker(
    tracked: list[str], papers: tuple[str, ...] = (), books: tuple[str, ...] = ()
) -> SingleSource:
    return SingleSource(tracked, papers, books)


CLEAN = [ROOT_PAPER, ROOT_BOOK, "README.md"]


def test_a_clean_tree_is_clean() -> None:
    found = checker(CLEAN)
    assert (found.extra_papers(), found.extra_books(), found.missing_roots()) == ([], [], [])
    assert (found.stale_exceptions(), found.root_named_as_exception()) == ([], [])


def test_a_second_paper_anywhere_is_caught_by_its_name() -> None:
    assert checker([*CLEAN, "docs/drafts/paper.md"]).extra_papers() == ["docs/drafts/paper.md"]
    assert (
        checker([*CLEAN, "src/x/docs/paper.md"], papers=("src/x/docs/paper.md",)).extra_papers()
        == []
    )


def test_a_second_book_definition_of_either_kind_is_caught() -> None:
    assert checker([*CLEAN, "t/properdocs.yml", "t/mkdocs.yml"]).extra_books() == [
        "t/mkdocs.yml",
        "t/properdocs.yml",
    ]
    assert checker([*CLEAN, "t/mkdocs.yml"], books=("t/mkdocs.yml",)).extra_books() == []


def test_an_empty_tree_does_not_pass_for_lack_of_files() -> None:
    assert checker([]).missing_roots() == [ROOT_PAPER, ROOT_BOOK]


def test_an_exception_whose_file_is_gone_is_stale() -> None:
    found = checker(CLEAN, papers=("src/x/docs/paper.md",), books=("src/x/mkdocs.yml",))
    assert found.stale_exceptions() == ["src/x/docs/paper.md", "src/x/mkdocs.yml"]


def test_the_root_cannot_be_recorded_as_an_exception() -> None:
    found = checker(CLEAN, papers=(ROOT_PAPER,), books=(ROOT_BOOK,))
    assert found.root_named_as_exception() == [ROOT_PAPER, ROOT_BOOK]
