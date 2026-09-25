# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The publication policy: what of a ledger a public shard may carry.

Sub-doctrine 7.a says anyone, no matter who, can search the ledger. The ledger was
not written for the public: it holds seed prompts, model output, tool calls, local
paths and whatever an engine read from the web. So the public never reads the ledger
itself. It reads a projection of it, made at read time by this policy, and the
policy is **default-deny**:

- **An event is published only if its kind is allowlisted.** Every other kind is
  withheld whole. The allowlist (`DEFAULT_ALLOWLIST`) names, per kind, the payload
  fields a published record keeps; every other field is withheld.
- **Engine chatter is withheld whole**, whatever the allowlist says: the turn
  traffic between vibey and an engine (`TurnRequested`, `TurnCompleted`) and every
  tool call (`ToolInvoked`), which is where prompts, model output and tool bodies
  land (`infrastructure/engines/loop_events.py` maps each loop's chatter onto
  exactly these kinds).
- **Untrusted provenance is withheld whole.** An event vibey marked `untrusted`
  carries text from outside -- a web page, an issue body -- and publishing it would
  re-serve a stranger's words under this project's name.
- **Every string a published record keeps is scrubbed**: absolute paths (POSIX,
  home-relative, Windows, UNC and `file:` URLs) and email addresses become tokens.
  A key inside a kept value that is itself a path or an address is withheld with
  its value.
- **`repo_path` is never published**, whatever the allowlist says, and a rule set
  that tries to allow it is refused on construction.
- **Credential redaction runs last**, through `CredentialRedactorInterface`, so
  the credential patterns stay in `infrastructure/ledger/redact.py` alone.

Nothing is dropped silently. Every event withheld is counted by reason, every
field withheld and every path, address and credential replaced is counted, per
record and in total, and those counts travel with the shard into the published
site.

**A published record's digest is the digest of what was published.** It is
recomputed after the policy, so a reader can check every record against its own
digest, and a withheld field cannot be recovered by guessing it and hashing. A
record the policy did not change has the same digest it has in the ledger.
"""

import dataclasses
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
from operator import attrgetter
from types import MappingProxyType
from typing import Final, cast
from uuid import UUID

from vibey.domain.errors import VibeyError
from vibey.domain.interfaces.publication_policy_interface import (
    CredentialRedactorInterface,
    PublicationPolicyInterface,
    PublicationRulesInterface,
    TrimCountsInterface,
)
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance, canonical_bytes, digest_event

PUBLICATION_SCHEME: Final = "vibey-publication-policy/v1"
"""The policy family a rule set belongs to. Folded into the rules' fingerprint."""

NEVER_PUBLISHED_FIELDS: Final = frozenset({"repo_path"})
"""Field names no rule set may publish. `repo_path` is where the project lives on
the operator's machine: it names a user and a disk layout and means nothing to
anyone else."""

DEFAULT_PATH_TOKEN: Final = "[path]"
DEFAULT_EMAIL_TOKEN: Final = "[email]"

ENGINE_CHATTER: Final = frozenset(
    {EventKind.TURN_REQUESTED, EventKind.TURN_COMPLETED, EventKind.TOOL_INVOKED}
)
"""Where every loop's prompts, model output and tool calls land."""

DEFAULT_WITHHELD_PROVENANCE: Final = frozenset({Provenance.UNTRUSTED})

DEFAULT_ALLOWLIST: Final[Mapping[EventKind, frozenset[str]]] = MappingProxyType(
    {
        EventKind.PHASE_TRANSITIONED: frozenset({"from", "to", "cycle", "guard"}),
        EventKind.DECISION_RECORDED: frozenset(
            {
                "decision_id",
                "decision",
                "title",
                "choice",
                "rationale",
                "alternatives",
                "supersedes",
                "next_phase",
                "work_item_id",
                "independent_review",
            }
        ),
        EventKind.QUESTION_ASKED: frozenset(
            {"item_id", "question_id", "text", "default", "blocking", "stage", "cycle"}
        ),
        EventKind.ANSWER_GIVEN: frozenset({"item_id", "question_id", "answer"}),
        EventKind.ASSUMPTION_STATED: frozenset({"item_id", "assumption_id", "text", "question"}),
        EventKind.FINDING_RAISED: frozenset(
            {"finding_id", "severity", "ambiguity", "text", "automated"}
        ),
        EventKind.FINDING_RESOLVED: frozenset({"finding_id", "resolution"}),
        EventKind.ARTIFACT_PRODUCED: frozenset({"artifact_id", "artifact_type", "title", "cycle"}),
        EventKind.VERDICT_RENDERED: frozenset({"complete", "success", "remaining_work"}),
        EventKind.VISUAL_DESIGN_OPTED_IN: frozenset({"choice"}),
        EventKind.VISUAL_DESIGN_DECLINED: frozenset({"choice"}),
        EventKind.VISUAL_DESIGN_ACCEPTED: frozenset({"choice"}),
        EventKind.VISUAL_DESIGN_WAIVED: frozenset({"choice"}),
        EventKind.DEPLOYMENT_OPTED_IN: frozenset({"choice"}),
        EventKind.DEPLOYMENT_DECLINED: frozenset({"choice"}),
        EventKind.DELIVERY_ESTIMATE_RECORDED: frozenset(
            {
                "schema",
                "recorded_at",
                "source_fingerprint",
                "history",
                "time",
                "billing",
                "materials",
                "track_record",
                "assumptions",
                "problems",
            }
        ),
    }
)
"""The default allowlist: the record of what was decided, asked, answered, assumed,
found and resolved, and how the phases moved -- and nothing an engine said on the
way. Kinds absent here are withheld whole; `WITHHELD_KINDS` names every one of them.
Paths an artifact was written to, research content and raw spend are left out on
purpose; the forecast is allowlisted because it is an explicitly derived, human-facing
summary with its assumptions beside it."""

