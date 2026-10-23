# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from dataclasses import replace

import pytest

from vibey.domain.effort import Effort
from vibey.domain.interfaces import AutoSlicerInterface
from vibey.domain.plan import DECOMPOSITION_PLANNER, VerificationSpec, WorkItem
from vibey.domain.slicing import (
    AUTO_SLICER,
    DEFAULT_MAX_CHILDREN,
    LAYERS_OUTER_TO_INNER,
    AutoSlicer,
    SliceLayer,
    SliceNode,
    SlicePlan,
)


def _item(item_id: str, *depends_on: str) -> WorkItem:
    return WorkItem(
        item_id=item_id,
        title=f"do {item_id}",
        acceptance_ids=(),
        depends_on=depends_on,
        est_effort=Effort.LOW,
        files_touched_hint=("a.py",),
        verification=VerificationSpec(commands=(), criteria_checked=()),
    )


def _items(count: int) -> tuple[WorkItem, ...]:
    return tuple(_item(f"i{n:04d}") for n in range(1, count + 1))


def _layers(plan: SlicePlan) -> tuple[SliceLayer, ...]:
    return plan.layers_used()


def test_the_layers_are_the_four_cdd_scopes_outermost_first() -> None:
    assert LAYERS_OUTER_TO_INNER == (
        SliceLayer.PROJECT,
        SliceLayer.PHASE,
        SliceLayer.EPIC,
        SliceLayer.STORY,
    )


def test_the_default_slicer_satisfies_its_interface() -> None:
    assert isinstance(AUTO_SLICER, AutoSlicerInterface)
    assert AUTO_SLICER.max_children == DEFAULT_MAX_CHILDREN


@pytest.mark.parametrize("bad", [-1, 0, 1])
def test_a_slicer_that_could_never_group_is_refused(bad: int) -> None:
    with pytest.raises(ValueError, match="max_children"):
        AutoSlicer(max_children=bad)


def test_an_empty_plan_has_no_slices_and_no_violations() -> None:
    plan = AUTO_SLICER.slice(())
    assert plan.nodes == ()
    assert plan.layers_used() == ()
    assert plan.violations(()) == ()


def test_a_small_plan_is_only_stories() -> None:
    plan = AutoSlicer(max_children=8).slice(_items(5))
    assert _layers(plan) == (SliceLayer.STORY,)
    assert [node.slice_id for node in plan.nodes] == [f"story-i000{n}" for n in range(1, 6)]
    assert plan.path_of("i0003") == ("story-i0003",)


def test_a_plan_over_the_cap_is_grouped_into_balanced_epics() -> None:
    plan = AutoSlicer(max_children=8).slice(_items(9))
    assert _layers(plan) == (SliceLayer.EPIC, SliceLayer.STORY)
    epics = [node for node in plan.nodes if node.layer is SliceLayer.EPIC]
    # 9 stories under a cap of 8 split 5 + 4, never 8 + 1.
    assert [len(epic.item_ids) for epic in epics] == [5, 4]
    assert plan.path_of("i0001") == ("epic-1", "story-i0001")
    assert plan.path_of("i0009") == ("epic-2", "story-i0009")
    story = next(node for node in plan.nodes if node.slice_id == "story-i0006")
    assert story.parent_id == "epic-2"
    assert story.item_ids == ("i0006",)


def test_a_plan_over_the_cap_squared_gains_phases() -> None:
    plan = AutoSlicer(max_children=8).slice(_items(70))
    assert _layers(plan) == (SliceLayer.PHASE, SliceLayer.EPIC, SliceLayer.STORY)
    assert plan.path_of("i0001") == ("phase-1", "epic-1", "story-i0001")


def test_a_plan_over_the_cap_cubed_gains_a_project_layer() -> None:
    plan = AutoSlicer(max_children=8).slice(_items(600))
    assert _layers(plan) == LAYERS_OUTER_TO_INNER
    assert plan.path_of("i0001")[0] == "project-1"
    assert plan.violations([item.item_id for item in _items(600)]) == ()


def test_depth_stops_at_four_layers_however_large_the_plan() -> None:
    plan = AutoSlicer(max_children=2).slice(_items(40))
    assert _layers(plan) == LAYERS_OUTER_TO_INNER
    projects = [node for node in plan.nodes if node.layer is SliceLayer.PROJECT]
    assert len(projects) > 2
    assert plan.violations([item.item_id for item in _items(40)]) == ()


