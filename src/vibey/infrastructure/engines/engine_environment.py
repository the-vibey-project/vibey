# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What an engine session may see of the worker's environment, per engine.

An engine session runs model-chosen shell commands -- unattended in BUILD and
DEPLOY_EXECUTE -- so its environment is the boundary between the model and whatever
the worker holds. It is built from an allow-list, never copied:

1. the system basics every process needs (`SYSTEM_ENVIRONMENT`);
2. the engine's own declared variables (`EngineDescriptor.env_passthrough`) and its
   own API credential (`EngineDescriptor.auth_env`);
3. whatever the project's stored config record declares under `engine_environment`:
   `allow` for every engine, `engines.<engine id>` for one.

Under all three sits `MODEL_SESSION_FORBIDDEN`: vibey's own variables (the queue and
ledger DSN among them), libpq's, and anything shaped like a database credential can
never be put on the list -- a declaration that tries is refused when the worker is
built. A GitHub token or a cloud credential is not forbidden, but it is on no default
list either: it reaches only the engine a project declares it for.

Declared by `interfaces/engine_environment_interface.py` (ADR-0016).
"""

from collections.abc import Mapping, Sequence
from dataclasses import replace

from vibey.application.interfaces import EngineAdapter
from vibey.domain.engine import EngineDescriptor, EngineId
from vibey.infrastructure.process import (
    MODEL_SESSION_FORBIDDEN,
    SYSTEM_ENVIRONMENT,
    ChildEnvironment,
    EnvironmentAllowList,
)
from vibey.infrastructure.process.interfaces import OrchestratorPythonEnvInterface

_KEY = "engine_environment"
_KNOWN_KEYS = frozenset({"allow", "engines"})


class EngineEnvironmentPolicy:
    """The engine-session allow-list: defaults, plus what the project declares.

    Declared by `interfaces/engine_environment_interface.py`.
    """

    __slots__ = ("_allow", "_per_engine")

    def __init__(
        self,
        *,
        allow: Sequence[str] = (),
        per_engine: Mapping[EngineId, Sequence[str]] | None = None,
    ) -> None:
        self._allow = tuple(allow)
        self._per_engine = {
            engine: tuple(entries) for engine, entries in (per_engine or {}).items()
        }
        # Checked now, so a forbidden declaration fails when the worker is built rather
        # than on the first session that would have received it.
        EnvironmentAllowList.parse(
            list(self._allow), where=f"{_KEY}.allow", forbidden=MODEL_SESSION_FORBIDDEN
        )
        for engine, entries in self._per_engine.items():
            EnvironmentAllowList.parse(
                list(entries),
                where=f"{_KEY}.engines.{engine.value}",
                forbidden=MODEL_SESSION_FORBIDDEN,
            )

    @classmethod
    def from_config(cls, config: Mapping[str, object]) -> "EngineEnvironmentPolicy":
        """Read the project's stored config record's `engine_environment` object.

        Read off the record the way `gates`, `review` and `skills_context` are; unset
        means the defaults. Anything malformed or forbidden raises, naming the key.
        """
        raw = config.get(_KEY)
        if raw is None:
            return cls()
        if not isinstance(raw, Mapping):
            raise ValueError(f"{_KEY} project config must be an object")
        unknown = sorted(set(raw) - _KNOWN_KEYS)
        if unknown:
            raise ValueError(f"{_KEY}: unknown key {unknown[0]!r}")
        allow = cls._entries(raw.get("allow", []), where=f"{_KEY}.allow")
        engines = raw.get("engines", {})
        if not isinstance(engines, Mapping):
            raise ValueError(f"{_KEY}.engines must be an object")
        per_engine: dict[EngineId, tuple[str, ...]] = {}
        for name, entries in engines.items():
            try:
                engine = EngineId(name)
            except ValueError:
                raise ValueError(f"{_KEY}.engines: unknown engine {name!r}") from None
            per_engine[engine] = cls._entries(entries, where=f"{_KEY}.engines.{name}")
        return cls(allow=allow, per_engine=per_engine)

    @staticmethod
    def _entries(raw: object, *, where: str) -> tuple[str, ...]:
        # parse() validates shape and the forbidden rule; the entries themselves are
        # kept as declared so the policy can be rebuilt per descriptor.
        return EnvironmentAllowList.parse(
            raw, where=where, forbidden=MODEL_SESSION_FORBIDDEN
        ).entries()

    def allow_list(self, descriptor: EngineDescriptor) -> EnvironmentAllowList:
        """Exactly what a `descriptor` session may receive."""
        return SYSTEM_ENVIRONMENT.extended(
            (
                *descriptor.auth_env,
                *descriptor.env_passthrough,
                *self._allow,
                *self._per_engine.get(descriptor.engine_id, ()),
            ),
            forbidden=MODEL_SESSION_FORBIDDEN,
            where=f"{descriptor.engine_id.value} session environment",
        )

    def environment(
        self,
        descriptor: EngineDescriptor,
        *,
        overlay: Mapping[str, str] | None = None,
        python_env: OrchestratorPythonEnvInterface | None = None,
        source: Mapping[str, str] | None = None,
    ) -> ChildEnvironment:
        """The builder every spawn of a `descriptor` session goes through."""
        return ChildEnvironment(
            self.allow_list(descriptor), python_env=python_env, overlay=overlay, source=source
        )

    def applied_to(self, adapter: EngineAdapter) -> EngineAdapter:
        """`adapter` running under this policy, when it spawns loop processes; any other
        adapter (the faked harness's scripted engines) is returned unchanged."""
        # Imported here: the adapter module imports this one for its default policy.
        from vibey.infrastructure.engines.loop_process_adapter import LoopProcessAdapter

        if isinstance(adapter, LoopProcessAdapter):
            return replace(adapter, environment=self)
        return adapter
