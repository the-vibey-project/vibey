# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`[budget] ultra_no_cap` edited as text: the operator's other lines survive (ADR-0063)."""

import tomllib
from pathlib import Path

import pytest

from vibey.infrastructure.budget_declaration import VibeyTomlBudgetDeclaration
from vibey.infrastructure.interfaces.budget_declaration_interface import (
    BudgetDeclarationInterface,
)

DECL = VibeyTomlBudgetDeclaration()


def test_it_satisfies_its_interface() -> None:
    assert isinstance(DECL, BudgetDeclarationInterface)


@pytest.mark.parametrize(
    ("text", "enabled", "expected"),
    [
        ("", True, "[budget]\nultra_no_cap = true\n"),
        (
            "[features]\ngptossloop = true\n",
            True,
            "[features]\ngptossloop = true\n\n[budget]\nultra_no_cap = true\n",
        ),
        (
            "[budget]  # caps\nmax_dollars_per_cycle = 5\n",
            True,
            "[budget]  # caps\nultra_no_cap = true\nmax_dollars_per_cycle = 5\n",
        ),
        (
            "# mine\n[budget]\nultra_no_cap = true\n[x]\ny = 1\n",
            False,
            "# mine\n[budget]\nultra_no_cap = false\n[x]\ny = 1\n",
        ),
        (
            "[features]\nultra_no_cap = 1\n",
            True,
            "[features]\nultra_no_cap = 1\n\n[budget]\nultra_no_cap = true\n",
        ),
    ],
)
def test_edit_replaces_inserts_or_appends(text: str, enabled: bool, expected: str) -> None:
    assert DECL.edit(text, enabled) == expected
    tomllib.loads(DECL.edit(text, enabled))


def test_write_creates_refuses_and_read_reads(tmp_path: Path) -> None:
    path = tmp_path / "vibey.toml"
    assert DECL.read(path) is False
    DECL.write(path, True)
    assert DECL.read(path) is True
    DECL.write(path, False)
    assert DECL.read(path) is False
    broken = tmp_path / "broken.toml"
    broken.write_text("[budget\n", encoding="utf-8")
    with pytest.raises(tomllib.TOMLDecodeError):
        DECL.write(broken, True)
    assert broken.read_text(encoding="utf-8") == "[budget\n"
    assert DECL.read(broken) is False
    other = tmp_path / "other.toml"
    other.write_text("[features]\nx = 1\n", encoding="utf-8")
    assert DECL.read(other) is False
    odd = tmp_path / "odd.toml"
    odd.write_text("[budget]\nultra_no_cap = 1\n", encoding="utf-8")
    assert DECL.read(odd) is False
