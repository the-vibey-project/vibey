# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Domain model for the local dependency configuration used by the installer.

This module declares the pure data structures that represent packages, services,
probes, recipes and the overall catalogue of installable services for an
operating system.  All types are frozen dataclasses with ``slots`` for
memory efficiency and to help type‑checkers.

The catalogue is intentionally small: it currently contains the three core
entries required for the installer.

The code is pure – it contains no I/O, no async, no reliance on external
services, and follows the same constraints as the rest of ``vibey.domain``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class HostOs(StrEnum):
    ARCH = "arch"
    MACOS = "macos"


class PackageSource(StrEnum):
    PACMAN = "pacman"
    AUR = "aur"
    BREW_FORMULA = "brew-formula"
    BREW_CASK = "brew-cask"
    NONE = "none"


class ServiceManager(StrEnum):
    SYSTEMD = "systemd"
    BREW_SERVICES = "brew-services"
    MACOS_APP = "macos-app"


class InstallerKind(StrEnum):
    PACKAGE = "package"
    POSTGRES = "postgres"
    MODEL = "model"


class DependencyState(StrEnum):
    READY = "ready"
    MISSING = "missing"
    STOPPED = "stopped"
    FAILED = "failed"
    SKIPPED = "skipped"
    UNSUPPORTED = "unsupported"


# ---------------------------------------------------------------------------
# Spec data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PackageSpec:
    source: PackageSource
    names: tuple[str, ...] = ()
    binaries: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ServiceSpec:
    manager: ServiceManager
    name: str


@dataclass(frozen=True, slots=True)
class ProbeSpec:
    argv: tuple[str, ...]
    privileged: bool = False
    timeout_seconds: float = 120.0
    timeout_hint: str = ""


@dataclass(frozen=True, slots=True)
class HostRecipe:
    package: PackageSpec
    service: ServiceSpec | None = None
    probe: ProbeSpec | None = None
    post_install: tuple[tuple[str, ...], ...] = ()
    hint: str = ""


@dataclass(frozen=True, slots=True)
class DependencySpec:
    key: str
    title: str
    group: str
    default: bool
    installer: InstallerKind
    arch: HostRecipe | None = None
    macos: HostRecipe | None = None
    requires: tuple[str, ...] = ()
    note: str = ""

    def recipe(self, host: HostOs | None) -> HostRecipe | None:
        if host is None:
            return None
        if host == HostOs.ARCH:
            return self.arch
        return self.macos


@dataclass(frozen=True, slots=True)
class DependencyReport:
    key: str
    state: DependencyState
    detail: str
    changed: bool = False
    fix: str = ""

    @property
    def ok(self) -> bool:
        return self.state == DependencyState.READY


@dataclass(frozen=True, slots=True)
class LocalStackReport:
    host_label: str
    reports: tuple[DependencyReport, ...]

    @property
    def ok(self) -> bool:
        return all(r.ok for r in self.reports)

    @property
    def changed(self) -> bool:
        return any(r.changed for r in self.reports)


class UnknownDependency(ValueError):
    pass


# ---------------------------------------------------------------------------
# Default catalogue entries
# ---------------------------------------------------------------------------

DEFAULT_LOCAL_MODEL: Final = "gpt-oss:20b"
DEFAULT_LOCAL_MODEL_DOWNLOAD: Final = "14 GB"

# Common hint for PostgreSQL, used in both recipes.
_POSTGRES_HINT = "export VIBEY_PG_URL=postgresql://$USER@localhost:5432/vibey"


_PACKAGE_POSTGRES_ARCH = PackageSpec(PackageSource.PACMAN, ("postgresql",), ("pg_isready",))
_PACKAGE_POSTGRES_MACOS = PackageSpec(PackageSource.BREW_FORMULA, ("postgresql@17",), ())

_POSTGRES_ARCH_RECIPE = HostRecipe(_PACKAGE_POSTGRES_ARCH, hint=_POSTGRES_HINT)
_POSTGRES_MACOS_RECIPE = HostRecipe(_PACKAGE_POSTGRES_MACOS, hint=_POSTGRES_HINT)

