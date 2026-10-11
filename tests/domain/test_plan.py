# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from dataclasses import replace

import pytest

from vibey.domain.effort import Effort
from vibey.domain.interfaces import DecompositionPlannerInterface, PlannedItemInterface
from vibey.domain.plan import (
    DECOMPOSITION_PLANNER,
    DecompositionPlanner,
    VerificationSpec,
    WorkItem,
    build_parallelism,
    fold_verification_only,
    validate_decomposition,
)


def _item(item_id: str, **overrides: object) -> WorkItem:
    defaults: dict[str, object] = {
        "item_id": item_id,
        "title": f"do {item_id}",
        "acceptance_ids": (),
        "depends_on": (),
        "est_effort": Effort.LOW,
        "files_touched_hint": (),
        "verification": VerificationSpec(commands=("pytest",), criteria_checked=("AC-1",)),
    }
    defaults.update(overrides)
    return WorkItem(**defaults)  # type: ignore[arg-type]


def test_validate_decomposition_empty_when_all_rules_pass() -> None:
    items = [
        _item("skeleton", acceptance_ids=("AC-1",)),
        _item("item-2", acceptance_ids=("AC-2",), depends_on=("skeleton",)),
    ]
    violations = validate_decomposition(
        items, criteria_ids=("AC-1", "AC-2"), walking_skeleton_item_id="skeleton"
    )
    assert violations == ()


def test_validate_decomposition_flags_unmapped_criteria() -> None:
    items = [_item("skeleton", acceptance_ids=("AC-1",))]
    violations = validate_decomposition(
        items, criteria_ids=("AC-1", "AC-2"), walking_skeleton_item_id="skeleton"
    )
    assert any("AC-2" in v and "unmapped" in v for v in violations)


def test_validate_decomposition_flags_walking_skeleton_with_dependencies() -> None:
    items = [
        _item("dep", acceptance_ids=("AC-1",)),
        _item("skeleton", acceptance_ids=("AC-2",), depends_on=("dep",)),
    ]
    violations = validate_decomposition(
        items, criteria_ids=("AC-1", "AC-2"), walking_skeleton_item_id="skeleton"
    )
    assert any("no dependencies" in v for v in violations)


def test_validate_decomposition_flags_missing_walking_skeleton() -> None:
    items = [_item("item-1", acceptance_ids=("AC-1",))]
    violations = validate_decomposition(
        items, criteria_ids=("AC-1",), walking_skeleton_item_id="skeleton"
    )
    assert any("not found" in v for v in violations)


def test_validate_decomposition_flags_duplicate_item_ids() -> None:
    items = [_item("skeleton", acceptance_ids=("AC-1",)), _item("skeleton", acceptance_ids=())]
    violations = validate_decomposition(
        items, criteria_ids=("AC-1",), walking_skeleton_item_id="skeleton"
    )
    assert any("duplicate" in v and "skeleton" in v for v in violations)


def test_validate_decomposition_flags_dependency_on_unknown_item() -> None:
    items = [_item("skeleton", acceptance_ids=("AC-1",), depends_on=("ghost",))]
    violations = validate_decomposition(
        items, criteria_ids=("AC-1",), walking_skeleton_item_id="skeleton"
    )
    assert any("ghost" in v and "unknown item" in v for v in violations)


def test_validate_decomposition_reports_every_violation_at_once() -> None:
    items = [_item("skeleton", acceptance_ids=(), depends_on=("ghost",))]
    violations = validate_decomposition(
        items, criteria_ids=("AC-1",), walking_skeleton_item_id="skeleton"
    )
    assert len(violations) >= 2


# --- the plan judged whole, then ordered (#265) ---


def _ids(items: tuple[WorkItem, ...]) -> list[str]:
    return [item.item_id for item in items]


def test_the_default_planner_is_a_stateless_planner_behind_its_seam() -> None:
    assert isinstance(DECOMPOSITION_PLANNER, DecompositionPlanner)
    assert isinstance(DECOMPOSITION_PLANNER, DecompositionPlannerInterface)
    assert isinstance(_item("skeleton"), PlannedItemInterface)


def test_a_two_item_cycle_is_named_once_with_both_members() -> None:
    items = [
        _item("skeleton", acceptance_ids=("AC-1",)),
        _item("a", depends_on=("b",)),
        _item("b", depends_on=("a",)),
    ]
    violations = DecompositionPlanner().violations(
        items, criteria_ids=("AC-1",), walking_skeleton_item_id="skeleton"
    )
    cycles = [v for v in violations if "cycle" in v]
    assert cycles == [
        "dependency cycle: items 'a', 'b' wait on each other, so none of them can ever start"
    ]


