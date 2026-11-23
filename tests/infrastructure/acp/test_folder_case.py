# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`FolderCase`: whether the volume a folder is on folds case, asked of that volume (review 1
I-2), never assumed from the platform alone."""

from __future__ import annotations

import os

import pytest

from vibey.infrastructure.acp.folder_case import PC_CASE_SENSITIVE, FolderCase
from vibey.infrastructure.acp.interfaces.folder_case_interface import FolderCaseInterface


def test_it_is_its_interface() -> None:
    assert isinstance(FolderCase(), FolderCaseInterface)


@pytest.mark.parametrize(("answer", "folds"), [(0, True), (1, False)])
def test_macos_asks_the_volume(monkeypatch: pytest.MonkeyPatch, answer: int, folds: bool) -> None:
    asked: list[tuple[str, int]] = []

    def pathconf(path: str, name: int) -> int:
        asked.append((path, name))
        return answer

    monkeypatch.setattr(os, "pathconf", pathconf)
    assert FolderCase(platform="darwin").folds("/Users/me/app") is folds
    assert asked == [("/Users/me/app", PC_CASE_SENSITIVE)]


def test_a_folder_the_volume_cannot_be_asked_about_does_not_fold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def pathconf(path: str, name: int) -> int:
        raise FileNotFoundError(path)

    monkeypatch.setattr(os, "pathconf", pathconf)
    assert FolderCase(platform="darwin").folds("/gone") is False


def test_elsewhere_case_never_folds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(os, "pathconf", lambda path, name: 0)
    assert FolderCase(platform="linux").folds("/home/me/app") is False
