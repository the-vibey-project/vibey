# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ledger search query: built valid or not at all, before any I/O."""

from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

import pytest

from vibey.domain.engine import EngineId
from vibey.domain.interfaces import (
    ActorInterface,
    ActorResolverInterface,
    EventKindResolverInterface,
    LedgerQueryInterface,
    LedgerSearchResultInterface,
)
from vibey.domain.ledger import EventKind, Provenance, UnrecognizedEventKind, digest_event
from vibey.domain.ledger_query import (
    ACTORS,
    DEFAULT_SEARCH_LIMIT,
    DIGEST_HEX_LENGTH,
    EVENT_KINDS,
    SELF_ACTOR,
    Actor,
    ActorResolver,
    ActorScope,
    EventKindResolver,
    InvalidLedgerQuery,
    LedgerQuery,
    LedgerSearchResult,
)

T0 = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)
DIGEST = digest_event({"question_id": "q1"})


# -- actors -----------------------------------------------------------------


@pytest.mark.parametrize("engine", list(EngineId))
def test_every_engine_id_resolves_to_the_engine_column(engine: EngineId) -> None:
    assert ActorResolver().resolve(engine.value) == Actor(ActorScope.ENGINE, engine.value)


@pytest.mark.parametrize("provenance", list(Provenance))
def test_every_provenance_resolves_to_the_provenance_column(provenance: Provenance) -> None:
    resolved = ActorResolver().resolve(provenance.value)
    assert resolved == Actor(ActorScope.PROVENANCE, provenance.value)


def test_the_self_label_means_events_vibey_wrote_itself() -> None:
    assert ActorResolver().resolve(SELF_ACTOR) == Actor(ActorScope.SELF, SELF_ACTOR)


def test_labels_are_read_case_insensitively_and_trimmed() -> None:
    resolver = ActorResolver()
    assert resolver.resolve("  ClaudeLoop ").scope is ActorScope.ENGINE
    assert resolver.resolve("TRUSTED").scope is ActorScope.PROVENANCE
    assert resolver.resolve(" Vibey").scope is ActorScope.SELF


def test_a_deployment_can_choose_its_own_self_label() -> None:
    resolver = ActorResolver(self_name="Conductor")
    assert resolver.self_name == "Conductor"
    assert resolver.resolve("conductor") == Actor(ActorScope.SELF, "Conductor")
    with pytest.raises(InvalidLedgerQuery):
        resolver.resolve(SELF_ACTOR)


def test_the_self_label_wins_when_it_shadows_an_engine() -> None:
    resolver = ActorResolver(self_name=EngineId.CLAUDELOOP.value)
    assert resolver.resolve("claudeloop").scope is ActorScope.SELF


def test_an_unknown_actor_names_every_label_that_would_have_worked() -> None:
    with pytest.raises(InvalidLedgerQuery) as caught:
        ActorResolver().resolve("mallory")
    message = str(caught.value)
    assert "'mallory'" in message
    for label in [*(e.value for e in EngineId), *(p.value for p in Provenance), SELF_ACTOR]:
        assert label in message


# -- kinds ------------------------------------------------------------------


@pytest.mark.parametrize("kind", list(EventKind))
def test_a_kind_resolves_by_value_or_by_name_in_any_case(kind: EventKind) -> None:
    resolver = EventKindResolver()
    assert resolver.resolve(kind.value) is kind
    assert resolver.resolve(kind.name.lower()) is kind
    assert resolver.resolve(f" {kind.value.upper()} ") is kind


def test_a_kind_this_vibey_does_not_know_is_searched_for_as_written() -> None:
    """vibey#275: a newer vibey's kind must be findable from an older CLI."""
    resolver = EventKindResolver()
    assert resolver.accepts_unrecognized is True
    assert resolver.resolve("  FutureKindX ") == UnrecognizedEventKind("FutureKindX")
    # Case is kept: the stored text is matched exactly, and a newer vibey's
    # values are as case-sensitive as this one's.
    assert resolver.resolve("futurekindx") == UnrecognizedEventKind("futurekindx")
    assert EVENT_KINDS.resolve("FutureKindX") == UnrecognizedEventKind("FutureKindX")


def test_a_strict_resolver_refuses_an_unknown_kind_and_lists_the_kinds() -> None:
    resolver = EventKindResolver(accept_unrecognized=False)
    assert resolver.accepts_unrecognized is False
    with pytest.raises(InvalidLedgerQuery) as caught:
        resolver.resolve("Nonsense")
    assert "'Nonsense'" in str(caught.value)
    assert EventKind.FINDING_RAISED.value in str(caught.value)
    # A known kind still resolves.
    assert resolver.resolve("findingraised") is EventKind.FINDING_RAISED