def test_a_self_dependency_is_named_as_such() -> None:
    items = [_item("skeleton", acceptance_ids=("AC-1",)), _item("loop", depends_on=("loop",))]
    violations = DecompositionPlanner().violations(
        items, criteria_ids=("AC-1",), walking_skeleton_item_id="skeleton"
    )
    assert violations == ("item 'loop' depends on itself",)


def test_every_separate_cycle_is_named_and_what_merely_waits_on_one_is_not() -> None:
    items = [
        _item("skeleton", acceptance_ids=("AC-1",)),
        _item("a", depends_on=("b",)),
        _item("b", depends_on=("a",)),
        _item("downstream", depends_on=("a",)),
        _item("c", depends_on=("d", "ghost")),
        _item("d", depends_on=("c",)),
    ]
    violations = DecompositionPlanner().violations(
        items, criteria_ids=("AC-1",), walking_skeleton_item_id="skeleton"
    )
    cycles = [v for v in violations if "cycle" in v]
    assert len(cycles) == 2
    assert "'a', 'b'" in cycles[0]
    assert "'c', 'd'" in cycles[1]
    assert not any("downstream" in v for v in violations)
    # The unknown dependency is reported as unknown, never folded into a cycle.
    assert "item 'c' depends on unknown item 'ghost'" in violations


def test_the_facade_reports_cycles_too() -> None:
    items = [_item("skeleton", acceptance_ids=("AC-1",)), _item("loop", depends_on=("loop",))]
    violations = validate_decomposition(
        items, criteria_ids=("AC-1",), walking_skeleton_item_id="skeleton"
    )
    assert violations == ("item 'loop' depends on itself",)


def test_an_already_ordered_plan_comes_back_unchanged() -> None:
    items = (
        _item("skeleton"),
        _item("item-2", depends_on=("skeleton",)),
        _item("item-3", depends_on=("item-2",)),
    )
    assert DecompositionPlanner().in_dependency_order(items) == items


def test_a_forward_dependency_is_ordered_not_refused() -> None:
    items = (
        _item("skeleton"),
        _item("item-2", depends_on=("item-3",)),
        _item("item-3", depends_on=("skeleton",)),
    )
    ordered = DecompositionPlanner().in_dependency_order(items)
    assert _ids(ordered) == ["skeleton", "item-3", "item-2"]


def test_ordering_is_stable_and_waits_for_every_dependency() -> None:
    items = (
        _item("skeleton"),
        _item("join", depends_on=("left", "right")),
        _item("right", depends_on=("skeleton",)),
        _item("left", depends_on=("skeleton",)),
        _item("free"),
    )
    ordered = DecompositionPlanner().in_dependency_order(items)
    # Of the items ready together, the one listed first goes first; "join"
    # waits for BOTH of its dependencies, not just the first to land.
    assert _ids(ordered) == ["skeleton", "right", "left", "join", "free"]


def test_an_unknown_dependency_does_not_block_ordering() -> None:
    items = (_item("skeleton"), _item("item-2", depends_on=("ghost",)))
    assert DecompositionPlanner().in_dependency_order(items) == items


def test_ordering_a_cycle_raises_rather_than_returning_part_of_the_plan() -> None:
    items = (_item("skeleton"), _item("a", depends_on=("b",)), _item("b", depends_on=("a",)))
    with pytest.raises(ValueError, match="dependency cycle"):
        DecompositionPlanner().in_dependency_order(items)


# --- build_parallelism tests ---


def test_build_parallelism_picks_minimum_of_three_inputs() -> None:
    assert build_parallelism(config_parallelism=4, eligible_items=10, cpu_count=8) == 4
    assert build_parallelism(config_parallelism=4, eligible_items=1, cpu_count=8) == 2
    assert build_parallelism(config_parallelism=4, eligible_items=10, cpu_count=3) == 3


def test_build_parallelism_none_config_uses_default() -> None:
    result = build_parallelism(config_parallelism=None, eligible_items=5, cpu_count=8)
    assert result == min(4, 5 * 2, 8)


def test_build_parallelism_zero_eligible_items_returns_zero() -> None:
    assert build_parallelism(config_parallelism=4, eligible_items=0, cpu_count=8) == 0


