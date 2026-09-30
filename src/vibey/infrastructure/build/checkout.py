# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The project checkout DECOMPOSE judges a plan's file references against.

The checkout is the project's own working tree (`project.repo_path`), read through an
existence check and nothing else: the plan-reference rule only needs to know whether a
path is there. The working tree rather than a git ref, deliberately -- a file present
but untracked counts as present, so the rule can only miss a reference, never invent
one (`vibey.domain.plan_references`).
"""

from pathlib import Path
from uuid import UUID

from vibey.application.interfaces import CheckoutView, ProjectStore


class FilesystemCheckout:
    """A checkout on disk, answering whether a checkout-relative path exists in it."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    @property
    def root(self) -> Path:
        return self._root

    def exists(self, path: str) -> bool:
        target = (self._root / path).resolve()
        if target != self._root and self._root not in target.parents:
            return False
        return target.exists()


class ProjectCheckoutLocator:
    """Finds a project's checkout through the project store."""

    def __init__(self, projects: ProjectStore) -> None:
        self._projects = projects

    async def checkout(self, project_id: UUID) -> CheckoutView | None:
        project = await self._projects.get(project_id)
        if project is None or not Path(project.repo_path).is_dir():
            return None
        return FilesystemCheckout(Path(project.repo_path))
