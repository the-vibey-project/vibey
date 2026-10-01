# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Which human gates may resolve to their own default after waiting, and when.

A gate stores a default answer and nothing ever applied it, so a parked job waited for a
person forever. Applying it everywhere would make silence consent, which sub-doctrine 12.d
forbids -- and some defaults act for the operator: `deploy_demo_review` defaults to
`approve`. So the operator's ruling (2026-09-30) is per-gate opt-in: a project names, under
`[human_gates] timeout_defaults`, each gate kind that may resolve to its default and how
many minutes it waits first. The declaration is the consent; an undeclared kind waits for a
person, however long, and is still reminded about.

Only a kind whose default this module can turn into the answer its handler reads may be
declared. Naming any other -- `approval`, which carries no default, or a kind vibey does not
raise -- is refused when the table is read, never ignored.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import timedelta
from types import MappingProxyType

from vibey.domain.config import ConfigError

TABLE = "human_gates"
KEY = "timeout_defaults"

DEFAULT_ANSWER_KEYS: Mapping[str, str] = MappingProxyType(
    {
        # The deployment opt-in after REVIEW; its handler reads {"choice": ...}.
        "choice": "choice",
        "deploy_interview": "choice",
        "deploy_failure_triage": "choice",
        # Its handler reads "verdict" or "choice"; `vibey answer` sends --choice.
        "deploy_acceptance": "choice",
        # Read as {"verdict": ...}.
        "deploy_demo_review": "verdict",
    }
)
"""Every gate kind that may time out to its default, and the key its handler reads the
answer under. `tests/cli/test_gate_answers.py` keeps it agreeing with `vibey answer`."""


@dataclass(frozen=True, slots=True)
class GateTimeoutPolicy:
    """The gate kinds a project lets resolve to their default, and each one's wait.

    Declared by `interfaces/gate_timeout_interface.py`. Empty -- nothing times out -- unless
    the project's configuration says otherwise.
    """

    waits: Mapping[str, timedelta] = field(default_factory=dict)

    @classmethod
    def from_config(cls, config: Mapping[str, object]) -> "GateTimeoutPolicy":
        """Read `[human_gates] timeout_defaults` from a project's stored configuration.

        Raises ConfigError for a table that is not a table, a kind that cannot time out,
        or a wait that is not a positive whole number of minutes.
        """
        table = config.get(TABLE)
        if table is None:
            return cls()
        if not isinstance(table, Mapping):
            raise ConfigError(TABLE, "must be a table")
        declared = table.get(KEY)
        if declared is None:
            return cls()
        if not isinstance(declared, Mapping):
            raise ConfigError(f"{TABLE}.{KEY}", "must be a table of gate kind = minutes")
        waits: dict[str, timedelta] = {}
        for kind, minutes in declared.items():
            if kind not in DEFAULT_ANSWER_KEYS:
                allowed = ", ".join(sorted(DEFAULT_ANSWER_KEYS))
                raise ConfigError(
                    f"{TABLE}.{KEY}.{kind}",
                    f"gate kind {kind!r} cannot time out to a default; one of: {allowed}",
                )
            if isinstance(minutes, bool) or not isinstance(minutes, int) or minutes <= 0:
                raise ConfigError(
                    f"{TABLE}.{KEY}.{kind}", "must be a positive whole number of minutes"
                )
            waits[str(kind)] = timedelta(minutes=minutes)
        return cls(waits=MappingProxyType(waits))

    def wait_for(self, kind: str) -> timedelta | None:
        """How long a gate of this kind waits before resolving, or None when it never does."""
        return self.waits.get(kind)

    def resolution(
        self, *, kind: str, default_answer: str | None, waited_seconds: float
    ) -> dict[str, str] | None:
        """The answer a gate resolves to now, or None while it must still wait for a person.

        None for an undeclared kind, for a gate that carries no default, and for one that
        has not yet waited its declared time.
        """
        wait = self.waits.get(kind)
        if wait is None or default_answer is None or not default_answer.strip():
            return None
        if waited_seconds < wait.total_seconds():
            return None
        return {DEFAULT_ANSWER_KEYS[kind]: default_answer}
