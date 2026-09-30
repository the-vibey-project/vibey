# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The checkout DECOMPOSE judges a plan's file references against."""

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

from vibey.application.interfaces import CheckoutLocator, CheckoutView
from vibey.infrastructure.build.checkout import FilesystemCheckout, ProjectCheckoutLocator
from vibey.infrastructure.build.interfaces import (
    FilesystemCheckoutInterface,
    ProjectCheckoutLocatorInterface,
)


def test_a_path_in_the_checkout_exists_and_one_outside_it_never_does(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    (root / "scripts" / "check.py").write_text("print(1)\n")
    (tmp_path / "secret.txt").write_text("x")
    checkout = FilesystemCheckout(root)

    assert isinstance(checkout, FilesystemCheckoutInterface)
    assert isinstance(checkout, CheckoutView)
    assert checkout.root == root.resolve()
    assert checkout.exists("scripts/check.py")
    assert checkout.exists("scripts")
    assert checkout.exists(".")
    assert not checkout.exists("generate_toc.py")
    assert not checkout.exists("../secret.txt")


class Projects:
    def __init__(self, repo_path: Path | None) -> None:
        self.repo_path = repo_path

    async def get(self, project_id: UUID) -> SimpleNamespace | None:
        if self.repo_path is None:
            return None
        return SimpleNamespace(
            project_id=project_id, repo_path=self.repo_path, created_at=datetime.now(UTC)
        )


async def test_the_locator_finds_the_project_working_tree(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# x\n")
    locator = ProjectCheckoutLocator(Projects(tmp_path))  # type: ignore[arg-type]

    assert isinstance(locator, ProjectCheckoutLocatorInterface)
    assert isinstance(locator, CheckoutLocator)
    view = await locator.checkout(uuid4())
    assert view is not None
    assert view.exists("README.md")


async def test_no_project_or_no_tree_is_no_checkout(tmp_path: Path) -> None:
    assert await ProjectCheckoutLocator(Projects(None)).checkout(uuid4()) is None  # type: ignore[arg-type]
    gone = ProjectCheckoutLocator(Projects(tmp_path / "gone"))  # type: ignore[arg-type]
    assert await gone.checkout(uuid4()) is None
