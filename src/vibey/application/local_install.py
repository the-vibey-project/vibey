# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Orchestrator that installs all dependencies in a declared order.

This module uses the protocols defined in :mod:`vibey.application.interfaces.local_install`.
The logic is deliberately pure – it takes installers and specs but performs
no I/O. The factories that provide concrete installers live in infrastructure.
"""

from __future__ import annotations

from collections.abc import Mapping

from vibey.application.interfaces.local_install import (
    DependencyInstaller,
    LocalStackInstallerInterface,
)
from vibey.domain.local_stack import (
    DependencyReport,
    DependencySpec,
    DependencyState,
    LocalStackReport,
)


class LocalStackInstaller(LocalStackInstallerInterface):
    """Concrete implementation of :class:`LocalStackInstallerInterface`.

    Parameters
    ----------
    specs:
        The list of :class:`DependencySpec` in the order the installer is
        requested to run.
    installers:
        Mapping from dependency key to a concrete :class:`DependencyInstaller`.
    host_label:
        Label representing the host OS (e.g. ``"arch"`` or ``"macos"``).
    """

    def __init__(
        self,
        specs: tuple[DependencySpec, ...],
        installers: Mapping[str, DependencyInstaller],
        *,
        host_label: str,
    ) -> None:
        missing = [s.key for s in specs if s.key not in installers]
        if missing:
            raise ValueError(f"Missing installers for: {', '.join(missing)}")
        self._specs = specs
        self._installers = installers
        self._host_label = host_label
        self._run_keys = {s.key for s in specs}

    # ------------------------------------------------------------------
    # Protocol implementations
    # ------------------------------------------------------------------
    def check(self) -> LocalStackReport:  # pragma: no cover - exercised via tests
        reports = tuple(self._installers[s.key].check() for s in self._specs)
        return LocalStackReport(host_label=self._host_label, reports=reports)

    def install(self) -> LocalStackReport:
        results: list[DependencyReport] = []
        known_ok: dict[str, bool] = {}
        for spec in self._specs:
            # Determine whether any required dependency in this run failed.
            skip_reason: str | None = None
            for req in spec.requires:
                # A previous install exists for this required key.
                if req in self._run_keys and not known_ok.get(req, False):
                    skip_reason = req
                    break
            if skip_reason:
                # Skip without invoking the installer.
                report = DependencyReport(
                    key=spec.key,
                    state=DependencyState.SKIPPED,
                    detail=f"skipped: {skip_reason} is not ready",
                    changed=False,
                    fix=f"vibey install --only {skip_reason}",
                )
                known_ok[spec.key] = False
            else:
                report = self._installers[spec.key].install()
                known_ok[spec.key] = report.ok
            results.append(report)
        return LocalStackReport(host_label=self._host_label, reports=tuple(results))


# The factory implementation is provided by infrastructure; this file defines
# only the interface contract and a concrete orchestrator.

"""End of file"""
