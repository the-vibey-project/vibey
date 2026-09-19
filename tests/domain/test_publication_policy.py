# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The publication policy: default-deny, nothing withheld silently, nothing withheld leaks."""

import json
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from vibey.domain.engine import EngineId
from vibey.domain.interfaces import (
    CredentialRedactorInterface,
    PublicationDecisionInterface,
    PublicationOutcomeInterface,
    PublicationPolicyInterface,
    PublicationRulesInterface,
    TrimCountsInterface,
)
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance, digest_event
from vibey.domain.ledger_record import LEDGER_RECORDS
from vibey.domain.phase import Phase
from vibey.domain.publication_policy import (
    DEFAULT_ALLOWLIST,
    DEFAULT_POLICY,
    DEFAULT_RULES,
    ENGINE_CHATTER,
    NEVER_PUBLISHED_FIELDS,
    NO_TRIM,
    InvalidPublicationRules,
    PublicationPolicy,
    PublicationRules,
    TrimCounts,
    WithheldReason,
)

PROJECT = UUID("6f1c2a0e-0000-4000-8000-000000000003")
T0 = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)


def _event(seq: int = 1, **overrides: object) -> LedgerEvent:
    payload = overrides.pop("payload", {"decision_id": "d1", "title": "use Postgres"})
    fields: dict[str, object] = {
        "event_id": uuid4(),
        "project_id": PROJECT,
        "cycle": 1,
        "phase": Phase.DESIGN,
        "seq": seq,
        "kind": EventKind.DECISION_RECORDED,
        "engine_id": None,
        "job_id": None,
        "causation_id": None,
        "correlation_id": PROJECT,
        "provenance": Provenance.TRUSTED,
        "produced_at": T0 + timedelta(seconds=seq),
        "payload": payload,
        "digest": digest_event(payload),  # type: ignore[arg-type]
    }
    fields.update(overrides)
    return LedgerEvent(**fields)  # type: ignore[arg-type]


def _published(
    event: LedgerEvent, policy: PublicationPolicyInterface = DEFAULT_POLICY
) -> tuple[Mapping[str, object], TrimCountsInterface]:
    decision = policy.decide(event)
    assert decision.record is not None, decision.withheld
    return decision.record.payload, decision.trim


def _text(value: str, policy: PublicationPolicyInterface = DEFAULT_POLICY) -> str:
    payload, _ = _published(_event(payload={"title": value}), policy)
    return str(payload["title"])


class _Redactor:
    """Replaces any value equal to `secret`, the way redact.py replaces a key."""

    def redact(self, payload: Mapping[str, object]) -> Mapping[str, object]:
        return {key: "[REDACTED]" if value == "secret" else value for key, value in payload.items()}


# -- the seams ---------------------------------------------------------------


def test_the_defaults_satisfy_their_interfaces() -> None:
    assert isinstance(DEFAULT_RULES, PublicationRulesInterface)
    assert isinstance(DEFAULT_POLICY, PublicationPolicyInterface)
    assert isinstance(NO_TRIM, TrimCountsInterface)
    assert isinstance(_Redactor(), CredentialRedactorInterface)
    decision = DEFAULT_POLICY.decide(_event())
    assert isinstance(decision, PublicationDecisionInterface)
    assert isinstance(DEFAULT_POLICY.apply([_event()]), PublicationOutcomeInterface)
    assert DEFAULT_POLICY.rules is DEFAULT_RULES
    assert PublicationPolicy().rules is DEFAULT_RULES


# -- default-deny --------------------------------------------------------------


def test_an_allowlisted_kind_keeps_only_its_allowlisted_fields() -> None:
    event = _event(payload={"decision_id": "d1", "title": "t", "internal": "x", "notes": "y"})
    decision = DEFAULT_POLICY.decide(event)

    assert decision.withheld is None
    assert decision.record is not None
    assert decision.record.payload == {"decision_id": "d1", "title": "t"}
    assert decision.trim == TrimCounts(fields=2)


def test_every_field_but_the_payload_and_its_digest_is_kept() -> None:
    event = _event(engine_id=EngineId.CLAUDELOOP, job_id=uuid4(), payload={"title": "t", "x": 1})
    record = DEFAULT_POLICY.decide(event).record

    assert record is not None
    kept = {name: value for name, value in LEDGER_RECORDS.to_fields(record).items()}
    original = LEDGER_RECORDS.to_fields(event)
    for name in set(original) - {"payload", "digest"}:
        assert kept[name] == original[name], name


