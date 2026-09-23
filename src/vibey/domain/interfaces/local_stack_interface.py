# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Protocol interfaces for the local stack catalogue.

The types defined here mirror the concrete classes in
``src/vibey/domain/local_stack.py``.  They are used by consumers that only need
to depend on the surface contract, without pulling in the data‑class
implementations.  All definitions are marked ``runtime_checkable`` so that an
instance may be tested against the protocol at runtime.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.local_stack import (
        DependencyReport,
        DependencySpec,
        DependencyState,
        HostOs,
        HostRecipe,
    )


# ---------------------------------------------------------------------------
# Value object protocols
# ---------------------------------------------------------------------------
from typing import Protocol


@runtime_checkable
class HostRecipeInterface(Protocol):
    @property
    def package(self) -> PackageSpec: ...
    @property
    def service(self) -> ServiceSpec | None: ...
    @property
    def probe(self) -> ProbeSpec | None: ...
    @property
    def post_install(self) -> tuple[tuple[str, ...], ...]: ...
    @property
    def hint(self) -> str: ...


@runtime_checkable
class DependencySpecInterface(Protocol):
    @property
    def key(self) -> str: ...
    @property
    def title(self) -> str: ...
    @property
    def group(self) -> str: ...
    @property
    def default(self) -> bool: ...
    @property
    def installer(self) -> InstallerKind: ...
    @property
    def arch(self) -> HostRecipe | None: ...
    @property
    def macos(self) -> HostRecipe | None: ...
    @property
    def requires(self) -> tuple[str, ...]: ...
    @property
    def note(self) -> str: ...

    def recipe(self, host: HostOs | None) -> HostRecipe | None: ...


@runtime_checkable
class DependencyReportInterface(Protocol):
    @property
    def key(self) -> str: ...
    @property
    def state(self) -> DependencyState: ...
    @property
    def detail(self) -> str: ...
    @property
    def changed(self) -> bool: ...
    @property
    def fix(self) -> str: ...

    @property
    def ok(self) -> bool: ...


@runtime_checkable
class LocalStackReportInterface(Protocol):
    @property
    def host_label(self) -> str: ...
    @property
    def reports(self) -> tuple[DependencyReport, ...]: ...

    @property
    def ok(self) -> bool: ...
    @property
    def changed(self) -> bool: ...


# ---------------------------------------------------------------------------
# Catalogue protocol
# ---------------------------------------------------------------------------


@runtime_checkable
@runtime_checkable
class LocalStackCatalogueInterface(Protocol):
    def entries(self) -> tuple[DependencySpec, ...]: ...
    def keys(self) -> tuple[str, ...]: ...
    def groups(self) -> tuple[str, ...]: ...
    def get(self, key: str) -> DependencySpec: ...
    def resolve(
        self,
        host: HostOs | None,
        *,
        only: Iterable[str] = (),
        extra: Iterable[str] = (),
        exclude: Iterable[str] = (),
    ) -> tuple[DependencySpec, ...]: ...


# ---------------------------------------------------------------------------
# Re‑export concrete types for type‑checking context
# ---------------------------------------------------------------------------

# These imports are guarded by TYPE_CHECKING; they avoid circular imports at
# runtime, keeping the domain pure.
if TYPE_CHECKING:
    from vibey.domain.local_stack import (
        HostOs,
        InstallerKind,
        PackageSpec,
        ProbeSpec,
        ServiceSpec,
    )

__all__ = [
    "HostRecipeInterface",
    "DependencySpecInterface",
    "DependencyReportInterface",
    "LocalStackReportInterface",
    "LocalStackCatalogueInterface",
]
