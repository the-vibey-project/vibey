# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Chooses the forge adapter a repository's `[platform]` table names (#138).

The one place a platform is named by kind. It maps each `ForgeKind` that has an adapter to
the code that builds one, and hands the result back as a `ForgeAdapterInterface`, so the
modules that ask about the forge stay forge-neutral.

GitHub is the only adapter today. `[platform] kind = "gitlab"` or `"forgejo"` is already
refused when the configuration loads, because every other command in this package still
speaks to GitHub directly and would do the wrong thing quietly. The selector refuses too,
for any kind it has no adapter for, so a configuration that reached it by some other road
fails with the same sentence instead of getting an adapter for the wrong forge.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from types import MappingProxyType

from vibey_gh.config import GhConfig, PlatformConfig
from vibey_gh.forge import ForgeKind
from vibey_gh.forge_github import GH_DEFAULT_HOST, GitHubForge
from vibey_gh.gh_transport import GhTransport
from vibey_gh.interfaces.forge_adapter_interface import ForgeAdapterInterface
from vibey_gh.interfaces.forge_selector_interface import ForgeSelectorInterface

# Builds one adapter from a repository's configuration. A callable rather than a class,
# so a test can register a double for a kind without subclassing anything.
AdapterFactory = Callable[[GhConfig], ForgeAdapterInterface]


class ForgeSelector(ForgeSelectorInterface):
    """Maps `[platform] kind` to the adapter that speaks to that forge."""

    def __init__(self, adapters: Mapping[ForgeKind, AdapterFactory] | None = None) -> None:
        self._adapters: Mapping[ForgeKind, AdapterFactory] = MappingProxyType(
            dict(adapters) if adapters is not None else {ForgeKind.GITHUB: self._github}
        )

    @property
    def kinds(self) -> frozenset[ForgeKind]:
        """The kinds this selector can build an adapter for."""
        return frozenset(self._adapters)

    def select(self, cfg: GhConfig) -> ForgeAdapterInterface:
        factory = self._adapters.get(ForgeKind(cfg.platform.kind))
        if factory is None:
            raise ValueError(PlatformConfig.not_adapted(cfg.platform.kind))
        return factory(cfg)

    @staticmethod
    def _github(cfg: GhConfig) -> ForgeAdapterInterface:
        # `gh`'s own default host is left unexported, so a repository on github.com runs
        # `gh` with the environment it always had; any other host pins `gh` to it.
        host = cfg.platform.host
        transport = GhTransport(host=None if host == GH_DEFAULT_HOST else host)
        return GitHubForge(root=cfg.root, transport=transport)
