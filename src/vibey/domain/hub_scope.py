# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What a caller of the hub may do: scopes, the actions they cover, and the ones none does.

The hub (`vibey serve`, ADR-0067) answers every krypton client over HTTP. Each request is
one `HubAction`, and each action needs exactly one `HubScope`. A caller holds a set of
scopes; an action is permitted only when the set holds the scope it needs. The default is
the empty set, so a caller nobody granted anything is refused everything (deny by default,
sub-doctrines 10.c and 12.j).

Some things are never a hub action at all, whatever a caller holds: declaring paid use,
lifting a cap or changing one, the database DSN, migrations and the canon. They belong to
the host's own configuration and to the operator's merge, and a device that could reach
them would make the host's declarations mean nothing. `NEVER_FROM_THE_HUB` names them, and
`HubScopePolicy.reserved` reports whether a named capability is one of them, so an adapter
that is asked for one refuses it by the same list the tests read.

Pure: no I/O, no clock.
"""

from enum import StrEnum
from typing import Final

from vibey.domain.errors import VibeyError


class HubForbidden(VibeyError):
    """The caller's scopes do not permit the action it asked for."""


class HubScope(StrEnum):
    """One kind of permission a paired device can hold. Stored by value."""

    VIEW = "view"
    """Read projects, status, gates, budgets, the queue, the ledger, loops, lanes, doctor."""
    ANSWER = "answer"
    """Answer a human gate that is not a spending decision."""
    SPEND = "spend"
    """Answer a gate whose answer spends money. Re-verified on every action."""
    RUN = "run"
    """Start, stop or wind down work."""
    BUMP = "bump"
    """Move a queued job to the front of its project's queue."""
    WORKFLOWS = "workflows"
    """Run a vibey command on the repository's GitHub-hosted runners (`vibey -w`, ADR-0085)."""


class HubAction(StrEnum):
    """Everything the hub can be asked to do. Each needs one scope (`REQUIRED_SCOPE`)."""

    READ = "read"
    ANSWER_GATE = "answer_gate"
    ANSWER_SPEND_GATE = "answer_spend_gate"
    RUN_WORK = "run_work"
    BUMP_JOB = "bump_job"
    RUN_ON_WORKFLOWS = "run_on_workflows"


REQUIRED_SCOPE: Final[dict[HubAction, HubScope]] = {
    HubAction.READ: HubScope.VIEW,
    HubAction.ANSWER_GATE: HubScope.ANSWER,
    HubAction.ANSWER_SPEND_GATE: HubScope.SPEND,
    HubAction.RUN_WORK: HubScope.RUN,
    HubAction.BUMP_JOB: HubScope.BUMP,
    HubAction.RUN_ON_WORKFLOWS: HubScope.WORKFLOWS,
}
"""The one scope each action needs. Total over `HubAction`; a test holds it so."""

NEVER_FROM_THE_HUB: Final[frozenset[str]] = frozenset(
    {
        "declare_paid_use",
        "no_cap",
        "change_caps",
        "database_dsn",
        "migrations",
        "canon",
    }
)
"""Capabilities no scope grants and no hub route offers. They stay on the host."""

RESERVED_COMMANDS: Final[dict[tuple[str, ...], str]] = {
    ("migrate",): "migrations",
    ("budget", "set"): "change_caps",
    ("budget", "clear"): "change_caps",
    ("budget", "cap"): "change_caps",
    ("budget", "no-cap"): "no_cap",
}
"""The vibey commands that reach a `NEVER_FROM_THE_HUB` capability, by their leading words.
A command sent to the workflows through the hub (ADR-0085) runs where a repository may have
declared its real database, so the hub refuses these there exactly as it never routes them
itself. Paid use, the DSN and the canon have no command: they are declared in files."""

SPEND_GATE_KINDS: Final[frozenset[str]] = frozenset(
    {
        "budget_exhausted",
        "deploy_interview",
        "deploy_acceptance",
        "deploy_demo_review",
        "deploy_failure_triage",
    }
)
"""Gate kinds whose answer decides whether money is spent -- resuming past a cap, or a
deployment stage that provisions cloud resources: answering one needs `spend`, and
`answer` alone is not enough. The REVIEW phase's opt-in to deployment is a generic
`choice` gate and cannot be told apart by kind; ADR-0067 records that gap."""


class HubScopePolicy:
    """Decides whether a set of granted scopes permits an action. Pure.

    Declared by `interfaces/hub_scope_interface.py::HubScopePolicyInterface`."""

    def permits(self, granted: frozenset[HubScope], action: HubAction) -> bool:
        """True only when `granted` holds the scope `action` needs."""
        return REQUIRED_SCOPE[action] in granted

    def action_for_gate(self, kind: str) -> HubAction:
        """The action answering a gate of `kind` is: a spending one for the kinds in
        `SPEND_GATE_KINDS`, a plain answer for every other."""
        return HubAction.ANSWER_SPEND_GATE if kind in SPEND_GATE_KINDS else HubAction.ANSWER_GATE

    def reserved(self, capability: str) -> bool:
        """True when `capability` is one the hub never offers (`NEVER_FROM_THE_HUB`)."""
        return capability in NEVER_FROM_THE_HUB

    def reserved_command(self, argv: tuple[str, ...]) -> str | None:
        """The `NEVER_FROM_THE_HUB` capability a vibey command line reaches, or None. Its
        command is read after vibey's leading global options, whose values are skipped."""
        words: list[str] = []
        skip = False
        for arg in argv:
            if skip:
                skip = False
            elif arg in ("--log-level", "--log-file"):
                skip = True
            elif not arg.startswith("-"):
                words.append(arg)
            elif words:
                break
        for prefix, capability in RESERVED_COMMANDS.items():
            if tuple(words[: len(prefix)]) == prefix:
                return capability
        return None

    def parse(self, values: frozenset[str]) -> frozenset[HubScope]:
        """The scopes `values` names. An unknown name raises `ValueError`: a grant that
        names a scope this version does not know is refused, never read as a narrower one."""
        return frozenset(HubScope(value) for value in values)


HUB_SCOPES: Final = HubScopePolicy()
"""The policy every hub adapter consults. Stateless, so one instance serves."""