def test_build_parallelism_always_at_least_zero() -> None:
    assert build_parallelism(config_parallelism=0, eligible_items=5, cpu_count=8) == 0


@pytest.mark.parametrize(
    ("config", "eligible", "cpu", "expected"),
    [
        (4, 3, 16, 4),
        (None, 3, 16, 4),
        (10, 2, 16, 4),
        (10, 10, 2, 2),
        (1, 100, 100, 1),
    ],
)
def test_build_parallelism_table(
    config: int | None, eligible: int, cpu: int, expected: int
) -> None:
    result = build_parallelism(config_parallelism=config, eligible_items=eligible, cpu_count=cpu)
    assert result == expected


# ── fold_verification_only ───────────────────────────────────────────────────


def _slice(
    item_id: str, criteria: tuple[str, ...], *, files: bool, **overrides: object
) -> WorkItem:
    return _item(
        item_id,
        acceptance_ids=criteria,
        files_touched_hint=("src/a.ts",) if files else (),
        verification=VerificationSpec(commands=("npm test",), criteria_checked=criteria),
        **overrides,
    )


def test_the_plan_that_prompted_it_folds_seven_items_into_four() -> None:
    """ws builds the section; c4, c9 and c10 only restate checks; c7, c8 and c11 add files."""
    items = [
        _slice("ws", ("C1", "C2", "C3", "C5", "C6"), files=True),
        _slice("c4", ("C4",), files=False, depends_on=("ws",)),
        _slice("c7", ("C7",), files=True, depends_on=("ws",)),
        _slice("c8", ("C8",), files=True, depends_on=("ws",)),
        _slice("c9", ("C9",), files=False, depends_on=("ws", "c4", "c7", "c8")),
        _slice("c10", ("C10",), files=False, depends_on=("c9",)),
        _slice("c11", ("C11",), files=True, depends_on=("c10",)),
    ]

    folded = fold_verification_only(items)

    assert [item.item_id for item in folded] == ["ws", "c7", "c8", "c11"]
    by_id = {item.item_id: item for item in folded}
    assert by_id["ws"].acceptance_ids == ("C1", "C2", "C3", "C5", "C6", "C4")
    # c9 and c10 landed on c8, the dependency listed last, which now also waits for c7.
    assert by_id["c8"].acceptance_ids == ("C8", "C9", "C10")
    assert by_id["c8"].depends_on == ("ws", "c7")
    assert by_id["c8"].verification.criteria_checked == ("C8", "C9", "C10")
    assert by_id["c8"].verification.commands == ("npm test",)  # not repeated
    # What waited on a folded item waits on what absorbed it.
    assert by_id["c11"].depends_on == ("c8",)
    # Every criterion is still claimed once somewhere.
    assert {c for item in folded for c in item.acceptance_ids} == {f"C{n}" for n in range(1, 12)}
    # And a folded plan is a sound one.
    assert (
        validate_decomposition(
            folded, criteria_ids=[f"C{n}" for n in range(1, 12)], walking_skeleton_item_id="ws"
        )
        == ()
    )


def test_an_item_with_files_is_never_folded() -> None:
    items = [_slice("a", ("C1",), files=True), _slice("b", ("C2",), files=True, depends_on=("a",))]
    assert fold_verification_only(items) == tuple(items)


def test_a_blank_path_is_not_a_file() -> None:
    blank = replace(
        _slice("check", ("C2",), files=False, depends_on=("a",)), files_touched_hint=("  ",)
    )
    folded = fold_verification_only([_slice("a", ("C1",), files=True), blank])
    assert [item.item_id for item in folded] == ["a"]


def test_an_item_with_no_files_and_nothing_to_fold_into_stays() -> None:
    skeleton = _slice("a", ("C1",), files=False)  # the first item has no dependency
    orphan = _slice("b", ("C2",), files=False, depends_on=("ghost",))  # an unknown one
    assert fold_verification_only([skeleton, orphan]) == (skeleton, orphan)


def test_folding_has_no_criteria_limit() -> None:
    full = _slice("a", tuple(f"C{n}" for n in range(1, 9)), files=True)
    check = _slice("b", ("C9",), files=False, depends_on=("a",))

    (folded,) = fold_verification_only([full, check])

    assert folded.acceptance_ids == tuple(f"C{n}" for n in range(1, 10))