WITHHELD_KINDS: Final[frozenset[EventKind]] = frozenset(
    {
        # What an engine was told and what it wrote: seed prompts, turn text, diffs.
        EventKind.SESSION_SEEDED,
        EventKind.TRANSCRIPT_RECORDED,
        EventKind.FILE_EDITED,
        # The operator's provider accounts, repository and engine rotation.
        EventKind.CAPACITY_REJECTED,
        EventKind.SAVEPOINT_CREATED,
        EventKind.HANDOFF_INITIATED,
        EventKind.HANDOFF_ACCEPTED,
        # Money: raw spend, and the caps the operator sets on it with the account that
        # set them (`vibey budget`). Only the explicit billing projection below reads
        # spend, and it reads no caps.
        EventKind.BUDGET_SPENT,
        EventKind.BUDGET_CAP_CHANGED,
        # ULTRA's operator controls and no-cap declarations name the account and device.
        EventKind.ULTRA_STARTED,
        EventKind.ULTRA_STOPPED,
        EventKind.ULTRA_PASS_COMPLETED,
        EventKind.ULTRA_NO_CAP_CHANGED,
        # Failover and handback name the operator's engines, accounts and probes.
        EventKind.ENGINE_FAILED_OVER,
        EventKind.ENGINE_PROBED,
        EventKind.ENGINE_HANDED_BACK,
        # Who answered a gate, from which account, and what they answered: the answer
        # can carry anything a person typed, and the account is the operator's.
        EventKind.GATE_ANSWERED,
        # Which devices could reach the hub, and which scopes the host granted them.
        EventKind.HUB_DEVICE_PAIRED,
        EventKind.HUB_DEVICE_REVOKED,
        # Queue operations: who reordered which job, and what the reaper did.
        EventKind.JOB_PRIORITY_BUMPED,
        EventKind.JOB_PRIORITY_UNBUMPED,
        EventKind.JOB_PRIORITY_REFUSED,
        EventKind.QUEUE_REAPED,
    }
)
"""Every kind the default rules withhold whole, named so that none is withheld -- or
published -- by omission. The policy is default-deny whatever this set says; it is the
record of each decision, and `tests/domain/test_publication_policy.py` fails when a
kind is in none of `DEFAULT_ALLOWLIST`, `ENGINE_CHATTER` and this set, or in two."""

# A path starts where a word could: at the start of the text, or after whitespace, a
# quote, an opening `(`, `[` or `{`, or one of `=,;:|>`. Not after a letter, a digit, a
# slash or `<`, so `a/b`, the path of `https://host/a/b` and the `/p` of `</p>` are left
# alone. The class is negated so the lookbehind stays one character wide.
_BOUNDARY: Final = r"(?<![^\s'\"`(\[{=,;:|>])"
_SEGMENT: Final = r"[^\s/'\"`<>(){}|,;]"
_PATH: Final = re.compile(
    "|".join(
        (
            r"(?i:file:)//[^\s'\"`<>]*",
            _BOUNDARY + r"[A-Za-z]:[\\/][^\s'\"`<>|]*",
            _BOUNDARY + r"\\\\[^\s'\"`<>|]+",
            _BOUNDARY + r"~[\w.-]*/" + _SEGMENT + r"*(?:/" + _SEGMENT + r"*)*",
            _BOUNDARY + r"/" + _SEGMENT + r"+(?:/" + _SEGMENT + r"+)*/?",
        )
    )
)
# local@domain with a dotted domain ending in letters, so `vibey@1.1.0` and
# `name@localhost` survive and `adam@example.com` does not.
_EMAIL: Final = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")