def test_the_slice_keeps_the_dependency_order_it_was_given() -> None:
    plan = AutoSlicer(max_children=3).slice(_items(10))
    flattened = [i for node in plan.nodes if node.layer is SliceLayer.STORY for i in node.item_ids]
    assert flattened == [item.item_id for item in _items(10)]


def _sound() -> tuple[SlicePlan, tuple[str, ...]]:
    items = _items(9)
    return AutoSlicer(max_children=8).slice(items), tuple(i.item_id for i in items)


def test_a_sliced_plan_is_sound() -> None:
    plan, ids = _sound()
    assert plan.violations(ids) == ()


def _break(plan: SlicePlan, index: int, **changes: object) -> SlicePlan:
    nodes = list(plan.nodes)
    nodes[index] = replace(nodes[index], **changes)  # type: ignore[arg-type]
    return SlicePlan(tuple(nodes))


def test_duplicate_slice_ids_are_named() -> None:
    plan, ids = _sound()
    broken = SlicePlan((*plan.nodes, plan.nodes[0]))
    assert any("duplicate slice id" in v and "epic-1" in v for v in broken.violations(ids))


def test_an_unknown_parent_is_named() -> None:
    plan, ids = _sound()
    broken = _break(plan, 2, parent_id="epic-9")
    assert any("unknown parent 'epic-9'" in v for v in broken.violations(ids))


def test_a_parent_must_sit_on_a_strictly_outer_layer() -> None:
    plan, ids = _sound()
    story = next(i for i, n in enumerate(plan.nodes) if n.layer is SliceLayer.STORY)
    other = next(
        n for n in plan.nodes if n.layer is SliceLayer.STORY and n is not plan.nodes[story]
    )
    broken = _break(plan, story, parent_id=other.slice_id)
    assert any("not on an outer layer" in v for v in broken.violations(ids))


def test_a_missing_item_is_named() -> None:
    plan, ids = _sound()
    assert any("i9999" in v and "no story" in v for v in plan.violations((*ids, "i9999")))


def test_an_item_in_two_stories_is_named() -> None:
    plan, ids = _sound()
    first_story = next(i for i, n in enumerate(plan.nodes) if n.layer is SliceLayer.STORY)
    duplicated = SlicePlan((*plan.nodes, replace(plan.nodes[first_story], slice_id="story-dup")))
    assert any("more than one story" in v for v in duplicated.violations(ids))


def test_a_story_for_an_unknown_item_is_named() -> None:
    plan, ids = _sound()
    assert any("unknown item" in v for v in plan.violations(ids[1:]))


def test_a_story_must_hold_exactly_one_item() -> None:
    plan, ids = _sound()
    index = next(i for i, n in enumerate(plan.nodes) if n.layer is SliceLayer.STORY)
    broken = _break(plan, index, item_ids=("i0001", "i0002"))
    assert any("exactly one item" in v for v in broken.violations(ids))


def test_a_group_must_hold_exactly_the_stories_beneath_it() -> None:
    plan, ids = _sound()
    broken = _break(plan, 0, item_ids=("i0001",))
    assert any("does not hold the stories beneath it" in v for v in broken.violations(ids))


def test_path_of_an_unknown_item_is_empty() -> None:
    plan, _ = _sound()
    assert plan.path_of("nope") == ()


def test_sequencing_a_plan_without_groups_changes_nothing() -> None:
    items = (_item("a"), _item("b", "a"))
    plan = AUTO_SLICER.slice(items)
    assert AUTO_SLICER.sequence(items, plan) == items


def test_each_group_waits_for_the_terminal_stories_of_the_group_before_it() -> None:
    items = _items(9)
    plan = AutoSlicer(max_children=8).slice(items)
    sequenced = {item.item_id: item for item in AUTO_SLICER.sequence(items, plan)}
    first_epic = [f"i000{n}" for n in range(1, 6)]
    for item_id in first_epic:
        assert sequenced[item_id].depends_on == ()
    for item_id in ("i0006", "i0007", "i0008", "i0009"):
        assert sequenced[item_id].depends_on == tuple(first_epic)


