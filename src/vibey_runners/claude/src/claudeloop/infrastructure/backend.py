# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Backend profiles, read from TOML and resolved against the process environment.

The decisions live in ``domain/backend.py``; this module does the three things
the domain may not: parse ``[profiles.<name>]`` tables out of config files, read
environment variables (``auth_token_env``, an ambient ``ANTHROPIC_BASE_URL``),
and read run meta back from ``.claudeloop/runs/`` to learn which backend a
session last ran against. See docs/guides/local-backend.md.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from claudeloop.domain.backend import DEFAULT_PROFILE_NAME, BackendIdentity, BackendProfile
from claudeloop.domain.errors import BackendProfileError
from claudeloop.domain.interfaces import (
    BackendIdentityInterface,
    BackendProfileInterface,
    BackendRuntimeInterface,
)
from claudeloop.infrastructure.rundir import RunDirectory, runs_root_for

_STR_KEYS = frozenset(
    {
        "base_url",
        "auth_token",
        "auth_token_env",
        "model_low",
        "model_medium",
        "model_high",
        "small_fast_model",
        "subagent_model",
        "cost_mode",
        "cli_path",
    }
)
_INT_KEYS = frozenset({"context_window", "max_output_tokens"})
_BOOL_KEYS = frozenset({"pass_effort", "disable_nonessential_traffic", "done_marker_fallback"})
_TABLE_KEYS = frozenset({"extra_env"})
_KNOWN_KEYS = _STR_KEYS | _INT_KEYS | _BOOL_KEYS | _TABLE_KEYS


class BackendProfileLoader:
    """Turns a config file's ``[profiles]`` table into validated BackendProfiles.

    Strict on purpose: an unknown key or a wrongly typed value is refused with the
    file it came from, because a profile silently ignoring ``base_url`` would send
    a run — and a paid key — to the wrong place.
    """

    def parse(self, table: object, *, source: str) -> Mapping[str, BackendProfileInterface]:
        if not isinstance(table, dict):
            raise BackendProfileError(f"[profiles] in {source} must be a table of tables")
        profiles: dict[str, BackendProfileInterface] = {}
        for name, body in table.items():
            profiles[str(name)] = self._profile(str(name), body, source=source)
        return profiles

    def select(
        self, profiles: Mapping[str, BackendProfileInterface], name: str | None
    ) -> BackendProfileInterface:
        key = (name or "").strip()
        if not key:
            return BackendProfile()
        if key in profiles:
            return profiles[key]
        if key == DEFAULT_PROFILE_NAME:
            return BackendProfile()
        known = ", ".join(sorted(profiles)) or "none are defined"
        raise BackendProfileError(
            f"unknown profile {key!r} (defined: {known}). Add a [profiles.{key}] table "
            "to claudeloop.toml or ~/.config/claudeloop/config.toml."
        )

    def _profile(self, name: str, body: object, *, source: str) -> BackendProfile:
        where = f"[profiles.{name}] in {source}"
        if not isinstance(body, dict):
            raise BackendProfileError(f"{where} must be a table")
        kwargs: dict[str, Any] = {"name": name}
        for key, value in body.items():
            if key not in _KNOWN_KEYS:
                raise BackendProfileError(
                    f"{where}: unknown key {key!r}; known keys are {', '.join(sorted(_KNOWN_KEYS))}"
                )
            kwargs[key] = self._value(key, value, where=where)
        try:
            return BackendProfile(**kwargs)
        except BackendProfileError as exc:
            raise BackendProfileError(f"{exc} (in {source})") from exc

    def _value(self, key: str, value: object, *, where: str) -> object:
        if key in _STR_KEYS:
            if not isinstance(value, str):
                raise BackendProfileError(f"{where}: {key} must be a string, got {value!r}")
            return value
        if key in _INT_KEYS:
            if isinstance(value, bool) or not isinstance(value, int):
                raise BackendProfileError(f"{where}: {key} must be an integer, got {value!r}")
            return value
        if key in _BOOL_KEYS:
            if not isinstance(value, bool):
                raise BackendProfileError(f"{where}: {key} must be true or false, got {value!r}")
            return value
        return self._extra_env(value, where=where)

    def _extra_env(self, value: object, *, where: str) -> tuple[tuple[str, str], ...]:
        if not isinstance(value, dict):
            raise BackendProfileError(f"{where}: extra_env must be a table of NAME = value")
        pairs: list[tuple[str, str]] = []
        for env_name, env_value in value.items():
            if isinstance(env_value, bool) or not isinstance(env_value, (str, int)):
                raise BackendProfileError(
                    f"{where}: extra_env.{env_name} must be a string or integer, got {env_value!r}"
                )
            pairs.append((str(env_name), str(env_value)))
        return tuple(pairs)


class BackendEnvironmentResolver:
    """Resolves a profile against the process environment: the token a local
    profile sends, and the identity recorded for resume safety."""

    def __init__(self, environ: Mapping[str, str] | None = None) -> None:
        self._environ: Mapping[str, str] = os.environ if environ is None else environ

    def auth_token(self, profile: BackendProfileInterface) -> str:
        if not profile.is_local:
            return ""
        if profile.auth_token_env:
            value = self._environ.get(profile.auth_token_env, "")
            if not value.strip():
                raise BackendProfileError(
                    f"profile {profile.name!r} reads its token from "
                    f"${profile.auth_token_env}, which is unset or empty"
                )
            return value
        return profile.auth_token

    def try_auth_token(self, profile: BackendProfileInterface) -> str | None:
        try:
            return self.auth_token(profile)
        except BackendProfileError:
            return None

    def runtime(self, profile: BackendProfileInterface) -> BackendRuntimeInterface:
        return profile.runtime(auth_token=self.auth_token(profile))

    def identity(self, profile: BackendProfileInterface) -> BackendIdentityInterface:
        return profile.identity(ambient_base_url=self._environ.get("ANTHROPIC_BASE_URL", ""))


class RunBackendHistory:
    """Which backend a Claude session last ran against, read back from the run
    meta every run records (``meta.json`` → ``backend``)."""

    def __init__(self, cwd: Path) -> None:
        self._root = runs_root_for(cwd)

    def last_backend(self, session_id: str) -> BackendIdentityInterface | None:
        if not self._root.is_dir():
            return None
        recorded: list[tuple[str, str]] = []
        for path in self._root.iterdir():
            meta_path = path / "meta.json"
            if not meta_path.is_file():
                continue
            try:
                meta = RunDirectory(path).read_meta()
            except (OSError, ValueError, KeyError, TypeError):
                # A run directory being written right now, or one a crash left
                # half-written, says nothing about the backend; it is not a
                # reason to refuse or to allow.
                continue
            if meta.session_id == session_id and meta.backend:
                recorded.append((meta.started_at, meta.backend))
        if not recorded:
            return None
        _started_at, backend = max(recorded)
        return BackendIdentity.parse(backend)
