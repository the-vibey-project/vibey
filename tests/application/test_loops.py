# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The two loops as `vibey loops` assembles them (sub-doctrines 8.b, 8.c), from descriptors
alone: which loop each engine sits in, the model and what chooses it at every effort, the
by-effort order, and the ladder."""

from vibey.application.dto import EffortChoice, EngineContext
from vibey.application.interfaces.loops import LoopCatalogInterface
from vibey.application.loops import LOOP_CATALOG, LoopCatalog
from vibey.domain.effort import BUILD_LADDER, BUILD_LADDER_EXHAUSTED, PHASE_BASE_EFFORT, Effort
from vibey.domain.engine import (
    RENAMED_ENGINES,
    EngineDescriptor,
    EngineId,
    EngineInvocation,
    EngineTier,
    Loop,
)


def _descriptor(
    engine_id: EngineId,
    *,
    tier: EngineTier = EngineTier.PAID,
    cost_out: float = 1.0,
    projection: dict[Effort, EngineInvocation] | None = None,
) -> EngineDescriptor:
    return EngineDescriptor(
        engine_id=engine_id,
        binary=f"{engine_id.value}-bin",
        min_version="0.1.0",
        state_dir=f".{engine_id.value}",
        done_marker="DONE",
        auth_env=(),
        capabilities=frozenset(),
        effort_projection=projection
        or {effort: EngineInvocation((), achieved=effort) for effort in Effort},
        session_verb="sessions",
        isolation_flags={},
        cost_per_mtok_in=0.0,
        cost_per_mtok_out=cost_out,
        context_window=1,
        tier=tier,
    )


def _context(
    descriptor: EngineDescriptor,
    *,
    enabled: bool = True,
    switch: str | None = None,
    model: str | None = None,
    on_by_default: bool = False,
) -> EngineContext:
    return EngineContext(
        descriptor=descriptor,
        enabled=enabled,
        run=("{binary}", "run", "{plan}"),
        switch=switch,
        model=model,
        on_by_default=on_by_default,
    )


def _every(argv: tuple[str, ...], *, notes: str = "") -> dict[Effort, EngineInvocation]:
    return {effort: EngineInvocation(argv, achieved=effort, notes=notes) for effort in Effort}


def test_the_shared_catalog_satisfies_its_interface() -> None:
    assert isinstance(LOOP_CATALOG, LoopCatalogInterface)


def test_the_sovereign_default_comes_first_and_each_engine_sits_in_its_tiers_loop() -> None:
    paid = _descriptor(EngineId.CLAUDELOOP)
    local = _descriptor(EngineId.QWENLOOP, tier=EngineTier.LOCAL)

    report = LoopCatalog().report([_context(paid), _context(local)])

    sovereign, paidloop = report.loops
    assert (sovereign.loop, sovereign.tier, sovereign.default, sovereign.declared_only) == (
        Loop.SOVEREIGN,
        EngineTier.LOCAL,
        True,
        False,
    )
    assert (paidloop.loop, paidloop.tier, paidloop.default, paidloop.declared_only) == (
        Loop.PAID,
        EngineTier.PAID,
        False,
        True,
    )
    assert [e.descriptor.engine_id for e in sovereign.engines] == [EngineId.QWENLOOP]
    assert [e.descriptor.engine_id for e in paidloop.engines] == [EngineId.CLAUDELOOP]


def test_the_report_names_the_efforts_the_default_loop_the_paid_default_and_the_ladder() -> None:
    report = LoopCatalog().report([])

    assert report.efforts == tuple(Effort)
    assert report.default_loop is Loop.SOVEREIGN
    assert report.paid_default_engine is EngineId.CLAUDELOOP
    assert report.ladder.phase_base == PHASE_BASE_EFFORT
    assert report.ladder.build_attempts == BUILD_LADDER
    assert report.ladder.exhausted_after == BUILD_LADDER_EXHAUSTED == 6
    assert report.ladder.rotates_when_effort_rises is True


def test_a_repealed_engine_stays_listed_and_nothing_selects_it_by_effort() -> None:
    """Canon 8.b repeals OpenCode from both loops: it is listed, for transparency, and left
    out of every by-effort view, so no consumer of `by_effort` picks it (amendment 5)."""
    engines = [
        _descriptor(EngineId.OPENCODE, tier=EngineTier.LOCAL),
        _descriptor(EngineId.QWENLOOP, tier=EngineTier.LOCAL),
    ]

    sovereign = LoopCatalog().report([_context(d) for d in engines]).loops[0]

    assert [(e.descriptor.engine_id, e.repealed) for e in sovereign.engines] == [
        (EngineId.OPENCODE, True),
        (EngineId.QWENLOOP, False),
    ]
    for effort, choices in sovereign.by_effort.items():
        assert [choice.engine_id for choice in choices] == [EngineId.QWENLOOP], effort


def test_a_loop_with_no_engines_is_still_listed_with_an_empty_view_per_effort() -> None:
    report = LoopCatalog().report([_context(_descriptor(EngineId.CLAUDELOOP))])

    sovereign = report.loops[0]
    assert sovereign.engines == ()
    assert dict(sovereign.by_effort) == {effort: () for effort in Effort}


def test_the_state_the_resolvers_gave_passes_through_untouched() -> None:
    local = _descriptor(EngineId.GPTOSSLOOP, tier=EngineTier.LOCAL)

    (engine,) = (
        LoopCatalog()
        .report(
            [
                _context(
                    local,
                    enabled=False,
                    switch="VIBEY_FEATURE_GPTOSSLOOP",
                    model="gpt-oss:20b",
                    on_by_default=True,
                )
            ]
        )
        .loops[0]
        .engines
    )

    assert (engine.enabled, engine.switch, engine.default_model, engine.on_by_default) == (
        False,
        "VIBEY_FEATURE_GPTOSSLOOP",
        "gpt-oss:20b",
        True,
    )
    assert engine.run == ("{binary}", "run", "{plan}")
    assert (engine.repealed, engine.notes) == (False, ())


def test_an_engine_whose_name_changed_meaning_says_what_it_became() -> None:
    """ADR-0060: qwenloop is the Qwen engine now; the gpt-oss engine is gptossloop."""
    local = _descriptor(EngineId.QWENLOOP, tier=EngineTier.LOCAL)

    (engine,) = LoopCatalog().report([_context(local)]).loops[0].engines

    assert engine.notes == (RENAMED_ENGINES[EngineId.QWENLOOP],)
    assert "gptossloop" in engine.notes[0]


def test_a_model_flag_names_the_model() -> None:
    cursor = _descriptor(EngineId.CURSORLOOP, projection=_every(("--model", "grok-4.5")))

    (engine,) = LoopCatalog().report([_context(cursor)]).loops[1].engines

    run = engine.efforts[0]
    assert (run.model, run.chosen_by, run.notes) == ("grok-4.5", None, "")


def test_the_model_vibey_chooses_is_used_where_no_flag_names_one() -> None:
    qwen = _descriptor(
        EngineId.QWENLOOP, tier=EngineTier.LOCAL, projection=_every(("--max-turns", "8"))
    )

    (engine,) = LoopCatalog().report([_context(qwen, model="gpt-oss:20b")]).loops[0].engines

    run = engine.efforts[0]
    assert (run.effort, run.argv, run.achieved, run.model, run.notes) == (
        Effort.TRIVIAL,
        ("--max-turns", "8"),
        Effort.TRIVIAL,
        "gpt-oss:20b",
        "",
    )


def test_when_nothing_names_the_model_the_notes_say_what_chooses_it() -> None:
    engines = [
        _descriptor(EngineId.CODEXLOOP, projection=_every((), notes="no effort control")),
        _descriptor(EngineId.CLAUDELOOP, projection=_every(("--preset", "high"))),
        _descriptor(
            EngineId.CLAUDELOOP_LOCAL,
            tier=EngineTier.LOCAL,
            projection=_every(("--profile", "local", "--preset", "low")),
        ),
        _descriptor(EngineId.AGYLOOP, projection=_every(("--model",))),
    ]

    report = LoopCatalog().report([_context(d) for d in engines])

    runs = {
        engine.descriptor.engine_id: engine.efforts[0]
        for loop in report.loops
        for engine in loop.engines
    }
    assert runs[EngineId.CODEXLOOP].model is None
    assert runs[EngineId.CODEXLOOP].notes == (
        "no effort control; codexloop-bin's own configuration chooses the model"
    )
    assert runs[EngineId.CLAUDELOOP].chosen_by == "claudeloop-bin preset high"
    assert runs[EngineId.CLAUDELOOP_LOCAL].notes == (
        "claudeloop-local-bin profile local, preset low"
    )
    # A flag that ends the argv names nothing.
    assert runs[EngineId.AGYLOOP].model is None


def test_by_effort_puts_exact_then_higher_then_lower_and_breaks_ties_by_price_then_id() -> None:
    def achieving(achieved: Effort) -> dict[Effort, EngineInvocation]:
        return {effort: EngineInvocation((), achieved=achieved) for effort in Effort}

    engines = [
        _descriptor(EngineId.AGYLOOP, cost_out=5.0, projection=achieving(Effort.STANDARD)),
        _descriptor(EngineId.CODEXLOOP, cost_out=0.5, projection=achieving(Effort.MAX)),
        _descriptor(EngineId.CURSORLOOP, cost_out=0.1, projection=achieving(Effort.LOW)),
        _descriptor(EngineId.CLAUDELOOP, cost_out=1.0, projection=achieving(Effort.STANDARD)),
        _descriptor(EngineId.QWENLOOP, cost_out=1.0, projection=achieving(Effort.STANDARD)),
    ]

    paidloop = LoopCatalog().report([_context(d) for d in engines]).loops[1]

    assert paidloop.by_effort[Effort.STANDARD] == (
        EffortChoice(EngineId.CLAUDELOOP, None, Effort.STANDARD),
        EffortChoice(EngineId.QWENLOOP, None, Effort.STANDARD),
        EffortChoice(EngineId.AGYLOOP, None, Effort.STANDARD),
        EffortChoice(EngineId.CODEXLOOP, None, Effort.MAX),
        EffortChoice(EngineId.CURSORLOOP, None, Effort.LOW),
    )


def test_an_engine_the_canon_repeals_is_reported_as_the_code_says_with_a_note() -> None:
    opencode = _descriptor(EngineId.OPENCODE, tier=EngineTier.LOCAL)

    (engine,) = LoopCatalog().report([_context(opencode)]).loops[0].engines

    assert engine.repealed is True
    assert engine.notes == (
        "sub-doctrine 8.b repeals opencode from both loops; reported here as its descriptor "
        "says, tier local",
    )
