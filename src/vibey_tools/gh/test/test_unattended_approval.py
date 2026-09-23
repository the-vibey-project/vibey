# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Tests for `[unattended_approval]`, the operator's grant to a delegated approver.

Sub-doctrine 12.f puts the judgement in the grant rather than in the approver, so this table
is the standard an approver applies and cannot alter. Every validation below exists because
a grant that is wrong in that direction fails open — it would authorise something nobody
authorised — and the cost of that is paid with nobody watching.

The table was very nearly shipped as a TOML block alone. `load_config` tolerates an unknown
section, which made it look fine; `vibey-gh doctor` rejects one as an error, and two tests
enforce that. Testing the loader and concluding the repository accepted it was a claim true
about the thing measured and false about the thing that mattered — so
`test_doctor_reads_the_section_rather_than_merely_tolerating_it` is here to hold that shut.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from vibey_gh import doctor
from vibey_gh.config import (
    CODEOWNERS_SENTINEL,
    DEFAULT_APPROVAL_FORBIDDEN,
    UnattendedApprovalConfig,
    expand_authors,
    load_config,
)

GRANTED = {
    "enabled": True,
    "branches": ["lane/*"],
    "authors": ["adammatthewsteinberger"],
    "forbidden_paths": [".vibey-gh.toml", ".github/**"],
}
# The one login every refusal test below keeps constant, so each varies exactly the field it
# is named for. `authors` is required of an enabled grant, so a test that left it out would
# be testing the authors refusal rather than its own subject.
AUTHORS = ("adammatthewsteinberger",)


def write(root: Path, table: dict | None) -> Path:
    """A repository whose `.vibey-gh.toml` carries `table` as `[unattended_approval]`."""
    lines = ['[platform]\nkind = "github"\n']
    if table is not None:
        lines.append("\n[unattended_approval]\n")
        for key, value in table.items():
            if isinstance(value, bool):
                lines.append(f"{key} = {str(value).lower()}\n")
            elif isinstance(value, list):
                inner = ", ".join(f'"{v}"' for v in value)
                lines.append(f"{key} = [{inner}]\n")
    (root / ".vibey-gh.toml").write_text("".join(lines), encoding="utf-8")
    return root


# --------------------------------------------------------------------------- defaults


def test_the_default_grants_nothing() -> None:
    """An upgrade is not a grant.

    A repository that merely gained this version of vibey-gh has authorised no approver, so
    the default must refuse. A default that approved anything would make installing the tool
    the act of granting, which is exactly the consent nobody gave.
    """
    grant = UnattendedApprovalConfig()
    assert grant.enabled is False
    assert grant.branches == ()
    assert grant.authors == ()


def test_an_absent_table_is_the_same_as_no_grant(tmp_path: Path) -> None:
    assert load_config(write(tmp_path, None)).unattended_approval.enabled is False


def test_a_disabled_table_validates_nothing(tmp_path: Path) -> None:
    """Off is off. A disabled grant with nonsense in it is inert, not an error."""
    grant = UnattendedApprovalConfig(enabled=False, branches=(), authors=(), forbidden_paths=())
    assert grant.enabled is False


# --------------------------------------------------------------------------- parsing


def test_the_loader_reads_every_key(tmp_path: Path) -> None:
    root = write(tmp_path, {**GRANTED, "require_all_gates": False})
    grant = load_config(root).unattended_approval
    assert grant.enabled is True
    assert grant.branches == ("lane/*",)
    assert grant.authors == ("adammatthewsteinberger",)
    assert grant.forbidden_paths == (".vibey-gh.toml", ".github/**")
    assert grant.require_all_gates is False


def test_omitted_keys_take_their_declared_defaults(tmp_path: Path) -> None:
    root = write(tmp_path, {"enabled": True, "branches": ["lane/*"], "authors": list(AUTHORS)})
    grant = load_config(root).unattended_approval
    assert grant.forbidden_paths == DEFAULT_APPROVAL_FORBIDDEN
    assert grant.require_all_gates is True


# --------------------------------------------------------------------------- refusals


def test_enabled_with_no_branch_is_refused() -> None:
    """A grant that names no branch says nothing, and silence is not consent (12.d)."""
    with pytest.raises(ValueError, match="branches must not be empty"):
        UnattendedApprovalConfig(enabled=True, branches=(), authors=AUTHORS)


