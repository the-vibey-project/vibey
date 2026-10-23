# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Multi-layer slicing of a BUILD decomposition (ADR-0092, issue #1666).

A large task is not one flat list of work items. Convergence-Driven Development
(ADR-0039) measures delivery at four nested scopes, outermost first: the project
vision, the phase or milestone, the feature set or epic, and the feature, unit or
user story. This module lays those scopes over the work-item graph a producer
returned, and turns each boundary between sibling groups into an ordering the
queue enforces.

The work item is the story: the one thing an engine builds. Everything above it is
a grouping the slicer adds, and only as many layers as the plan's size needs. A
plan that fits one group stays stories; one that does not gains epics; and so on up
through phases and the project, never past the four. Every plan therefore sits on
at least one layer, and the slicing is finished -- the whole sliced plan exists --
before any of it is enqueued, because the handler enqueues it in one transaction.

Groups are consecutive runs of a plan already in dependency order, so a group never
depends on a later one and the order that results is acyclic by construction.
"""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Final

from vibey.domain.interfaces.slicing_interface import AutoSlicerInterface
from vibey.domain.plan import WorkItem

DEFAULT_MAX_CHILDREN: Final = 8
"""The most children one group holds before the plan gains the next layer out."""


class SliceLayer(StrEnum):
    """The four CDD scopes (ADR-0039)."""

    PROJECT = "project"
    PHASE = "phase"
    EPIC = "epic"
    STORY = "story"


LAYERS_OUTER_TO_INNER: Final = (
    SliceLayer.PROJECT,
    SliceLayer.PHASE,
    SliceLayer.EPIC,
    SliceLayer.STORY,
)
_GROUP_LAYERS_INNER_TO_OUTER: Final = (SliceLayer.EPIC, SliceLayer.PHASE, SliceLayer.PROJECT)
_DEPTH: Final = {layer: depth for depth, layer in enumerate(LAYERS_OUTER_TO_INNER)}


@dataclass(frozen=True, slots=True)
class SliceNode:
    """One slice: where it sits, and the work items beneath it in execution order."""

    slice_id: str
    layer: SliceLayer
    title: str
    parent_id: str | None
    item_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SlicePlan:
    """Every slice of one decomposition, outermost first and in execution order."""

    nodes: tuple[SliceNode, ...]

    def layers_used(self) -> tuple[SliceLayer, ...]:
        used = {node.layer for node in self.nodes}
        return tuple(layer for layer in LAYERS_OUTER_TO_INNER if layer in used)

    def path_of(self, item_id: str) -> tuple[str, ...]:
        """The slice ids from the outermost group down to the item's story; empty if none."""
        by_id = {node.slice_id: node for node in self.nodes}
        story = next(
            (n for n in self.nodes if n.layer is SliceLayer.STORY and item_id in n.item_ids), None
        )
        path: list[str] = []
        node = story
        while node is not None:
            path.append(node.slice_id)
            node = by_id.get(node.parent_id) if node.parent_id is not None else None
        return tuple(reversed(path))

    def titles_of(self, item_id: str) -> tuple[str, ...]:
        """The titles along `path_of`, so a job can say which feature set it serves."""
        by_id = {node.slice_id: node for node in self.nodes}
        return tuple(by_id[slice_id].title for slice_id in self.path_of(item_id))

    def violations(self, item_ids: Sequence[str]) -> tuple[str, ...]:
        """Every way the slicing is unsound for `item_ids`; empty means it can be used."""
        violations: list[str] = []
        ids = [node.slice_id for node in self.nodes]
        for slice_id in sorted({i for i in ids if ids.count(i) > 1}):
            violations.append(f"duplicate slice id {slice_id!r}")

        by_id = {node.slice_id: node for node in self.nodes}
        for node in self.nodes:
            if node.parent_id is None:
                continue
            parent = by_id.get(node.parent_id)
            if parent is None:
                violations.append(f"slice {node.slice_id!r} has unknown parent {node.parent_id!r}")
            elif _DEPTH[parent.layer] >= _DEPTH[node.layer]:
                violations.append(
                    f"slice {node.slice_id!r} ({node.layer}) has parent {parent.slice_id!r} "
                    f"({parent.layer}), which is not on an outer layer"
                )

        violations.extend(self._story_violations(item_ids))
        violations.extend(self._group_violations())
        return tuple(violations)

    def _story_violations(self, item_ids: Sequence[str]) -> list[str]:
        violations: list[str] = []
        stories = [node for node in self.nodes if node.layer is SliceLayer.STORY]
        placed: dict[str, int] = defaultdict(int)
        for story in stories:
            if len(story.item_ids) != 1:
                violations.append(f"story {story.slice_id!r} must hold exactly one item")
            for item_id in story.item_ids:
                placed[item_id] += 1
        known = set(item_ids)
        for item_id in item_ids:
            if placed[item_id] == 0:
                violations.append(f"item {item_id!r} is in no story")
        for item_id, count in sorted(placed.items()):
            if count > 1:
                violations.append(f"item {item_id!r} is in more than one story")
            if item_id not in known:
                violations.append(f"story holds unknown item {item_id!r}")
        return violations

    def _group_violations(self) -> list[str]:
        children: dict[str, list[SliceNode]] = defaultdict(list)
        for node in self.nodes:
            if node.parent_id is not None:
                children[node.parent_id].append(node)
        return [
            f"{node.layer} {node.slice_id!r} does not hold the stories beneath it"
            for node in self.nodes
            if node.layer is not SliceLayer.STORY
            and node.item_ids != tuple(i for c in children[node.slice_id] for i in c.item_ids)
        ]


