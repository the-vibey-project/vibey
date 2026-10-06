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
        "state_sync",
    }
)
"""Capabilities no scope grants and no hub route offers. They stay on the host."""

RESERVED_COMMANDS: Final[dict[tuple[str, ...], str]] = {
    ("migrate",): "migrations",
    ("budget", "set"): "change_caps",
    ("budget", "clear"): "change_caps",
    ("budget", "cap"): "change_caps",
    ("budget", "no-cap"): "no_cap",
    ("state",): "state_sync",
}
"""The vibey commands that reach a `NEVER_FROM_THE_HUB` capability, by their leading words.
A command sent to the workflows through the hub (ADR-0085) runs where a repository may have
declared its real database, so the hub refuses these there exactly as it never routes them
itself. Paid use, the DSN and the canon have no command: they are declared in files."""

READ_COMMANDS: Final[dict[tuple[str, ...], frozenset[str]]] = {
    (): frozenset(),  # global options alone: --version, --help
    ("status",): frozenset({"--json"}),
    ("projects",): frozenset({"--json"}),
    ("gates",): frozenset({"--json"}),  # not --remind: it notifies
    ("engines",): frozenset(),
    ("loops",): frozenset({"--json"}),
    ("cost",): frozenset(),
    # Not --record, --fit-output, --install-postgres, --conformance or --sovereign-fit:
    # they write, install, or run an engine.
    ("doctor",): frozenset({"--project", "--engines", "--provider", "--engine", "--cluster"}),
    ("ledger", "show"): frozenset({"--kind", "--limit", "--phase", "-n"}),
    ("ledger", "search"): frozenset(
        {
            "--actor",
            "--digest",
            "--id",
            "--json",
            "--kind",
            "--limit",
            "--since",
            "--text",
            "--until",
            "-n",
        }
    ),
    ("queue", "list"): frozenset({"--json"}),
    ("budget", "show"): frozenset({"--all", "--json"}),
    ("ultra", "status"): frozenset({"--json"}),
    ("deploy", "status"): frozenset(),
    ("deploy", "inspect"): frozenset(),
}
"""The vibey commands that only read, each with the options that keep it a read. A read
command that carries any other option -- `gates --remind`, `doctor --record` -- is not
taken for a read: it needs every scope, so an option added to a command later fails closed."""

COMMAND_ACTIONS: Final[dict[tuple[str, ...], frozenset[HubAction]]] = {
    **{words: frozenset({HubAction.READ}) for words in READ_COMMANDS},
    # The command line cannot say whether the gate spends money, so both are needed.
    ("answer",): frozenset({HubAction.ANSWER_GATE, HubAction.ANSWER_SPEND_GATE}),
    ("queue", "bump"): frozenset({HubAction.BUMP_JOB}),
    ("queue", "unbump"): frozenset({HubAction.BUMP_JOB}),
    ("work",): frozenset({HubAction.RUN_WORK}),
    ("worker",): frozenset({HubAction.RUN_WORK}),
    ("ultra", "start"): frozenset({HubAction.RUN_WORK}),
    ("ultra", "stop"): frozenset({HubAction.RUN_WORK}),
    ("abandon",): frozenset({HubAction.RUN_WORK}),
}
"""What a vibey command sent to the workflows through the hub does, as hub actions. On a
repository that declares its real database the command acts on it, so the `workflows` scope
alone must not let a device do what its other scopes do not: the caller needs the scope of
each action too, and a command not named here needs every scope the hub defines (ADR-0085)."""

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

    @staticmethod
    def command_words(argv: tuple[str, ...]) -> tuple[str, ...]:
        """A vibey command line's command, read after its leading global options (whose
        values are skipped) and up to its first option."""
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
        return tuple(words)

    def reserved_command(self, argv: tuple[str, ...]) -> str | None:
        """The `NEVER_FROM_THE_HUB` capability a vibey command line reaches, or None."""
        words = self.command_words(argv)
        for prefix, capability in RESERVED_COMMANDS.items():
            if words[: len(prefix)] == prefix:
                return capability
        return None

    def scopes_for_command(self, argv: tuple[str, ...]) -> frozenset[HubScope]:
        """Every scope a caller must hold to send `argv` to the workflows: `workflows`, and
        the scope of each action the command performs; every scope for a command
        `COMMAND_ACTIONS` does not name. The longest matching prefix decides."""
        words = self.command_words(argv)
        matches = [p for p in COMMAND_ACTIONS if words[: len(p)] == p and (p or not words)]
        if not matches:
            return frozenset(HubScope)
        prefix = max(matches, key=len)
        if prefix in READ_COMMANDS and not self._only_safe_options(argv, READ_COMMANDS[prefix]):
            return frozenset(HubScope)
        actions = COMMAND_ACTIONS[prefix]
        return frozenset({HubScope.WORKFLOWS} | {REQUIRED_SCOPE[a] for a in actions})

    def _only_safe_options(self, argv: tuple[str, ...], safe: frozenset[str]) -> bool:
        """True when every option after the command is `--help` or one of `safe`. An option's
        `=value` is set aside; any token that is not exactly a declared option (`-n5`) is
        not one of them."""
        words = self.command_words(argv)
        if not words:
            return True
        after = argv[argv.index(words[-1]) + 1 :]
        return all(
            arg.split("=", 1)[0] in safe | {"--help"} for arg in after if arg.startswith("-")
        )

    def parse(self, values: frozenset[str]) -> frozenset[HubScope]:
        """The scopes `values` names. An unknown name raises `ValueError`: a grant that
        names a scope this version does not know is refused, never read as a narrower one."""
        return frozenset(HubScope(value) for value in values)


HUB_SCOPES: Final = HubScopePolicy()
"""The policy every hub adapter consults. Stateless, so one instance serves."""