def test_enabled_with_no_author_is_refused() -> None:
    """A grant that names nobody authorises nobody.

    `branches` bounds where a change may land and says nothing about who pushed it, so an
    allowlist left empty is not a narrower grant -- it is a grant whose only remaining bound
    is a lane glob. Refusing it keeps the absence of a grant a refusal rather than a
    permission that happens to be spelled with no names in it (12.f).
    """
    with pytest.raises(ValueError, match="authors must not be empty"):
        UnattendedApprovalConfig(enabled=True, branches=("lane/*",), authors=())


def test_enabled_with_no_forbidden_path_is_refused() -> None:
    with pytest.raises(ValueError, match="forbidden_paths must not be empty"):
        UnattendedApprovalConfig(
            enabled=True, branches=("lane/*",), authors=AUTHORS, forbidden_paths=()
        )


def test_the_grant_must_forbid_changes_to_itself() -> None:
    """12.f: an approver never widens its own mandate.

    Left out, an approver could approve a change to `forbidden_paths` and thereby approve
    anything at all afterwards. It is the one entry the list cannot be allowed to lose, so
    it is enforced rather than documented.
    """
    with pytest.raises(ValueError, match=r"must contain '\.vibey-gh\.toml'"):
        UnattendedApprovalConfig(
            enabled=True, branches=("lane/*",), authors=AUTHORS, forbidden_paths=(".github/**",)
        )


@pytest.mark.parametrize("bad", [("lane/*", ""), ("lane/*", "   ")])
def test_a_blank_branch_is_refused(bad: tuple[str, ...]) -> None:
    with pytest.raises(ValueError, match="branches entries must be non-empty"):
        UnattendedApprovalConfig(enabled=True, branches=bad, authors=AUTHORS)


def test_a_duplicated_branch_is_refused() -> None:
    with pytest.raises(ValueError, match="branches entries must be unique"):
        UnattendedApprovalConfig(enabled=True, branches=("lane/*", "lane/*"), authors=AUTHORS)


@pytest.mark.parametrize("bad", [("adammatthewsteinberger", ""), ("adammatthewsteinberger", "  ")])
def test_a_blank_author_is_refused(bad: tuple[str, ...]) -> None:
    """A blank entry is the shape a templating mistake takes, and it must not read as a name.

    An allowlist is compared against a login, so an empty string is either matched by nothing
    -- dead weight nobody notices -- or, in some future comparison, by an author whose login
    the forge failed to report. Refusing it at load costs one error and removes both.
    """
    with pytest.raises(ValueError, match="authors entries must be non-empty"):
        UnattendedApprovalConfig(enabled=True, branches=("lane/*",), authors=bad)


def test_a_duplicated_author_is_refused() -> None:
    """Twice named is once granted, so the second entry is a mistake being reported."""
    with pytest.raises(ValueError, match="authors entries must be unique"):
        UnattendedApprovalConfig(
            enabled=True,
            branches=("lane/*",),
            authors=("adammatthewsteinberger", "adammatthewsteinberger"),
        )


def test_a_blank_forbidden_path_is_refused() -> None:
    with pytest.raises(ValueError, match="forbidden_paths entries must be non-empty"):
        UnattendedApprovalConfig(
            enabled=True,
            branches=("lane/*",),
            authors=AUTHORS,
            forbidden_paths=(".vibey-gh.toml", ""),
        )


def test_a_duplicated_forbidden_path_is_refused() -> None:
    with pytest.raises(ValueError, match="forbidden_paths entries must be unique"):
        UnattendedApprovalConfig(
            enabled=True,
            branches=("lane/*",),
            authors=AUTHORS,
            forbidden_paths=(".vibey-gh.toml", ".vibey-gh.toml"),
        )


# --------------------------------------------------------------------------- @codeowners


def write_codeowners(root: Path, text: str) -> Path:
    (root / ".github").mkdir(exist_ok=True)
    (root / ".github" / "CODEOWNERS").write_text(text, encoding="utf-8")
    return root


