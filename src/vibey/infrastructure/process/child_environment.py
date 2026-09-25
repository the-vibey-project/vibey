# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What a model-driven child process may see of the worker's environment.

Engine sessions and gate commands used to start from a copy of the worker's whole
environment with a few Python variables removed. `VIBEY_PG_URL` -- the queue and
ledger DSN -- went with it, into processes that run model-chosen shell commands
during unattended phases, where injected text can steer them. With the DSN a session
could UPDATE or DELETE queue rows directly, and nothing would record it.

A child's environment is now BUILT UP from an allow-list rather than cut down from a
copy: the system basics every process needs (`SYSTEM_ENVIRONMENT`), plus what the
caller declares for that child. A second rule sits under every allow-list and cannot
be configured away: vibey's own variables (and libpq's, which can carry the same
database without naming it) can never be put on one. A declaration that tries is
refused when the worker is built, rather than dropped silently.

Declared by `interfaces/child_environment_interface.py` (ADR-0016).
"""

import os
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from vibey.infrastructure.process.interfaces.child_environment_interface import (
    EnvironmentAllowListInterface,
    ForbiddenEnvironmentInterface,
)
from vibey.infrastructure.process.interfaces.python_env_interface import (
    OrchestratorPythonEnvInterface,
)
from vibey.infrastructure.process.python_env import OrchestratorPythonEnv

_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_PREFIX_BODY = re.compile(r"[A-Za-z0-9_]*")

# The variables that locate vibey's own Python environment. Stripped from every child
# unless the caller explicitly turns isolation off (`gates.isolate_python_env`, #212).
_PYTHON_ENV = ("VIRTUAL_ENV", "VIRTUAL_ENV_PROMPT", "PYTHONHOME", "PYTHONPATH")


@dataclass(frozen=True, slots=True)
class ForbiddenEnvironment:
    """Names no allow-list may admit, whatever it declares.

    `prefixes` forbid every name that starts with one; `markers` forbid every name that
    contains one. Declared by `interfaces/child_environment_interface.py`.
    """

    prefixes: tuple[str, ...] = ()
    markers: tuple[str, ...] = ()

    def forbids(self, name: str) -> bool:
        return name.startswith(self.prefixes) or any(marker in name for marker in self.markers)

    def forbids_prefix(self, prefix: str) -> bool:
        """Whether a declared prefix could admit a forbidden name: it lies under a
        forbidden prefix, it covers one (`VIB*`, `*`), or it carries a marker."""
        return (
            prefix.startswith(self.prefixes)
            or any(forbidden.startswith(prefix) for forbidden in self.prefixes)
            or any(marker in prefix for marker in self.markers)
        )


# vibey's own configuration and credentials (`VIBEY_PG_URL`, every `VIBEY_*_TOKEN`,
# `_PASSWORD` and `_URL`) and libpq's (`PGPASSWORD`, `PGHOST`, `PGSERVICEFILE`, ...),
# which reach the same database without ever naming a DSN. Git's plumbing too: a gate
# that inherits GIT_DIR from a hook operates on the wrong repository (#212).
GATE_FORBIDDEN = ForbiddenEnvironment(prefixes=("VIBEY_", "PG", "GIT_"))

# A model session additionally never receives anything shaped like a database
# credential, whoever declares it. A gate may be given its project's own test DSN; an
# engine session may not be given any.
MODEL_SESSION_FORBIDDEN = ForbiddenEnvironment(
    prefixes=("VIBEY_", "PG"), markers=("DSN", "DATABASE_URL", "PASSWORD", "PASSWD")
)


class EnvironmentAllowList:
    """The names and prefixes a child may receive, under a rule nothing can widen.

    An entry ending in `*` names a prefix (`CLAUDELOOP_*`); anything else is an exact
    name. Every entry is checked against `forbidden` on construction, so a list that
    could admit vibey's own DSN never exists. Declared by
    `interfaces/child_environment_interface.py`.
    """

    __slots__ = ("_forbidden", "_names", "_prefixes")

    def __init__(
        self,
        names: Iterable[str] = (),
        prefixes: Iterable[str] = (),
        *,
        forbidden: ForbiddenEnvironmentInterface = MODEL_SESSION_FORBIDDEN,
        where: str = "environment allow-list",
    ) -> None:
        self._names = tuple(dict.fromkeys(names))
        self._prefixes = tuple(dict.fromkeys(prefixes))
        self._forbidden = forbidden
        for name in self._names:
            if not _NAME.fullmatch(name):
                raise ValueError(f"{where}: {name!r} is not an environment variable name")
            if forbidden.forbids(name):
                raise ValueError(f"{where}: {name} can never be passed to a child process")
        for prefix in self._prefixes:
            if not _PREFIX_BODY.fullmatch(prefix):
                raise ValueError(f"{where}: {prefix + '*'!r} is not an environment variable name")
            if forbidden.forbids_prefix(prefix):
                raise ValueError(f"{where}: {prefix}* can never be passed to a child process")

    @classmethod
    def parse(
        cls,
        raw: object,
        *,
        where: str,
        forbidden: ForbiddenEnvironmentInterface = MODEL_SESSION_FORBIDDEN,
    ) -> "EnvironmentAllowList":
        """Read a config value: a list of names, each prefix ending in `*`."""
        if not isinstance(raw, list | tuple) or not all(isinstance(e, str) for e in raw):
            raise ValueError(f"{where} must be a list of strings")
        names, prefixes = cls._split(raw, where=where)
        return cls(names, prefixes, forbidden=forbidden, where=where)

    @staticmethod
    def _split(entries: Iterable[str], *, where: str) -> tuple[list[str], list[str]]:
        names: list[str] = []
        prefixes: list[str] = []
        for entry in entries:
            if entry.endswith("*"):
                prefixes.append(entry[:-1])
            elif "*" in entry:
                raise ValueError(f"{where}: {entry!r} is not an environment variable name")
            else:
                names.append(entry)
        return names, prefixes

    @property
    def names(self) -> frozenset[str]:
        return frozenset(self._names)

    @property
    def prefixes(self) -> tuple[str, ...]:
        return self._prefixes

    @property
    def forbidden(self) -> ForbiddenEnvironmentInterface:
        return self._forbidden

    def entries(self) -> tuple[str, ...]:
        """Every entry as it would be declared: names, then prefixes with their `*`."""
        return (*self._names, *(prefix + "*" for prefix in self._prefixes))

    def admits(self, name: str) -> bool:
        if self._forbidden.forbids(name):
            return False
        return name in self._names or name.startswith(self._prefixes)

    def extended(
        self,
        entries: Iterable[str],
        *,
        forbidden: ForbiddenEnvironmentInterface | None = None,
        where: str = "environment allow-list",
    ) -> "EnvironmentAllowList":
        """This list plus `entries`, all of it checked again under `forbidden` (this
        list's own rule when None) -- so narrowing the rule can never smuggle through an
        entry the narrower rule refuses."""
        names, prefixes = self._split(entries, where=where)
        return EnvironmentAllowList(
            (*self._names, *names),
            (*self._prefixes, *prefixes),
            forbidden=self._forbidden if forbidden is None else forbidden,
            where=where,
        )


# What every child needs to run at all, and nothing that carries a credential of its
# own: where to find programs and its home, who it runs as, its temp directory, locale
# and terminal, the certificate bundle and proxy the host reaches the network through,
# and the XDG directories tools keep their own configuration and caches in.
SYSTEM_ENVIRONMENT = EnvironmentAllowList(
    names=(
        "PATH",
        "HOME",
        "USER",
        "LOGNAME",
        "SHELL",
        "TMPDIR",
        "TMP",
        "TEMP",
        "LANG",
        "LANGUAGE",
        "TZ",
        "TERM",
        "COLORTERM",
        "NO_COLOR",
        "COLUMNS",
        "LINES",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
        "REQUESTS_CA_BUNDLE",
        "CURL_CA_BUNDLE",
        "NODE_EXTRA_CA_CERTS",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "NO_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "no_proxy",
        "all_proxy",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
        # macOS: the text encoding CoreFoundation-based CLIs (the keychain helper an
        # engine CLI reads its login through) expect to inherit.
        "__CF_USER_TEXT_ENCODING",
    ),
    prefixes=("LC_",),
)


class ChildEnvironment:
    """The one builder for a model-driven child process's environment.

    Reads the source (the live process environment by default) at `build()` time, keeps
    only what the allow-list admits, strips vibey's own Python environment from PATH
    unless told not to, and lays the caller's `overlay` over the result last. Declared
    by `interfaces/child_environment_interface.py`.
    """

    __slots__ = ("_allow", "_isolate_python_env", "_overlay", "_python_env", "_source")

    def __init__(
        self,
        allow: EnvironmentAllowListInterface,
        *,
        python_env: OrchestratorPythonEnvInterface | None = None,
        isolate_python_env: bool = True,
        overlay: Mapping[str, str] | None = None,
        source: Mapping[str, str] | None = None,
    ) -> None:
        self._allow = allow
        self._python_env = OrchestratorPythonEnv() if python_env is None else python_env
        self._isolate_python_env = isolate_python_env
        self._overlay = dict(overlay or {})
        # The overlay is vibey's own values (a local runner's endpoint), not passthrough -- but
        # the rule under the allow-list binds it too.
        for name in self._overlay:
            if allow.forbidden.forbids(name):
                raise ValueError(f"{name} can never be passed to a child process")
        self._source = source

    @property
    def allow_list(self) -> EnvironmentAllowListInterface:
        return self._allow

    def build(self) -> dict[str, str]:
        source = os.environ if self._source is None else self._source
        env = {name: value for name, value in source.items() if self._allow.admits(name)}
        if self._isolate_python_env:
            env = self.without_python_env(env, venv_prefixes=self._python_env.venv_prefixes())
        else:
            env.update({name: source[name] for name in _PYTHON_ENV if name in source})
        env.update(self._overlay)
        return env

    @staticmethod
    def without_python_env(
        env: Mapping[str, str], *, venv_prefixes: tuple[str | None, ...]
    ) -> dict[str, str]:
        """A copy of ``env`` with the orchestrator's Python environment removed.

        Engine sessions inheriting vibey's environment mutated it live, twice: with
        VIRTUAL_ENV set and vibey's .venv/bin first on PATH, a session's `pip install
        -e .` landed editable installs INSIDE vibey's own venv (shadowing modules for
        every later gate run and even downgrading vibey's dev tools), and its bare
        `pytest`/`python` resolved to vibey's interpreter.
        """
        isolated = dict(env)
        for key in _PYTHON_ENV:
            isolated.pop(key, None)
        prefixes = tuple(prefix for prefix in venv_prefixes if prefix)
        path = isolated.get("PATH")
        if prefixes and path:
            isolated["PATH"] = os.pathsep.join(
                part
                for part in path.split(os.pathsep)
                if not any(
                    part == prefix or part.startswith(prefix + os.sep) for prefix in prefixes
                )
            )
        return isolated