def test_the_published_digest_is_the_digest_of_what_was_published() -> None:
    trimmed = DEFAULT_POLICY.decide(_event(payload={"title": "t", "x": 1})).record
    untouched_event = _event(payload={"title": "t"})
    untouched = DEFAULT_POLICY.decide(untouched_event).record

    assert trimmed is not None and untouched is not None
    assert trimmed.digest == digest_event({"title": "t"})
    assert untouched.digest == untouched_event.digest


def test_a_kind_not_on_the_allowlist_is_withheld_whole() -> None:
    decision = DEFAULT_POLICY.decide(_event(kind=EventKind.BUDGET_SPENT, payload={"dollars": 1}))

    assert decision.record is None
    assert decision.withheld is WithheldReason.KIND_NOT_ALLOWLISTED
    assert decision.trim == NO_TRIM


@pytest.mark.parametrize("kind", sorted(ENGINE_CHATTER))
def test_engine_chatter_is_withheld_even_when_allowlisted(kind: EventKind) -> None:
    rules = PublicationRules(allowed={kind: frozenset({"text"})})
    decision = PublicationPolicy(rules).decide(_event(kind=kind, payload={"text": "hi"}))

    assert decision.withheld is WithheldReason.ENGINE_CHATTER


def test_untrusted_provenance_is_withheld_first() -> None:
    event = _event(kind=EventKind.TOOL_INVOKED, provenance=Provenance.UNTRUSTED)
    assert DEFAULT_POLICY.decide(event).withheld is WithheldReason.UNTRUSTED_PROVENANCE


def test_repo_path_is_never_published_and_no_rule_set_may_allow_it() -> None:
    payload, trim = _published(_event(payload={"title": "t", "repo_path": "/Users/a/p"}))
    assert "repo_path" not in payload
    assert trim.fields == 1
    assert DEFAULT_RULES.never_published == NEVER_PUBLISHED_FIELDS == {"repo_path"}

    with pytest.raises(InvalidPublicationRules, match="DecisionRecorded may not publish repo_path"):
        PublicationRules(allowed={EventKind.DECISION_RECORDED: frozenset({"repo_path"})})


def test_the_default_allowlist_publishes_no_engine_chatter_and_no_repo_path() -> None:
    assert not ENGINE_CHATTER & DEFAULT_ALLOWLIST.keys()
    assert all(not names & NEVER_PUBLISHED_FIELDS for names in DEFAULT_ALLOWLIST.values())


# -- scrubbing -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "published"),
    [
        ("see /Users/adam/git/vibey/x.py", "see [path]"),
        ("/home/dev/.config", "[path]"),
        (
            "cwd=/private/tmp/w, then (/opt/bin) and `/var/log`",
            "cwd=[path], then ([path]) and `[path]`",
        ),
        ("at /Users/adam/[draft]/notes.md:12", "at [path]"),
        ("~/git/vibey and ~adam/x", "[path] and [path]"),
        ("C:\\Users\\adam\\x.txt or D:/data", "[path] or [path]"),
        ("share \\\\server\\share\\f", "share [path]"),
        ("open file:///Users/adam/x.html now", "open [path] now"),
        ("scp host:/srv/x", "scp host:[path]"),
    ],
)
def test_absolute_paths_are_stripped_from_published_strings(text: str, published: str) -> None:
    assert _text(text) == published


@pytest.mark.parametrize(
    "text",
    [
        "src/vibey/domain/ledger.py",
        "https://github.com/the-vibey-project/vibey/pull/5",
        "and/or 1/2",
        "<p>ok</p> </script>",
        "a lone / slash",
        "install vibey@1.1.0 or name@localhost",
    ],
)
def test_relative_paths_urls_tags_and_versions_survive(text: str) -> None:
    assert _text(text) == text


def test_email_addresses_are_stripped_and_counted() -> None:
    payload, trim = _published(
        _event(payload={"title": "mail adam@example.com and a.b+c@sub.example.co.uk"})
    )
    assert payload["title"] == "mail [email] and [email]"
    assert trim == TrimCounts(emails=2)


