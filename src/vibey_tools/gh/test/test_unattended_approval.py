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
    DEFAULT_APPROVAL_FORBIDDEN,
    UnattendedApprovalConfig,
    load_config,
)

GRANTED = {
    "enabled": True,
    "branches": ["lane/*"],
    "forbidden_paths": [".vibey-gh.toml", ".github/**"],
}


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


def test_an_absent_table_is_the_same_as_no_grant(tmp_path: Path) -> None:
    assert load_config(write(tmp_path, None)).unattended_approval.enabled is False


def test_a_disabled_table_validates_nothing(tmp_path: Path) -> None:
    """Off is off. A disabled grant with nonsense in it is inert, not an error."""
    grant = UnattendedApprovalConfig(enabled=False, branches=(), forbidden_paths=())
    assert grant.enabled is False


# --------------------------------------------------------------------------- parsing


def test_the_loader_reads_every_key(tmp_path: Path) -> None:
    root = write(tmp_path, {**GRANTED, "require_all_gates": False})
    grant = load_config(root).unattended_approval
    assert grant.enabled is True
    assert grant.branches == ("lane/*",)
    assert grant.forbidden_paths == (".vibey-gh.toml", ".github/**")
    assert grant.require_all_gates is False


def test_omitted_keys_take_their_declared_defaults(tmp_path: Path) -> None:
    root = write(tmp_path, {"enabled": True, "branches": ["lane/*"]})
    grant = load_config(root).unattended_approval
    assert grant.forbidden_paths == DEFAULT_APPROVAL_FORBIDDEN
    assert grant.require_all_gates is True


# --------------------------------------------------------------------------- refusals


def test_enabled_with_no_branch_is_refused() -> None:
    """A grant that names no branch says nothing, and silence is not consent (12.d)."""
    with pytest.raises(ValueError, match="branches must not be empty"):
        UnattendedApprovalConfig(enabled=True, branches=())


def test_enabled_with_no_forbidden_path_is_refused() -> None:
    with pytest.raises(ValueError, match="forbidden_paths must not be empty"):
        UnattendedApprovalConfig(enabled=True, branches=("lane/*",), forbidden_paths=())


def test_the_grant_must_forbid_changes_to_itself() -> None:
    """12.f: an approver never widens its own mandate.

    Left out, an approver could approve a change to `forbidden_paths` and thereby approve
    anything at all afterwards. It is the one entry the list cannot be allowed to lose, so
    it is enforced rather than documented.
    """
    with pytest.raises(ValueError, match=r"must contain '\.vibey-gh\.toml'"):
        UnattendedApprovalConfig(
            enabled=True, branches=("lane/*",), forbidden_paths=(".github/**",)
        )


@pytest.mark.parametrize("bad", [("lane/*", ""), ("lane/*", "   ")])
def test_a_blank_branch_is_refused(bad: tuple[str, ...]) -> None:
    with pytest.raises(ValueError, match="branches entries must be non-empty"):
        UnattendedApprovalConfig(enabled=True, branches=bad)


def test_a_duplicated_branch_is_refused() -> None:
    with pytest.raises(ValueError, match="branches entries must be unique"):
        UnattendedApprovalConfig(enabled=True, branches=("lane/*", "lane/*"))


def test_a_blank_forbidden_path_is_refused() -> None:
    with pytest.raises(ValueError, match="forbidden_paths entries must be non-empty"):
        UnattendedApprovalConfig(
            enabled=True, branches=("lane/*",), forbidden_paths=(".vibey-gh.toml", "")
        )


def test_a_duplicated_forbidden_path_is_refused() -> None:
    with pytest.raises(ValueError, match="forbidden_paths entries must be unique"):
        UnattendedApprovalConfig(
            enabled=True,
            branches=("lane/*",),
            forbidden_paths=(".vibey-gh.toml", ".vibey-gh.toml"),
        )


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


def test_doctor_still_names_a_key_it_does_not_read(tmp_path: Path) -> None:
    """Knowing the section must not blanket-approve whatever is inside it."""
    root = write(tmp_path, GRANTED)
    with (root / ".vibey-gh.toml").open("a", encoding="utf-8") as handle:
        handle.write("invented_key = true\n")
    messages = [dataclasses.astuple(f)[1] for f in doctor._check_unknown_keys(root)]
    assert any("invented_key" in m for m in messages), messages
