# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey-gh check --ci`: do the live repository settings say what `[repository_profile]` says?

`repository-profile.yml` PATCHes the declared settings into the forge and verifies them in the
same run. That is a write followed by a check, not an audit: a setting somebody changed by hand
is silently overwritten on the next release, and nothing ever said it had drifted. This only
reads and compares, never writes.

Drift is every declared setting whose live value differs: the flags, the squash-commit title
and message when declared, the description and the topic set. The list of settings is the
declaration's own (`RepositoryProfileConfig.settings()`), the one the writer sends, so the
writer and the auditor cannot disagree about what is managed.

A value the forge did not show this token is *not surveyed*, never matching. A read that could
not be made at all (no `gh`, no token, another forge) is a waiver that says so out loud.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any

from vibey_gh import github_state
from vibey_gh.config import GhConfig
from vibey_gh.gh_transport import GhTransport
from vibey_gh.interfaces.gh_transport_interface import GhTransportInterface
from vibey_gh.interfaces.profile_drift_interface import ProfileDriftInterface

__all__ = ["ProfileDrift"]

# What `repository-profile.yml` writes when `description` is declared empty. The auditor
# reads the same sentence, or an adopter with no description would read as permanently drifted.
DESCRIPTION_FALLBACK = "{name} — automated delivery, release provenance, and living documentation."
# Two settings the repository object does not carry: each has its own endpoint, where the
# forge answers 204 for on and 404 for off.
SECURITY_ENDPOINTS = {
    "vulnerability_alerts": "vulnerability-alerts",
    "automated_security_fixes": "automated-security-fixes",
}


class ProfileDrift(ProfileDriftInterface):
    """Implements `ProfileDriftInterface`."""

    def __init__(
        self,
        *,
        transport: GhTransportInterface | None = None,
        repository: Callable[[], str] = github_state.repository,
    ) -> None:
        self._transport: GhTransportInterface = transport or GhTransport()
        self._repository = repository

    def survey(self, cfg: GhConfig) -> tuple[tuple[str, ...], tuple[str, ...]]:
        if not cfg.repository_profile.enabled:
            return (), ()
        if cfg.platform.kind != "github":
            return (), (
                f"repository settings are read from GitHub only (forge {cfg.platform.kind})",
            )
        try:
            repository = self._repository()
        except (RuntimeError, FileNotFoundError, ValueError) as exc:
            return (), (f"the repository could not be identified: {exc}",)
        return self.compare(cfg, self.fetch(repository))

    def fetch(self, repository: str) -> dict[str, Any]:
        """The live settings keyed like the declaration. What could not be read is named in
        `_unread` (key to reason); `*` means nothing could be."""
        live: dict[str, Any] = {}
        unread: dict[str, str] = {}
        live["_unread"] = unread
        try:
            repo_run = self._transport.run(["api", f"repos/{repository}"])
        except FileNotFoundError:
            unread["*"] = f"the GitHub CLI (`{self._transport.executable}`) is not installed"
            return live
        if repo_run.returncode:
            unread["*"] = f"repository settings could not be read: {self._detail(repo_run)}"
            return live
        try:
            live.update(self._decode(repo_run.stdout))
        except (TypeError, ValueError) as exc:
            unread["*"] = f"repository settings could not be read: {exc}"
            return live
        topics = self._transport.run(["api", f"repos/{repository}/topics"])
        if topics.returncode:
            unread["topics"] = self._detail(topics)
        else:
            try:
                live["topics"] = list(self._decode(topics.stdout).get("names") or [])
            except (TypeError, ValueError) as exc:
                unread["topics"] = str(exc)
        for name, endpoint in SECURITY_ENDPOINTS.items():
            run = self._transport.run(["api", f"repos/{repository}/{endpoint}"])
            if run.returncode == 0:
                live[name] = True
            elif "404" in (run.stderr or ""):
                live[name] = False
            else:
                unread[name] = self._detail(run)
        return live

    @staticmethod
    def _decode(text: str) -> dict[str, Any]:
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("the answer is not JSON") from exc
        if not isinstance(value, dict):
            raise TypeError("the answer is not an object")
        return value

    @staticmethod
    def _detail(run: Any) -> str:
        lines = (run.stderr or run.stdout or "").strip().splitlines()
        return lines[-1] if lines else "no output"

    def compare(
        self, cfg: GhConfig, live: Mapping[str, Any]
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        profile = cfg.repository_profile
        if not profile.enabled:
            return (), ()
        unread: Mapping[str, str] = live.get("_unread") or {}
        if "*" in unread:
            return (), (unread["*"],)
        drift: list[str] = []
        unsurveyed: list[str] = []

        def missing(key: str) -> None:
            reason = unread.get(key)
            unsurveyed.append(
                f"{key} could not be read: {reason}"
                if reason
                else f"{key} was withheld from this token"
            )

        for name, declared in profile.settings().items():
            if name not in live:
                missing(name)
            elif live[name] != declared:
                drift.append(f"{name} is {live[name]!r}, declared {declared!r}")
        expected = profile.description or DESCRIPTION_FALLBACK.format(
            name=str(live.get("name", ""))
        )
        if "description" not in live:
            missing("description")
        elif (live["description"] or "") != expected:
            drift.append(f"description is {live['description']!r}, declared {expected!r}")
        if "topics" not in live:
            missing("topics")
        elif sorted(live["topics"]) != sorted(profile.topics):
            drift.append(
                f"topics are {', '.join(sorted(live['topics'])) or 'none'}, "
                f"declared {', '.join(sorted(profile.topics)) or 'none'}"
            )
        return tuple(drift), tuple(unsurveyed)