def test_paths_are_counted_per_occurrence() -> None:
    _, trim = _published(_event(payload={"title": "/a/b and /c/d", "rationale": "~/e"}))
    assert trim == TrimCounts(paths=3)


def test_the_tokens_are_part_of_the_rules() -> None:
    rules = PublicationRules(path_token="<p>", email_token="<e>")
    policy = PublicationPolicy(rules)
    assert _text("/tmp/x a@b.io", policy) == "<p> <e>"
    assert rules.fingerprint != DEFAULT_RULES.fingerprint


def test_nested_values_are_scrubbed_and_keys_that_are_paths_or_addresses_withheld() -> None:
    payload, trim = _published(
        _event(
            payload={
                "alternatives": [
                    "keep /tmp/a",
                    {"note": "adam@example.com", "/Users/adam": "x", "ops@corp.com": 1},
                    ("tuple", 2),
                ],
                "choice": {"nested": {"deep": "~/x"}},
            }
        )
    )
    assert payload == {
        "alternatives": ["keep [path]", {"note": "[email]"}, ["tuple", 2]],
        "choice": {"nested": {"deep": "[path]"}},
    }
    assert trim == TrimCounts(fields=2, paths=2, emails=1)


def test_scalars_pass_and_anything_else_is_published_as_scrubbed_text() -> None:
    marker = UUID("12345678-1234-5678-1234-567812345678")
    payload, _ = _published(
        _event(
            payload={
                "title": None,
                "independent_review": True,
                "decision_id": 3,
                "choice": 1.5,
                "rationale": marker,
            }
        )
    )
    assert payload == {
        "title": None,
        "independent_review": True,
        "decision_id": 3,
        "choice": 1.5,
        "rationale": str(marker),
    }


# -- credential redaction runs last -----------------------------------------------


def test_the_redactor_runs_on_what_was_kept_and_is_counted() -> None:
    policy = PublicationPolicy(redactor=_Redactor())
    decision = policy.decide(_event(payload={"title": "secret", "choice": "fine"}))

    assert decision.record is not None
    assert decision.record.payload == {"title": "[REDACTED]", "choice": "fine"}
    assert decision.record.digest == digest_event({"title": "[REDACTED]", "choice": "fine"})
    assert decision.trim == TrimCounts(credentials=1)


def test_a_redactor_that_changes_nothing_counts_nothing() -> None:
    policy = PublicationPolicy(redactor=_Redactor())
    assert _published(_event(payload={"title": "plain"}), policy)[1] == NO_TRIM


# -- a whole ledger ----------------------------------------------------------------


def test_apply_counts_every_withheld_event_by_reason_and_every_trim() -> None:
    events = [
        _event(3, payload={"title": "/tmp/x", "extra": 1}),
        _event(1, kind=EventKind.TURN_COMPLETED),
        _event(2, provenance=Provenance.UNTRUSTED),
        _event(4, kind=EventKind.FILE_EDITED),
        _event(5, payload={"title": "clean"}),
        _event(6, kind=EventKind.SESSION_SEEDED),
    ]
    outcome = DEFAULT_POLICY.apply(events)

    assert [record.seq for record in outcome.records] == [3, 5]
    assert dict(outcome.withheld) == {
        WithheldReason.UNTRUSTED_PROVENANCE: 1,
        WithheldReason.ENGINE_CHATTER: 1,
        WithheldReason.KIND_NOT_ALLOWLISTED: 2,
    }
    assert outcome.events_withheld == 4
    assert dict(outcome.trims) == {events[0].event_id: TrimCounts(fields=1, paths=1)}
    assert outcome.trimmed == TrimCounts(fields=1, paths=1)


def test_apply_on_nothing_counts_every_reason_as_zero() -> None:
    outcome = DEFAULT_POLICY.apply([])
    assert outcome.records == ()
    assert dict(outcome.withheld) == dict.fromkeys(WithheldReason, 0)
    assert outcome.trimmed == NO_TRIM


# -- the rules are data ---------------------------------------------------------------