_CATALOGUE_ENTRIES: tuple[DependencySpec, ...] = (
    DependencySpec(
        key="postgres",
        title="PostgreSQL",
        group="services",
        default=True,
        installer=InstallerKind.POSTGRES,
        arch=_POSTGRES_ARCH_RECIPE,
        macos=_POSTGRES_MACOS_RECIPE,
        note="Homebrew is pinned to 17, the major the chart (deploy/helm/vibey/values.yaml:53) and CI run. Arch's repositories carry only the current major (18.6 on 2026-09-22), which vibey supports (14+).",
    ),
    DependencySpec(
        key="ollama",
        title="Ollama",
        group="services",
        default=True,
        installer=InstallerKind.PACKAGE,
        arch=HostRecipe(
            PackageSpec(PackageSource.PACMAN, ("ollama",), ("ollama",)),
            ServiceSpec(ServiceManager.SYSTEMD, "ollama"),
            ProbeSpec(("ollama", "list"), timeout_seconds=60.0),
        ),
        macos=HostRecipe(
            PackageSpec(PackageSource.BREW_FORMULA, ("ollama",), ("ollama",)),
            ServiceSpec(ServiceManager.BREW_SERVICES, "ollama"),
            ProbeSpec(("ollama", "list"), timeout_seconds=60.0),
        ),
    ),
    DependencySpec(
        key="model",
        title=f"local model {DEFAULT_LOCAL_MODEL}",
        group="services",
        default=True,
        installer=InstallerKind.MODEL,
        arch=HostRecipe(PackageSpec(PackageSource.NONE)),
        macos=HostRecipe(PackageSpec(PackageSource.NONE)),
        requires=("ollama",),
    ),
)


# ---------------------------------------------------------------------------
# Catalogue implementation
# ---------------------------------------------------------------------------


class LocalStackCatalogue:
    def __init__(self, entries: tuple[DependencySpec, ...] = _CATALOGUE_ENTRIES):
        self._entries: tuple[DependencySpec, ...] = entries
        self._key_index: Mapping[str, int] = {}
        self._group_index: Mapping[str, int] = {}
        for i, entry in enumerate(entries):
            if entry.key in self._key_index:
                raise ValueError(f"duplicate key '{entry.key}' in catalogue")
            self._key_index[entry.key] = i
            if entry.group not in self._group_index:
                self._group_index[entry.group] = i
            # forward requires check
            for req in entry.requires:
                if req not in self._key_index or self._key_index[req] > i:
                    raise ValueError(f"{entry.key} requires unknown or forward dependency '{req}'")

    def entries(self) -> tuple[DependencySpec, ...]:
        return self._entries

    def keys(self) -> tuple[str, ...]:
        return tuple(e.key for e in self._entries)

    def groups(self) -> tuple[str, ...]:
        seen: set[str] = set()
        result: list[str] = []
        for e in self._entries:
            if e.group not in seen:
                seen.add(e.group)
                result.append(e.group)
        return tuple(result)

    def get(self, key: str) -> DependencySpec:
        if key not in self._key_index:
            known = ", ".join(self.keys()) + ", " + ", ".join(self.groups())
            raise UnknownDependency(f"unknown dependency or group '{key}'; known: {known}")
        return self._entries[self._key_index[key]]

    def _expand_name(self, name: str, acc: set[str], host: HostOs | None) -> None:
        if name in self._group_index:
            # expand group
            for e in self._entries:
                if e.group == name:
                    acc.add(e.key)
        elif name in self._key_index:
            acc.add(name)
        else:
            known = ", ".join(self.keys()) + ", " + ", ".join(self.groups())
            raise UnknownDependency(f"unknown dependency or group '{name}'; known: {known}")

    def resolve(
        self,
        host: HostOs | None,
        *,
        only: Iterable[str] = (),
        extra: Iterable[str] = (),
        exclude: Iterable[str] = (),
    ) -> tuple[DependencySpec, ...]:
        only_set: set[str] = set()
        for n in only:
            self._expand_name(n, only_set, host)
        if only_set:
            starting = only_set
        else:
            starting = {e.key for e in self._entries if e.default and e.recipe(host) is not None}
        # add extras
        for n in extra:
            self._expand_name(n, starting, host)

        # add requires transitively
        def add_requires(key: str) -> None:
            for req in self._entries[self._key_index[key]].requires:
                if req not in starting:
                    starting.add(req)
                    add_requires(req)

        for k in list(starting):
            add_requires(k)
        # apply excludes
        exclude_set: set[str] = set()
        for n in exclude:
            self._expand_name(n, exclude_set, host)
        final_keys = starting - exclude_set
        # preserve order
        return tuple(e for e in self._entries if e.key in final_keys)


# Expose the default catalogue variable
CATALOGUE_ENTRIES: Final[tuple[DependencySpec, ...]] = _CATALOGUE_ENTRIES