@pytest.mark.parametrize("label", ["", "   "])
def test_an_empty_kind_label_is_refused_even_by_default(label: str) -> None:
    with pytest.raises(InvalidLedgerQuery, match="unknown event kind"):
        EventKindResolver().resolve(label)


def test_a_query_can_mix_known_and_unrecognized_kinds() -> None:
    kinds = frozenset({EventKind.FINDING_RAISED, UnrecognizedEventKind("FutureKindX")})
    assert LedgerQuery(kinds=kinds).kinds == kinds


# -- the query --------------------------------------------------------------


def test_an_empty_query_asks_for_the_latest_events() -> None:
    query = LedgerQuery()
    assert query.limit == DEFAULT_SEARCH_LIMIT
    assert query.kinds == frozenset()
    assert (query.event_id, query.digest, query.actor, query.text) == (None, None, None, None)
    assert (query.since, query.until) == (None, None)


def test_every_criterion_is_kept_as_given() -> None:
    event_id = uuid4()
    actor = Actor(ActorScope.ENGINE, "codexloop")
    query = LedgerQuery(
        event_id=event_id,
        digest=DIGEST,
        actor=actor,
        since=T0,
        until=T0 + timedelta(hours=1),
        kinds=frozenset({EventKind.FINDING_RAISED, EventKind.FINDING_RESOLVED}),
        text="flaky",
        limit=7,
    )
    assert query.event_id == event_id
    assert query.digest == DIGEST
    assert query.actor == actor
    assert query.kinds == {EventKind.FINDING_RAISED, EventKind.FINDING_RESOLVED}
    assert query.text == "flaky"
    assert query.limit == 7


@pytest.mark.parametrize("limit", [0, -1])
def test_a_limit_below_one_is_refused(limit: int) -> None:
    with pytest.raises(InvalidLedgerQuery, match="limit must be at least 1"):
        LedgerQuery(limit=limit)


def test_a_digest_is_normalised_to_lowercase_without_whitespace() -> None:
    assert LedgerQuery(digest=f"  {DIGEST.upper()}\n").digest == DIGEST


def test_the_digest_length_is_the_ledgers_own() -> None:
    assert len(DIGEST) == DIGEST_HEX_LENGTH


@pytest.mark.parametrize(
    "digest",
    [DIGEST[:12], DIGEST + "0", "z" * DIGEST_HEX_LENGTH, "", "test-digest-1"],
    ids=["prefix", "too-long", "not-hex", "empty", "not-a-digest"],
)
def test_anything_but_a_full_hex_digest_is_refused(digest: str) -> None:
    with pytest.raises(InvalidLedgerQuery, match="full 64-character hex SHA-256"):
        LedgerQuery(digest=digest)


@pytest.mark.parametrize("field", ["since", "until"])
def test_a_naive_bound_is_refused(field: str) -> None:
    naive = datetime(2026, 9, 18, 12, 0)
    with pytest.raises(InvalidLedgerQuery, match=f"{field} must carry a timezone"):
        LedgerQuery(**{field: naive})  # type: ignore[arg-type]


def test_bounds_in_any_zone_are_accepted() -> None:
    plus_two = timezone(timedelta(hours=2))
    query = LedgerQuery(since=T0.astimezone(plus_two), until=T0 + timedelta(seconds=1))
    assert query.since == T0


@pytest.mark.parametrize("gap", [timedelta(0), timedelta(hours=-1)], ids=["equal", "reversed"])
def test_an_empty_window_is_refused(gap: timedelta) -> None:
    with pytest.raises(InvalidLedgerQuery, match="the window is empty"):
        LedgerQuery(since=T0, until=T0 + gap)


def test_a_one_sided_window_is_fine() -> None:
    assert LedgerQuery(since=T0).until is None
    assert LedgerQuery(until=T0).since is None


def test_an_empty_needle_is_refused() -> None:
    with pytest.raises(InvalidLedgerQuery, match="text must not be empty"):
        LedgerQuery(text="")


def test_the_result_carries_the_events_and_the_truncation() -> None:
    result = LedgerSearchResult(events=(), truncated=True)
    assert result.events == ()
    assert result.truncated is True


# -- seams ------------------------------------------------------------------


def test_the_classes_satisfy_their_declared_seams() -> None:
    assert isinstance(ACTORS, ActorResolverInterface)
    assert isinstance(EVENT_KINDS, EventKindResolverInterface)
    assert isinstance(Actor(ActorScope.SELF, SELF_ACTOR), ActorInterface)
    assert isinstance(LedgerQuery(), LedgerQueryInterface)
    assert isinstance(LedgerSearchResult(events=(), truncated=False), LedgerSearchResultInterface)