def test_only_a_groups_entry_stories_take_the_barrier() -> None:
    # i0006 is an entry of the second epic; i0007 already waits for it inside the epic.
    items = (*_items(5), _item("i0006"), _item("i0007", "i0006"))
    plan = AutoSlicer(max_children=4).slice(items)
    assert [len(n.item_ids) for n in plan.nodes if n.layer is SliceLayer.EPIC] == [4, 3]
    sequenced = {item.item_id: item for item in AUTO_SLICER.sequence(items, plan)}
    # The epics are i0001..i0004 and i0005..i0007; i0006 is not an entry (it is beside i0005).
    assert sequenced["i0007"].depends_on == ("i0006",)


def test_a_barrier_does_not_repeat_a_dependency_the_story_already_has() -> None:
    items = (*_items(4), _item("i0005", "i0004"))
    plan = AutoSlicer(max_children=4).slice(items)
    sequenced = {item.item_id: item for item in AUTO_SLICER.sequence(items, plan)}
    assert sequenced["i0005"].depends_on.count("i0004") == 1


def test_a_deeply_sliced_plan_stays_sound_and_runs_group_by_group() -> None:
    slicer = AutoSlicer(max_children=3)
    items = _items(30)
    plan = slicer.slice(items)
    sequenced = slicer.sequence(items, plan)

    ids = [i.item_id for i in sequenced]
    assert (
        DECOMPOSITION_PLANNER.violations(
            sequenced, criteria_ids=(), walking_skeleton_item_id=ids[0]
        )
        == ()
    )
    order = {
        i.item_id: n for n, i in enumerate(DECOMPOSITION_PLANNER.in_dependency_order(sequenced))
    }
    by_parent: dict[str | None, list[SliceNode]] = {}
    for node in plan.nodes:
        if node.layer is not SliceLayer.STORY:
            by_parent.setdefault(node.parent_id, []).append(node)
    checked = 0
    for siblings in by_parent.values():
        for previous, current in zip(siblings, siblings[1:], strict=False):
            assert max(order[i] for i in previous.item_ids) < min(
                order[i] for i in current.item_ids
            )
            checked += 1
    assert checked > 0


def _named(count: int, epic_of: "dict[int, str]") -> tuple[WorkItem, ...]:
    return tuple(replace(_item(f"i{n:04d}"), epic=epic_of.get(n, "")) for n in range(1, count + 1))


def test_consecutive_items_under_one_name_form_one_named_epic() -> None:
    items = _named(5, {1: "Parsing", 2: "Parsing", 3: "Output", 4: "Output", 5: "Output"})
    plan = AutoSlicer(max_children=8).slice(items)
    epics = [n for n in plan.nodes if n.layer is SliceLayer.EPIC]
    assert [(e.title, len(e.item_ids)) for e in epics] == [("Parsing", 2), ("Output", 3)]
    assert plan.titles_of("i0003") == ("Output", "do i0003")
    assert plan.violations([i.item_id for i in items]) == ()


def test_a_named_run_over_the_cap_is_split_and_numbered() -> None:
    items = _named(9, {n: "Core" for n in range(1, 10)})
    plan = AutoSlicer(max_children=8).slice(items)
    titles = [n.title for n in plan.nodes if n.layer is SliceLayer.EPIC]
    assert titles == ["Core (1/2)", "Core (2/2)"]


def test_unnamed_items_between_named_ones_form_epics_titled_by_place() -> None:
    items = _named(4, {1: "A", 4: "A"})
    plan = AutoSlicer(max_children=8).slice(items)
    titles = [n.title for n in plan.nodes if n.layer is SliceLayer.EPIC]
    assert titles == ["A", "Epic 2: do i0002", "A"]


def test_named_epics_still_gain_phases_when_there_are_many() -> None:
    items = _named(30, {n: f"E{n}" for n in range(1, 31)})
    plan = AutoSlicer(max_children=8).slice(items)
    assert _layers(plan) == (SliceLayer.PHASE, SliceLayer.EPIC, SliceLayer.STORY)
    sequenced = AUTO_SLICER.sequence(items, plan)
    assert (
        DECOMPOSITION_PLANNER.violations(
            sequenced, criteria_ids=(), walking_skeleton_item_id="i0001"
        )
        == ()
    )


def test_unnamed_plans_title_their_epics_by_their_first_story() -> None:
    plan = AutoSlicer(max_children=8).slice(_items(9))
    assert plan.titles_of("i0001") == ("Epic 1: do i0001", "do i0001")