class WithheldReason(StrEnum):
    """Why an event was withheld whole. Checked in this order; the first wins."""

    UNTRUSTED_PROVENANCE = "untrusted_provenance"
    ENGINE_CHATTER = "engine_chatter"
    KIND_NOT_ALLOWLISTED = "kind_not_allowlisted"


class InvalidPublicationRules(VibeyError):
    """A rule set that contradicts a rule no rule set may break.

    An exception type, so it has no interface beside it: a `Protocol` cannot be
    raised or caught, and the seam an error crosses is its type.
    """


@dataclass(frozen=True, slots=True)
class PublicationRules:
    """The data the policy applies, in one place (ADR-0018): widening what is
    published is a change to this value and nothing else."""

    allowed: Mapping[EventKind, frozenset[str]] = field(default_factory=lambda: DEFAULT_ALLOWLIST)
    chatter: frozenset[EventKind] = ENGINE_CHATTER
    withheld_provenance: frozenset[Provenance] = DEFAULT_WITHHELD_PROVENANCE
    path_token: str = DEFAULT_PATH_TOKEN
    email_token: str = DEFAULT_EMAIL_TOKEN
    scheme: str = PUBLICATION_SCHEME

    def __post_init__(self) -> None:
        for kind, names in self.allowed.items():
            refused = names & NEVER_PUBLISHED_FIELDS
            if refused:
                raise InvalidPublicationRules(
                    f"{kind.value} may not publish {', '.join(sorted(refused))}: "
                    "that field is never published"
                )
        # A copy the caller cannot mutate after the check.
        object.__setattr__(self, "allowed", MappingProxyType(dict(self.allowed)))

    @property
    def never_published(self) -> frozenset[str]:
        return NEVER_PUBLISHED_FIELDS

    @property
    def fingerprint(self) -> str:
        return sha256(
            canonical_bytes(
                {
                    "scheme": self.scheme,
                    "allowed": {kind.value: sorted(names) for kind, names in self.allowed.items()},
                    "chatter": sorted(kind.value for kind in self.chatter),
                    "withheld_provenance": sorted(p.value for p in self.withheld_provenance),
                    "never_published": sorted(NEVER_PUBLISHED_FIELDS),
                    "path_token": self.path_token,
                    "email_token": self.email_token,
                }
            )
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class TrimCounts:
    """What the policy removed from inside published records."""

    fields: int = 0
    paths: int = 0
    emails: int = 0
    credentials: int = 0

    @property
    def total(self) -> int:
        return self.fields + self.paths + self.emails + self.credentials

    def plus(self, other: TrimCountsInterface) -> "TrimCounts":
        return TrimCounts(
            fields=self.fields + other.fields,
            paths=self.paths + other.paths,
            emails=self.emails + other.emails,
            credentials=self.credentials + other.credentials,
        )


NO_TRIM: Final = TrimCounts()


@dataclass(frozen=True, slots=True)
class PublicationDecision:
    """What the policy did with one event."""

    record: LedgerEvent | None
    withheld: WithheldReason | None
    trim: TrimCountsInterface = NO_TRIM


@dataclass(frozen=True, slots=True)
class PublicationOutcome:
    """What the policy did with a ledger."""

    records: tuple[LedgerEvent, ...]
    trims: Mapping[UUID, TrimCountsInterface]
    withheld: Mapping[WithheldReason, int]
    trimmed: TrimCountsInterface

    @property
    def events_withheld(self) -> int:
        return sum(self.withheld.values())


class PublicationPolicy:
    """Projects ledger events onto what a public shard may carry. Pure."""

    def __init__(
        self,
        rules: PublicationRulesInterface | None = None,
        *,
        redactor: CredentialRedactorInterface | None = None,
    ) -> None:
        self._rules: PublicationRulesInterface = rules if rules is not None else DEFAULT_RULES
        self._redactor = redactor

    @property
    def rules(self) -> PublicationRulesInterface:
        return self._rules

    def decide(self, event: LedgerEvent) -> PublicationDecision:
        reason = self._reason(event)
        if reason is not None:
            return PublicationDecision(record=None, withheld=reason)
        record, trim = self._publish(event)
        return PublicationDecision(record=record, withheld=None, trim=trim)

    def apply(self, events: Sequence[LedgerEvent]) -> PublicationOutcome:
        withheld = dict.fromkeys(WithheldReason, 0)
        records: list[LedgerEvent] = []
        trims: dict[UUID, TrimCountsInterface] = {}
        trimmed: TrimCountsInterface = NO_TRIM
        for event in sorted(events, key=attrgetter("seq")):
            reason = self._reason(event)
            if reason is not None:
                withheld[reason] += 1
                continue
            record, trim = self._publish(event)
            records.append(record)
            if trim.total:
                trims[record.event_id] = trim
                trimmed = trimmed.plus(trim)
        return PublicationOutcome(
            records=tuple(records),
            trims=MappingProxyType(trims),
            withheld=MappingProxyType(withheld),
            trimmed=trimmed,
        )

    def _publish(self, event: LedgerEvent) -> tuple[LedgerEvent, TrimCountsInterface]:
        # `_reason` withholds every unrecognized kind before `_publish` is called.
        # The cast records that invariant without importing a newer kind's meaning.
        kind = cast(EventKind, event.kind)
        keep = self._rules.allowed[kind] - self._rules.never_published
        payload: dict[str, object] = {}
        trim: TrimCountsInterface = NO_TRIM
        for key, value in event.payload.items():
            if key not in keep:
                trim = trim.plus(TrimCounts(fields=1))
                continue
            payload[key], inner = self._scrub(value)
            trim = trim.plus(inner)
        if self._redactor is not None:
            redacted = dict(self._redactor.redact(payload))
            if redacted != payload:
                trim = trim.plus(TrimCounts(credentials=1))
            payload = redacted
        return dataclasses.replace(event, payload=payload, digest=digest_event(payload)), trim

    def _reason(self, event: LedgerEvent) -> WithheldReason | None:
        if event.provenance in self._rules.withheld_provenance:
            return WithheldReason.UNTRUSTED_PROVENANCE
        if event.kind in self._rules.chatter:
            return WithheldReason.ENGINE_CHATTER
        if event.kind not in self._rules.allowed:
            return WithheldReason.KIND_NOT_ALLOWLISTED
        return None

    def _scrub(self, value: object) -> tuple[object, TrimCountsInterface]:
        if value is None or isinstance(value, bool | int | float):
            return value, NO_TRIM
        if isinstance(value, str):
            text, emails = _EMAIL.subn(self._rules.email_token, value)
            text, paths = _PATH.subn(self._rules.path_token, text)
            return text, TrimCounts(paths=paths, emails=emails)
        if isinstance(value, Mapping):
            return self._scrub_mapping(value)
        if isinstance(value, list | tuple):
            items: list[object] = []
            trim: TrimCountsInterface = NO_TRIM
            for item in value:
                clean, inner = self._scrub(item)
                items.append(clean)
                trim = trim.plus(inner)
            return items, trim
        # Payloads decoded from JSON never get here; anything else is published as
        # the text `canonical_bytes` would hash it as, and scrubbed like any text.
        return self._scrub(str(value))

    def _scrub_mapping(self, value: Mapping[object, object]) -> tuple[object, TrimCountsInterface]:
        kept: dict[str, object] = {}
        trim: TrimCountsInterface = NO_TRIM
        for key, item in value.items():
            name = str(key)
            if _EMAIL.search(name) or _PATH.search(name):
                # A key is a name, not content: one that is a path or an address
                # is withheld with its value rather than rewritten into a token
                # that two keys could collide on.
                trim = trim.plus(TrimCounts(fields=1))
                continue
            kept[name], inner = self._scrub(item)
            trim = trim.plus(inner)
        return kept, trim


DEFAULT_RULES: Final[PublicationRulesInterface] = PublicationRules()
"""The default-deny rules. Annotated with the interface so `mypy --strict` checks
the class against its declared seam."""

DEFAULT_POLICY: Final[PublicationPolicyInterface] = PublicationPolicy()
"""The default rules with no credential redactor. A caller that publishes passes one
(`vibey ledger export` passes `infrastructure/ledger/redact.py`'s)."""

# An operator-scoped billing shard is deliberately a different projection from the
# public shard above. Public export withholds raw spend; this explicit opt-in keeps only
# the numeric fields and event kinds the budget brake and phase-timing projection consume,
# so ``vibey-gh forecast`` can use real billing history without publishing prompts,
# outputs, tool bodies or credentials. Empty payload allowlists are intentional: the
# event kind itself is the operational count.
BILLING_ALLOWLIST: Final[Mapping[EventKind, frozenset[str]]] = MappingProxyType(
    {
        EventKind.TURN_COMPLETED: frozenset({"cost_usd"}),
        EventKind.BUDGET_SPENT: frozenset({"dollars", "turns"}),
        EventKind.PHASE_TRANSITIONED: frozenset(),
        EventKind.CAPACITY_REJECTED: frozenset(),
        EventKind.HANDOFF_INITIATED: frozenset(),
        EventKind.TOOL_INVOKED: frozenset(),
        EventKind.FILE_EDITED: frozenset(),
        EventKind.ARTIFACT_PRODUCED: frozenset(),
    }
)
BILLING_RULES: Final[PublicationRulesInterface] = PublicationRules(
    allowed=BILLING_ALLOWLIST,
    chatter=frozenset(),
    scheme="vibey-billing-publication/v1",
)
BILLING_POLICY: Final[PublicationPolicyInterface] = PublicationPolicy(BILLING_RULES)
"""The explicit operator-only billing projection consumed by the forecast."""
