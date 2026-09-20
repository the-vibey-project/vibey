# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Chooses the forge adapter a repository's `[platform]` table names (#138).

The one place a platform is named by kind. It maps each `ForgeKind` that has an adapter to
the code that builds one, and hands the result back as a `ForgeAdapterInterface`, so the
modules that ask about the forge stay forge-neutral.

The selector refuses any kind it has no adapter for, so a configuration that reached it by
some other road fails with the same sentence instead of getting an adapter for the wrong forge.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable, Mapping
from types import MappingProxyType
from urllib.parse import urlsplit

from vibey_gh.config import ADAPTED_PLATFORM_KINDS, GhConfig, PlatformConfig
from vibey_gh.forge import ForgeKind
from vibey_gh.forge_forgejo import ForgejoForge
from vibey_gh.forge_github import GH_DEFAULT_HOST, GitHubForge
from vibey_gh.forge_gitlab import GitLabForge
from vibey_gh.forgejo_transport import ForgejoTransport
from vibey_gh.gh_transport import GhTransport
from vibey_gh.gitlab_transport import GitLabTransport
from vibey_gh.interfaces.forge_adapter_interface import ForgeAdapterInterface
from vibey_gh.interfaces.forge_selector_interface import ForgeSelectorInterface

# Builds one adapter from a repository's configuration. A callable rather than a class,
# so a test can register a double for a kind without subclassing anything.
AdapterFactory = Callable[[GhConfig], ForgeAdapterInterface]


class ForgeSelector(ForgeSelectorInterface):
    """Maps `[platform] kind` to the adapter that speaks to that forge."""

    def __init__(self, adapters: Mapping[ForgeKind, AdapterFactory] | None = None) -> None:
        self._adapters: Mapping[ForgeKind, AdapterFactory] = MappingProxyType(
            dict(adapters)
            if adapters is not None
            else {
                ForgeKind.GITHUB: self._github,
                **{
                    ForgeKind(kind): factory
                    for kind, factory in (
                        (ForgeKind.GITLAB.value, self._gitlab),
                        (ForgeKind.FORGEJO.value, self._forgejo),
                    )
                    if kind in ADAPTED_PLATFORM_KINDS
                },
            }
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
        host = cfg.platform.host
        transport = GhTransport(host=None if host == GH_DEFAULT_HOST else host)
        return GitHubForge(root=cfg.root, repository=_repository(cfg), transport=transport)

    @staticmethod
    def _gitlab(cfg: GhConfig) -> ForgeAdapterInterface:
        transport = GitLabTransport(
            host=cfg.platform.host,
            token=os.environ.get(cfg.platform.token_env, "") if cfg.platform.token_env else "",
        )
        return GitLabForge(root=cfg.root, repository=_repository(cfg), transport=transport)

    @staticmethod
    def _forgejo(cfg: GhConfig) -> ForgeAdapterInterface:
        transport = ForgejoTransport(
            host=cfg.platform.host,
            token=os.environ.get(cfg.platform.token_env, "") if cfg.platform.token_env else "",
        )
        return ForgejoForge(root=cfg.root, repository=_repository(cfg), transport=transport)


def _repository(cfg: GhConfig) -> str:
    """Bind an adapter to configured repository identity or the local origin URL."""
    if cfg.platform.repository:
        return cfg.platform.repository
    result = subprocess.run(
        ["git", "config", "--get", "remote.origin.url"],
        cwd=cfg.root,
        capture_output=True,
        text=True,
        check=False,
    )
    remote = result.stdout.strip().removesuffix(".git")
    if not remote:
        return ""
    if "://" in remote:
        path = urlsplit(remote).path
    else:
        path = remote.rsplit(":", 1)[-1]
    return path.strip("/")
