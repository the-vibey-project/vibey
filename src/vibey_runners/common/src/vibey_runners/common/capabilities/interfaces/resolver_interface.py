# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam over turning a bundle into a run's snapshot (SP-LOOPS Task 6)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable

from vibey_runners.common.capabilities.interfaces.bundle_interface import BundleSpecInterface
from vibey_runners.common.capabilities.lock_entry import LockEntry
from vibey_runners.common.capabilities.snapshot import CapabilitySnapshot


@runtime_checkable
class CapabilityResolverInterface(Protocol):
    def resolve(
        self, bundle: BundleSpecInterface, lock: Sequence[LockEntry], roots: Mapping[str, Path]
    ) -> CapabilitySnapshot:
        """The snapshot of `bundle` for one run. `lock` is what the person's lock file holds (a
        missing file is no entries): read it from the same file the resolver was built with,
        which is where the shipped marketplace writes its own entry; `roots` maps each marketplace name to its folder on disk, an
        absolute path from the person's own folders -- never a project's, and never the
        bundle's `source`. Only the marketplaces the enabled plugins come from are read. Raises
        `UnlockedMarketplaceError` for a person-added marketplace with no lock entry,
        `LockMismatchError` when a marketplace's tree, or the run's copy of it, is not what was
        locked, and `CapabilityResolutionError` for anything else that stops the run; on any
        failure no snapshot folder is left behind."""
        ...