def test_the_fingerprint_is_stable_and_moves_with_every_rule() -> None:
    assert PublicationRules().fingerprint == DEFAULT_RULES.fingerprint
    variants = [
        PublicationRules(allowed={EventKind.DECISION_RECORDED: frozenset({"title"})}),
        PublicationRules(chatter=frozenset({EventKind.TOOL_INVOKED})),
        PublicationRules(withheld_provenance=frozenset()),
        PublicationRules(email_token="[address]"),
        PublicationRules(scheme="another/v1"),
    ]
    prints = {rules.fingerprint for rules in variants} | {DEFAULT_RULES.fingerprint}
    assert len(prints) == len(variants) + 1


def test_the_allowlist_is_copied_so_the_caller_cannot_widen_it_afterwards() -> None:
    allowed = {EventKind.DECISION_RECORDED: frozenset({"title"})}
    rules = PublicationRules(allowed=allowed)
    allowed[EventKind.BUDGET_SPENT] = frozenset({"dollars"})

    assert EventKind.BUDGET_SPENT not in rules.allowed
    with pytest.raises(TypeError):
        rules.allowed[EventKind.BUDGET_SPENT] = frozenset()  # type: ignore[index]


def test_a_widened_rule_set_publishes_what_it_names() -> None:
    rules = PublicationRules(
        allowed={**DEFAULT_ALLOWLIST, EventKind.BUDGET_SPENT: frozenset({"dollars"})},
        withheld_provenance=frozenset(),
    )
    policy = PublicationPolicy(rules)

    assert _published(_event(kind=EventKind.BUDGET_SPENT, payload={"dollars": 2}), policy)[0] == {
        "dollars": 2
    }
    assert policy.decide(_event(provenance=Provenance.UNTRUSTED)).record is not None


def test_trim_counts_add_field_by_field() -> None:
    total = TrimCounts(1, 2, 3, 4).plus(TrimCounts(10, 20, 30, 40))
    assert total == TrimCounts(11, 22, 33, 44)
    assert total.total == 110


# -- properties -------------------------------------------------------------------------

_SENTINEL = "WITHHELD-" + uuid4().hex
_NAMES = sorted({name for names in DEFAULT_ALLOWLIST.values() for name in names})
_JSON_LEAVES = st.one_of(
    st.none(), st.booleans(), st.integers(), st.text(max_size=20), st.floats(allow_nan=False)
)
_JSON = st.recursive(
    _JSON_LEAVES,
    lambda children: (
        st.lists(children, max_size=3) | st.dictionaries(st.text(max_size=8), children, max_size=3)
    ),
    max_leaves=5,
)


@st.composite
def _ledger_events(draw: st.DrawFn) -> LedgerEvent:
    kind = draw(st.sampled_from(sorted(EventKind)))
    kept = draw(st.dictionaries(st.sampled_from(_NAMES), _JSON, max_size=4))
    hidden_names = draw(
        st.lists(st.text(min_size=1, max_size=10), max_size=4).map(
            lambda names: [name for name in names if name not in DEFAULT_ALLOWLIST.get(kind, ())]
        )
    )
    payload: dict[str, object] = dict(kept)
    for name in hidden_names:
        payload[name] = f"{_SENTINEL} {name}"
    payload["repo_path"] = f"{_SENTINEL} repo"
    return _event(
        draw(st.integers(min_value=1, max_value=10_000)),
        kind=kind,
        provenance=draw(st.sampled_from(sorted(Provenance))),
        engine_id=draw(st.none() | st.sampled_from(sorted(EngineId))),
        payload=payload,
    )


# Generation is cheap but shares the machine with every other xdist worker; the
# property is about content, not speed, so neither clock is allowed to fail it.
@settings(max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.lists(_ledger_events(), max_size=8))
def test_no_withheld_field_ever_appears_in_what_is_published(
    events: list[LedgerEvent],
) -> None:
    policy = PublicationPolicy(redactor=_Redactor())
    outcome = policy.apply(events)

    assert len(outcome.records) + outcome.events_withheld == len(events)
    for record in outcome.records:
        allowed = DEFAULT_ALLOWLIST[record.kind] - NEVER_PUBLISHED_FIELDS
        assert set(record.payload) <= allowed
        assert record.kind not in ENGINE_CHATTER
        assert record.provenance is not Provenance.UNTRUSTED
        assert record.digest == digest_event(record.payload)
        text = json.dumps(LEDGER_RECORDS.to_fields(record), default=str)
        assert _SENTINEL not in text
    for event in events:
        decision = policy.decide(event)
        assert (decision.record is None) != (decision.withheld is None)