@dataclass(frozen=True, slots=True)
class _Draft:
    """A slice before its parent is known."""

    layer: SliceLayer
    title: str
    item_ids: tuple[str, ...]
    children: tuple["_Draft", ...]


class AutoSlicer:
    """Slices a decomposition into as many CDD layers as its size calls for, and orders
    the groups. Stateless but for its one setting; a deployment that wants other rules
    substitutes its own at the `AutoSlicerInterface` seam."""

    def __init__(self, *, max_children: int = DEFAULT_MAX_CHILDREN) -> None:
        if max_children < 2:
            raise ValueError(
                f"max_children must be at least 2, got {max_children}: a group of one "
                "adds a layer and groups nothing"
            )
        self._max_children = max_children

    @property
    def max_children(self) -> int:
        return self._max_children

    def slice(self, items: Sequence[WorkItem]) -> SlicePlan:
        """Groups `items`, which must already be in dependency order, bottom-up."""
        level = [_Draft(SliceLayer.STORY, item.title, (item.item_id,), ()) for item in items]
        ordinals = {layer: 0 for layer in LAYERS_OUTER_TO_INNER}
        layers: tuple[SliceLayer, ...] = _GROUP_LAYERS_INNER_TO_OUTER
        if any(item.epic for item in items):
            level = self._named_epics(items, level, ordinals)
            layers = layers[1:]
        for layer in layers:
            if len(level) <= self._max_children:
                break
            grouped: list[_Draft] = []
            for chunk in self._balanced(level):
                ordinals[layer] += 1
                ids = tuple(i for draft in chunk for i in draft.item_ids)
                title = f"{layer.value.title()} {ordinals[layer]}"
                if layer is SliceLayer.EPIC:
                    title = f"{title}: {chunk[0].title}"
                grouped.append(_Draft(layer, title, ids, chunk))
            level = grouped

        nodes: list[SliceNode] = []
        counters = {layer: 0 for layer in LAYERS_OUTER_TO_INNER}
        for draft in level:
            self._flatten(draft, None, counters, nodes)
        return SlicePlan(tuple(nodes))

    def sequence(self, items: Sequence[WorkItem], plan: SlicePlan) -> tuple[WorkItem, ...]:
        """`items` with the ordering the slices prescribe: each group's entry stories also
        wait for the terminal stories of the group before it, so a group runs to completion
        before the next begins. Defined for a plan `plan.violations` accepts."""
        by_id = {item.item_id: item for item in items}
        extra: dict[str, list[str]] = defaultdict(list)
        siblings: dict[str | None, list[SliceNode]] = defaultdict(list)
        for node in plan.nodes:
            if node.layer is not SliceLayer.STORY:
                siblings[node.parent_id].append(node)
        for group in siblings.values():
            for previous, current in zip(group, group[1:], strict=False):
                waits_for = self._terminals(previous.item_ids, by_id)
                for entry in self._entries(current.item_ids, by_id):
                    extra[entry].extend(waits_for)
        return tuple(
            replace(item, depends_on=tuple(dict.fromkeys((*item.depends_on, *extra[item.item_id]))))
            if extra[item.item_id]
            else item
            for item in items
        )

    @staticmethod
    def _terminals(item_ids: Sequence[str], by_id: dict[str, WorkItem]) -> list[str]:
        """The items of a group that nothing else in the group waits for."""
        inside = set(item_ids)
        needed = {dep for i in item_ids for dep in by_id[i].depends_on if dep in inside}
        return [i for i in item_ids if i not in needed]

    @staticmethod
    def _entries(item_ids: Sequence[str], by_id: dict[str, WorkItem]) -> list[str]:
        """The items of a group that wait for nothing else in the group."""
        inside = set(item_ids)
        return [i for i in item_ids if not any(dep in inside for dep in by_id[i].depends_on)]

    def _named_epics(
        self,
        items: Sequence[WorkItem],
        stories: list[_Draft],
        ordinals: dict[SliceLayer, int],
    ) -> list[_Draft]:
        """Epics from the planner's own names: a run of consecutive items under one `epic` is
        one epic, split by size if it is over the cap, and a run with no name is an epic too,
        titled by its place. A name that returns after other work is a new epic of the same
        name -- a group is only ever a consecutive run, so the order stays sound."""
        runs: list[tuple[str, list[_Draft]]] = []
        for item, story in zip(items, stories, strict=True):
            if runs and runs[-1][0] == item.epic:
                runs[-1][1].append(story)
            else:
                runs.append((item.epic, [story]))
        epics: list[_Draft] = []
        for name, drafts in runs:
            parts = self._balanced(drafts) if len(drafts) > self._max_children else [tuple(drafts)]
            for number, part in enumerate(parts, start=1):
                ordinals[SliceLayer.EPIC] += 1
                if not name:
                    title = f"Epic {ordinals[SliceLayer.EPIC]}: {part[0].title}"
                elif len(parts) == 1:
                    title = name
                else:
                    title = f"{name} ({number}/{len(parts)})"
                ids = tuple(i for draft in part for i in draft.item_ids)
                epics.append(_Draft(SliceLayer.EPIC, title, ids, part))
        return epics

    def _balanced(self, level: list[_Draft]) -> list[tuple[_Draft, ...]]:
        """Consecutive chunks of at most `max_children`, as even as they can be: 9 under a
        cap of 8 is 5 and 4, never 8 and 1."""
        count = -(-len(level) // self._max_children)
        size, extra = divmod(len(level), count)
        chunks: list[tuple[_Draft, ...]] = []
        start = 0
        for index in range(count):
            end = start + size + (1 if index < extra else 0)
            chunks.append(tuple(level[start:end]))
            start = end
        return chunks

    def _flatten(
        self,
        draft: _Draft,
        parent_id: str | None,
        counters: dict[SliceLayer, int],
        out: list[SliceNode],
    ) -> None:
        counters[draft.layer] += 1
        if draft.layer is SliceLayer.STORY:
            slice_id = f"story-{draft.item_ids[0]}"
        else:
            slice_id = f"{draft.layer.value}-{counters[draft.layer]}"
        out.append(SliceNode(slice_id, draft.layer, draft.title, parent_id, draft.item_ids))
        for child in draft.children:
            self._flatten(child, slice_id, counters, out)


AUTO_SLICER: AutoSlicerInterface = AutoSlicer()
