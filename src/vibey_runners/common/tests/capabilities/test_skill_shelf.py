# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The skill shelf: exactly the skills a run's document names, then its plugins' commands, paged
within an answer budget and read page by page, never cut (SP-LOOPS Phase 5, R9-R11; Review
Focus 4)."""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

import pytest
from fakes import RecordingReader
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from vibey_runners.common.capabilities.bundle import BundleSpec
from vibey_runners.common.capabilities.interfaces.skill_shelf_interface import (
    SkillShelfInterface,
)
from vibey_runners.common.capabilities.resolver import DESCRIPTION_MAX_CHARS
from vibey_runners.common.capabilities.shelf_entry import ShelfEntry
from vibey_runners.common.capabilities.shelf_page import ShelfPage
from vibey_runners.common.capabilities.shelf_text import ShelfText
from vibey_runners.common.capabilities.skill_catalog import SkillCatalog
from vibey_runners.common.capabilities.skill_entry import SkillEntry
from vibey_runners.common.capabilities.skill_index import SKILL_MAX_BYTES, SkillIndex
from vibey_runners.common.capabilities.skill_shelf import MIN_ANSWER_CHARS, SkillShelf
from vibey_runners.common.capabilities.skill_shelf_error import SkillShelfError
from vibey_runners.common.capabilities.snapshot import CapabilitySnapshot
from vibey_runners.common.capabilities.snapshot_document import SnapshotDocument

DIGEST = "sha256:" + "cd" * 32


def _skill(plugin: Path, name: str, description: str, body: str = "# Body\n") -> Path:
    folder = plugin / "skills" / name
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "SKILL.md"
    path.write_text(f"---\nname: {name}\ndescription: {description}\n---\n\n{body}", "utf-8")
    return Path(os.path.realpath(path))


def _command(plugin: Path, name: str, text: str) -> Path:
    folder = plugin / "commands"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.md"
    path.write_text(text, encoding="utf-8")
    return Path(os.path.realpath(path))


def _document(plugin_dirs: Sequence[Path], names: Sequence[str] | None = None) -> SnapshotDocument:
    """The document of a snapshot over `plugin_dirs` that names `names` (`plugin:skill`), or
    every skill the index finds."""
    catalog = SkillIndex().build(plugin_dirs)
    kept = tuple(
        entry
        for entry in catalog.skills
        if names is None or f"{entry.plugin}:{entry.name}" in names
    )
    if names is not None:
        order = {name: index for index, name in enumerate(names)}
        kept = tuple(sorted(kept, key=lambda entry: order[f"{entry.plugin}:{entry.name}"]))
    snapshot = CapabilitySnapshot(
        tuple(plugin_dirs), SkillCatalog(kept, ()), (), DIGEST, plugin_dirs[0].parent
    )
    return SnapshotDocument.of(snapshot, BundleSpec.from_mapping({"plugins": []}), [])


@pytest.fixture
def plugins(tmp_path: Path) -> tuple[Path, Path]:
    alpha = tmp_path / "alpha"
    beta = tmp_path / "beta"
    _skill(alpha, "lint", "Lints\tthe tree.")
    _skill(alpha, "format", "Formats the tree.")
    _skill(beta, "ship", "Ships it.")
    _command(alpha, "verify", "---\ndescription: Runs every gate\n---\nRun them.\n")
    _command(beta, "release", "Cuts a release.\n")
    return alpha, beta


def _names(shelf: SkillShelf) -> list[str]:
    return [entry.name for entry in shelf.entries]


def test_the_shelf_satisfies_its_interface(plugins: tuple[Path, Path]) -> None:
    assert isinstance(SkillShelf.of(_document(plugins)), SkillShelfInterface)


def test_the_shelf_holds_exactly_the_documents_skills_in_order_then_the_commands(
    plugins: tuple[Path, Path],
) -> None:
    alpha, beta = plugins
    document = _document(plugins, ["beta:ship", "alpha:lint", "alpha:format"])
    shelf = SkillShelf.of(document)
    assert shelf.entries == (
        ShelfEntry("beta:ship", "skill", "Ships it.", _real(beta / "skills/ship/SKILL.md")),
        ShelfEntry("alpha:lint", "skill", "Lints the tree.", _real(alpha / "skills/lint/SKILL.md")),
        ShelfEntry(
            "alpha:format", "skill", "Formats the tree.", _real(alpha / "skills/format/SKILL.md")
        ),
        ShelfEntry(
            "alpha:verify", "command", "Runs every gate", _real(alpha / "commands/verify.md")
        ),
        ShelfEntry(
            "beta:release", "command", "Cuts a release.", _real(beta / "commands/release.md")
        ),
    )
    assert shelf.skipped == ()


def _real(path: Path) -> Path:
    return Path(os.path.realpath(path))


def test_a_skill_the_document_does_not_name_is_never_shelved(
    plugins: tuple[Path, Path],
) -> None:
    reader = RecordingReader()
    shelf = SkillShelf.of(_document(plugins, ["alpha:lint"]), reader=reader)
    assert _names(shelf) == ["alpha:lint", "alpha:verify", "beta:release"]
    with pytest.raises(SkillShelfError):
        shelf.read("alpha:format", 1, 4096)
    with pytest.raises(SkillShelfError):
        shelf.read("beta:ship", 1, 4096)
    assert reader.paths == []


def test_a_named_skill_its_plugin_no_longer_holds_is_skipped_with_a_reason(
    plugins: tuple[Path, Path],
) -> None:
    _alpha, beta = plugins
    document = _document(plugins, ["alpha:lint", "beta:ship"])
    (beta / "skills" / "ship" / "SKILL.md").unlink()
    shelf = SkillShelf.of(document)
    assert _names(shelf) == ["alpha:lint", "alpha:verify", "beta:release"]
    assert shelf.skipped == (
        (_real(beta / "skills" / "ship"), "has no SKILL.md"),
        (beta, "the run's document names the skill beta:ship, which its plugin no longer holds"),
    )


def test_a_named_skill_of_a_plugin_the_document_does_not_hold_is_skipped(tmp_path: Path) -> None:
    alpha = tmp_path / "alpha"
    lint = _skill(alpha, "lint", "Lints.")
    catalog = SkillCatalog((SkillEntry("ghost", "haunt", "Haunts.", lint),), ())
    snapshot = CapabilitySnapshot((alpha,), catalog, (), DIGEST, tmp_path)
    document = SnapshotDocument.of(snapshot, BundleSpec.from_mapping({"plugins": []}), [])
    shelf = SkillShelf.of(document)
    assert shelf.entries == ()
    assert shelf.skipped == (
        (
            Path("ghost"),
            "the run's document names the skill ghost:haunt, which its plugin no longer holds",
        ),
    )


def test_a_command_named_like_a_skill_is_skipped_with_a_reason(tmp_path: Path) -> None:
    alpha = tmp_path / "alpha"
    _skill(alpha, "verify", "Verifies.")
    clash = _command(alpha, "verify", "A command with the skill's name.\n")
    shelf = SkillShelf.of(_document([alpha]))
    assert shelf.entries == (
        ShelfEntry("alpha:verify", "skill", "Verifies.", _real(alpha / "skills/verify/SKILL.md")),
    )
    assert shelf.skipped == (
        (clash, "is the command alpha:verify, which a skill of that name already is"),
    )


def test_a_skill_description_is_held_to_one_safe_line(tmp_path: Path) -> None:
    alpha = tmp_path / "alpha"
    _skill(alpha, "long", "‮" + "d" * (DESCRIPTION_MAX_CHARS * 2))
    (entry,) = SkillShelf.of(_document([alpha])).entries
    assert len(entry.description) == DESCRIPTION_MAX_CHARS
    assert entry.description.endswith("...")
    assert "‮" not in entry.description


# -- paging the list ---------------------------------------------------------------------------


def _json(entries: Sequence[ShelfEntry]) -> str:
    """A page as the widest form the tools could write it: ASCII-escaped, default separators."""
    return json.dumps(
        [{"name": e.name, "kind": e.kind, "description": e.description} for e in entries]
    )


def test_a_page_holds_every_entry_when_the_shelf_fits(plugins: tuple[Path, Path]) -> None:
    shelf = SkillShelf.of(_document(plugins))
    assert shelf.page(1, 4096) == ShelfPage(shelf.entries, 1, 1)


def test_pages_are_filled_greedily_in_order(tmp_path: Path) -> None:
    alpha = tmp_path / "alpha"
    for number in range(12):
        _skill(alpha, f"s{number:02d}", f"Skill {number} " + "w" * 120)
    shelf = SkillShelf.of(_document([alpha]))
    budget = MIN_ANSWER_CHARS
    pages = [shelf.page(1, budget)]
    while pages[-1].number < pages[-1].pages:
        pages.append(shelf.page(pages[-1].number + 1, budget))
    assert [entry for page in pages for entry in page.entries] == list(shelf.entries)
    assert all(len(_json(page.entries)) <= budget for page in pages)
    for page, following in zip(pages, pages[1:], strict=False):
        assert len(_json((*page.entries, following.entries[0]))) > budget
    assert {page.pages for page in pages} == {len(pages)}


def test_an_entry_too_long_for_any_page_is_shown_by_name_only(tmp_path: Path) -> None:
    alpha = tmp_path / "alpha"
    _skill(alpha, "short", "Short.")
    _skill(alpha, "wordy", "w" * 900)
    shelf = SkillShelf.of(_document([alpha]))
    short, wordy = shelf.entries
    assert len(_json([wordy])) > MIN_ANSWER_CHARS
    page = shelf.page(1, MIN_ANSWER_CHARS)
    assert page == ShelfPage((short, replace(wordy, description="")), 1, 1)
    assert shelf.page(1, 4096) == ShelfPage((short, wordy), 1, 1)


def test_an_empty_shelf_has_one_empty_page(tmp_path: Path) -> None:
    alpha = tmp_path / "alpha"
    alpha.mkdir()
    shelf = SkillShelf.of(_document([alpha]))
    assert shelf.entries == ()
    assert shelf.page(1, MIN_ANSWER_CHARS) == ShelfPage((), 1, 1)


def test_an_answer_budget_below_the_floor_is_refused(plugins: tuple[Path, Path]) -> None:
    shelf = SkillShelf.of(_document(plugins))
    with pytest.raises(ValueError, match=f"at least {MIN_ANSWER_CHARS}"):
        shelf.page(1, MIN_ANSWER_CHARS - 1)
    with pytest.raises(ValueError, match=f"at least {MIN_ANSWER_CHARS}"):
        shelf.read("alpha:lint", 1, MIN_ANSWER_CHARS - 1)


def test_an_unknown_name_or_page_names_the_shelf_size(plugins: tuple[Path, Path]) -> None:
    shelf = SkillShelf.of(_document(plugins))
    with pytest.raises(SkillShelfError) as unknown:
        shelf.read("alpha:nothing", 1, 4096)
    assert str(unknown.value) == (
        "there is no skill or command 'alpha:nothing' on this run's shelf of 5 entries "
        "(skills_list shows them on 1 page)"
    )
    for number in (0, 2):
        with pytest.raises(SkillShelfError) as page:
            shelf.page(number, 4096)
        assert str(page.value) == (
            f"there is no page {number} of this run's shelf of 5 entries; it has 1 page"
        )
    with pytest.raises(SkillShelfError) as body:
        shelf.read("alpha:lint", 3, 4096)
    assert str(body.value) == (
        "there is no page 3 of 'alpha:lint' on this run's shelf of 5 entries; it has 1 page"
    )
    assert isinstance(body.value, LookupError)


# -- reading a body -----------------------------------------------------------------------------


def test_a_body_is_paged_never_cut(tmp_path: Path) -> None:
    alpha = tmp_path / "alpha"
    long_line = "L" * 1500
    body = "".join(f"line {n}: " + "x" * (n % 70) + "\n" for n in range(200)) + long_line
    path = _skill(alpha, "big", "Big.", body + "\r\nend é\U0001f600 no newline")
    shelf = SkillShelf.of(_document([alpha]))
    first = shelf.read("alpha:big", 1, MIN_ANSWER_CHARS)
    texts = [first.text]
    for number in range(2, first.pages + 1):
        page = shelf.read("alpha:big", number, MIN_ANSWER_CHARS)
        assert (page.name, page.kind, page.number, page.pages) == (
            "alpha:big",
            "skill",
            number,
            first.pages,
        )
        texts.append(page.text)
    assert "".join(texts) == path.read_bytes().decode("utf-8")
    assert len(texts) > 2
    assert all(len(text) <= MIN_ANSWER_CHARS for text in texts)
    # A page ends at a line end, unless it is a full page of a line too long for any page.
    for text in texts[:-1]:
        assert _ends_a_line(text) or len(text) == MIN_ANSWER_CHARS
    assert "".join(texts).count(long_line) == 1


def _ends_a_line(text: str) -> bool:
    return text.splitlines(keepends=True)[-1] != text.splitlines()[-1]


def test_a_text_that_opens_with_a_line_longer_than_a_page_is_split_into_full_pages(
    tmp_path: Path,
) -> None:
    alpha = tmp_path / "alpha"
    text = "W" * (MIN_ANSWER_CHARS * 2 + 7) + "\nTail.\n"
    path = _command(alpha, "wide", text)
    shelf = SkillShelf.of(_document([alpha]))
    pages = [shelf.read("alpha:wide", number, MIN_ANSWER_CHARS) for number in (1, 2, 3)]
    assert [len(page.text) for page in pages] == [MIN_ANSWER_CHARS, MIN_ANSWER_CHARS, 14]
    assert {page.pages for page in pages} == {3}
    assert "".join(page.text for page in pages) == path.read_bytes().decode("utf-8")


def test_a_command_is_read_whole_as_a_command(plugins: tuple[Path, Path]) -> None:
    shelf = SkillShelf.of(_document(plugins))
    assert shelf.read("beta:release", 1, 4096) == ShelfText(
        "beta:release", "command", 1, 1, "Cuts a release.\n"
    )


def test_an_empty_body_is_one_empty_page(tmp_path: Path) -> None:
    alpha = tmp_path / "alpha"
    _skill(alpha, "lint", "Lints.")
    path = _command(alpha, "blank", "Blank.\n")
    shelf = SkillShelf.of(_document([alpha]))
    path.write_text("", encoding="utf-8")
    assert shelf.read("alpha:blank", 1, MIN_ANSWER_CHARS) == ShelfText(
        "alpha:blank", "command", 1, 1, ""
    )


def test_a_body_that_cannot_be_read_now_is_a_shelf_error(tmp_path: Path) -> None:
    alpha = tmp_path / "alpha"
    lint = _skill(alpha, "lint", "Lints.")
    big = _skill(alpha, "big", "Big.")
    latin = _skill(alpha, "latin", "Latin.")
    reader = RecordingReader(fail={lint: PermissionError(13, "Permission denied")})
    shelf = SkillShelf.of(_document([alpha]), reader=reader)
    big.write_bytes(b"x" * (SKILL_MAX_BYTES + 1))
    latin.write_bytes(b"caf\xe9")
    reasons = {}
    for name in ("alpha:lint", "alpha:big", "alpha:latin"):
        with pytest.raises(SkillShelfError) as caught:
            shelf.read(name, 1, 4096)
        reasons[name] = str(caught.value)
    assert reasons == {
        "alpha:lint": "'alpha:lint' cannot be read now: [Errno 13] Permission denied",
        "alpha:big": f"'alpha:big' cannot be read now: it is larger than {SKILL_MAX_BYTES} bytes",
        "alpha:latin": "'alpha:latin' cannot be read now: it is not UTF-8",
    }


@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    lines=st.lists(
        st.text(st.characters(codec="utf-8", exclude_categories=["Cs"]), max_size=900),
        max_size=40,
    ),
    budget=st.integers(MIN_ANSWER_CHARS, 3000),
    entries=st.lists(
        st.tuples(
            st.from_regex(r"[a-z][a-z0-9-]{0,40}", fullmatch=True),
            st.text(max_size=1500),
        ),
        max_size=30,
        unique_by=lambda pair: pair[0],
    ),
)
def test_every_page_fits_the_answer_budget(
    tmp_path_factory: pytest.TempPathFactory,
    lines: list[str],
    budget: int,
    entries: list[tuple[str, str]],
) -> None:
    alpha = tmp_path_factory.mktemp("shelf") / "alpha"
    body = "\n".join(lines)
    for name, description in entries:
        _command(alpha, name, f"---\ndescription: {json.dumps(description)}\n---\n")
    _command(alpha, "zzz-body", "---\ndescription: The body.\n---\n" + body)
    shelf = SkillShelf.of(_document([alpha]))
    first = shelf.page(1, budget)
    listed = list(first.entries)
    assert len(_json(first.entries)) <= budget
    for number in range(2, first.pages + 1):
        page = shelf.page(number, budget)
        assert len(_json(page.entries)) <= budget
        listed.extend(page.entries)
    assert [entry.name for entry in listed] == [entry.name for entry in shelf.entries]
    text = shelf.read("alpha:zzz-body", 1, budget)
    texts = [text.text]
    for number in range(2, text.pages + 1):
        texts.append(shelf.read("alpha:zzz-body", number, budget).text)
    assert all(len(page) <= budget for page in texts)
    assert "".join(texts) == (alpha / "commands" / "zzz-body.md").read_bytes().decode("utf-8")