def test_the_sentinel_expands_to_the_logins_codeowners_names(tmp_path: Path) -> None:
    """One list of maintainers, not two that drift apart.

    CODEOWNERS already records who may approve a change to an owned path. Spelling those
    same people out again here would leave a repository one forgotten edit away from an
    allowlist that still names somebody the project no longer trusts with the paths.
    """
    write_codeowners(
        tmp_path,
        "# who owns what\n"
        "/tests/live/**    @adammatthewsteinberger\n"
        "/docs/**          @adammatthewsteinberger @second-owner  # @ignored-comment\n",
    )
    assert expand_authors((CODEOWNERS_SENTINEL,), tmp_path) == (
        "adammatthewsteinberger",
        "second-owner",
    )


def test_the_sentinel_keeps_order_and_drops_duplicates(tmp_path: Path) -> None:
    """A login spelled out AND inherited appears once, where it was first named."""
    write_codeowners(tmp_path, "/docs/**  @adammatthewsteinberger @second-owner\n")
    assert expand_authors(("adammatthewsteinberger", CODEOWNERS_SENTINEL, "third"), tmp_path) == (
        "adammatthewsteinberger",
        "second-owner",
        "third",
    )


def test_a_list_without_the_sentinel_is_returned_unchanged(tmp_path: Path) -> None:
    write_codeowners(tmp_path, "/docs/**  @somebody-else\n")
    assert expand_authors(("adammatthewsteinberger",), tmp_path) == ("adammatthewsteinberger",)


def test_a_missing_codeowners_file_expands_the_sentinel_to_nothing(tmp_path: Path) -> None:
    """No CODEOWNERS expands to nobody, and nobody is the closed end of the range.

    The alternative -- raising -- would make a repository without CODEOWNERS unable to load
    its configuration at all, which is a worse failure than the one it prevents. It is safe
    only because the empty result fails closed: an empty allowlist authorises nobody, never
    everybody, and an enabled grant left with no authors is refused outright.
    """
    assert expand_authors((CODEOWNERS_SENTINEL,), tmp_path) == ()
    with pytest.raises(ValueError, match="authors must not be empty"):
        UnattendedApprovalConfig(
            enabled=True,
            branches=("lane/*",),
            authors=expand_authors((CODEOWNERS_SENTINEL,), tmp_path),
        )


def test_a_codeowners_that_names_nobody_expands_to_nothing(tmp_path: Path) -> None:
    """The neighbouring case, and it must fail the same way rather than the opposite one."""
    write_codeowners(tmp_path, "# every line here is a comment\n\n")
    assert expand_authors((CODEOWNERS_SENTINEL,), tmp_path) == ()


# --------------------------------------------------------------------------- the doctor


def test_doctor_reads_the_section_rather_than_merely_tolerating_it(tmp_path: Path) -> None:
    """The check that would have caught shipping a TOML block with nothing behind it.

    `load_config` ignores an unknown table; `doctor` calls one an error. Adding the block
    without teaching the loader and the doctor about it produced a config that parsed
    cleanly and failed the build.
    """
    findings = doctor._check_unknown_keys(write(tmp_path, GRANTED))
    messages = [dataclasses.astuple(f)[1] for f in findings]
    assert not [m for m in messages if "unattended_approval" in m], messages


def test_doctor_does_not_flag_the_author_allowlist(tmp_path: Path) -> None:
    """`authors` is a key vibey-gh reads, so the doctor must not call it silently ignored.

    `_SECTION_KEYS` derives this section's keys from the dataclass, so adding a field ought
    to be enough -- but "ought to be enough" is what shipped a table the doctor rejected the
    first time, and a derivation is only a claim until something runs it.
    """
    findings = doctor._check_unknown_keys(write(tmp_path, GRANTED))
    messages = [dataclasses.astuple(f)[1] for f in findings]
    assert not [m for m in messages if "authors" in m], messages


def test_doctor_still_names_a_key_it_does_not_read(tmp_path: Path) -> None:
    """Knowing the section must not blanket-approve whatever is inside it."""
    root = write(tmp_path, GRANTED)
    with (root / ".vibey-gh.toml").open("a", encoding="utf-8") as handle:
        handle.write("invented_key = true\n")
    messages = [dataclasses.astuple(f)[1] for f in doctor._check_unknown_keys(root)]
    assert any("invented_key" in m for m in messages), messages
