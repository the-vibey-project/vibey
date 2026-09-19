# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""BUILD decomposition: the work-item graph and its two structural rules
(M6 task 6.1), per phase-protocols.md section 2.1.

`build.decompose` turns an accepted spec into a dependency-ordered work-item
graph. Two rules are checked structurally, not left to the decomposer's
judgment:

1. Every acceptance criterion maps to >= 1 work item. An unmapped criterion
   is a decomposition bug and fails the job.
2. The walking skeleton has no dependencies. It goes first, alone, and must
   go green before anything else starts.

Both, and the graph's own soundness (unique ids, known dependencies, no
cycle), are judged over the WHOLE plan before any of it is enqueued: a plan
checked item by item is only found wrong after part of it has been acted on.
A sound plan is then put into dependency order here, so the order a producer
happened to list its items in is never load-bearing.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from heapq import heapify, heappop, heappush

from vibey.domain.effort import Effort
from vibey.domain.interfaces.plan_interface import (
    DecompositionPlannerInterface,
    PlannedItemInterface,
)


@dataclass(frozen=True, slots=True)
class VerificationSpec:
    """Exactly how a work item's completion will be checked."""

    commands: tuple[str, ...]
    criteria_checked: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WorkItem:
    item_id: str
    title: str
    acceptance_ids: tuple[str, ...]
    depends_on: tuple[str, ...]
    est_effort: Effort
    files_touched_hint: tuple[str, ...]
    verification: VerificationSpec


class DecompositionPlanner:
    """Judges a decomposition as a whole, then puts it in dependency order.

    Stateless: one instance serves every caller, and a deployment that wants
    different rules substitutes its own at the `DecompositionPlannerInterface`
    seam rather than editing this.
    """

    def violations(
        self,
        items: Sequence[PlannedItemInterface],
        *,
        criteria_ids: Sequence[str],
        walking_skeleton_item_id: str,
    ) -> tuple[str, ...]:
        """Returns every violation, each named; empty means the decomposition
        can enter BUILD."""
        violations: list[str] = []

        ids = [item.item_id for item in items]
        duplicates = {item_id for item_id in ids if ids.count(item_id) > 1}
        if duplicates:
            violations.append(f"duplicate item_id(s): {', '.join(sorted(duplicates))}")

        known_ids = set(ids)
        for item in items:
            for dep in item.depends_on:
                if dep not in known_ids:
                    violations.append(f"item {item.item_id!r} depends on unknown item {dep!r}")

        violations.extend(self._cycles(items))

        mapped = {acceptance_id for item in items for acceptance_id in item.acceptance_ids}
        unmapped = [criterion_id for criterion_id in criteria_ids if criterion_id not in mapped]
        if unmapped:
            violations.append(
                f"{len(unmapped)} acceptance criterion/criteria unmapped: {', '.join(unmapped)}"
            )

        skeleton = next((item for item in items if item.item_id == walking_skeleton_item_id), None)
        if skeleton is None:
            violations.append(f"walking skeleton item {walking_skeleton_item_id!r} not found")
        elif skeleton.depends_on:
            violations.append(
                f"walking skeleton item {walking_skeleton_item_id!r} must have no "
                f"dependencies, has {len(skeleton.depends_on)}"
            )

        return tuple(violations)

    def in_dependency_order[ItemT: PlannedItemInterface](
        self, items: Sequence[ItemT]
    ) -> tuple[ItemT, ...]:
        """The same items, every dependency before its dependents.

        Stable: of the items ready at any point, the one the producer listed
        first goes next, so an already-ordered plan comes back unchanged and
        the walking skeleton -- listed first, depending on nothing -- stays
        first. Defined only for a plan `violations` accepts; a cycle raises
        ValueError rather than returning part of the plan.
        """
        position = {item.item_id: index for index, item in enumerate(items)}
        waits_for = [
            {position[dep] for dep in item.depends_on if dep in position} for item in items
        ]
        dependents: list[list[int]] = [[] for _ in items]
        for index, deps in enumerate(waits_for):
            for dep in deps:
                dependents[dep].append(index)
        outstanding = [len(deps) for deps in waits_for]

        ready = [index for index, count in enumerate(outstanding) if count == 0]
        heapify(ready)
        order: list[int] = []
        while ready:
            index = heappop(ready)
            order.append(index)
            for dependent in dependents[index]:
                outstanding[dependent] -= 1
                if outstanding[dependent] == 0:
                    heappush(ready, dependent)

        if len(order) != len(items):
            raise ValueError(
                "decomposition cannot be put in dependency order: it has a dependency "
                "cycle (violations() names it)"
            )
        return tuple(items[index] for index in order)

    def _cycles(self, items: Sequence[PlannedItemInterface]) -> list[str]:
        """One violation per group of items that wait on each other -- a
        strongly connected component, found by mutual reachability, which is
        plenty for a plan of tens of items. Unknown dependencies are ignored
        here; they are reported as unknown, not as cycles."""
        known = {item.item_id for item in items}
        graph = {
            item.item_id: tuple(dep for dep in item.depends_on if dep in known) for item in items
        }
        reach = {item_id: self._reachable(item_id, graph) for item_id in graph}
        cyclic = [item_id for item_id in graph if item_id in reach[item_id]]

        violations: list[str] = []
        reported: set[str] = set()
        for item_id in cyclic:
            if item_id in reported:
                continue
            group = [
                other for other in cyclic if other in reach[item_id] and item_id in reach[other]
            ]
            reported.update(group)
            if len(group) == 1:
                violations.append(f"item {item_id!r} depends on itself")
            else:
                violations.append(
                    f"dependency cycle: items {', '.join(repr(i) for i in group)} "
                    "wait on each other, so none of them can ever start"
                )
        return violations

    def _reachable(self, start: str, graph: dict[str, tuple[str, ...]]) -> set[str]:
        """Every item reachable from `start` by one or more dependency edges."""
        seen: set[str] = set()
        stack = list(graph[start])
        while stack:
            node = stack.pop()
            if node not in seen:
                seen.add(node)
                stack.extend(graph[node])
        return seen


# The published default planner. The annotation is load-bearing: a
# `runtime_checkable` Protocol only checks member names at runtime, so this
# assignment is what makes `mypy --strict` verify `DecompositionPlanner`
# against the declared seam.
DECOMPOSITION_PLANNER: DecompositionPlannerInterface = DecompositionPlanner()


def validate_decomposition(
    items: Sequence[WorkItem],
    *,
    criteria_ids: Sequence[str],
    walking_skeleton_item_id: str,
) -> tuple[str, ...]:
    """Returns violations; empty means the decomposition can enter BUILD.

    A module-level function on purpose, and only as a facade over
    `DecompositionPlanner.violations`, where the rules now live (ADR-0016):
    the work-plan producers call this name to refuse a bad plan before
    returning it, and moving a seam out from under its callers is churn,
    not convergence.
    """
    return DECOMPOSITION_PLANNER.violations(
        items, criteria_ids=criteria_ids, walking_skeleton_item_id=walking_skeleton_item_id
    )


_DEFAULT_BUILD_PARALLELISM = 4


def build_parallelism(
    *,
    config_parallelism: int | None,
    eligible_items: int,
    cpu_count: int,
) -> int:
    """Return the concurrency bound for BUILD: ``min(config, eligible×2, cpu)``.

    ``config_parallelism`` comes from ``phases.build.parallelism`` in vibey.toml
    (None means use the default of 4).  ``eligible_items`` and ``cpu_count`` are
    supplied by the caller — the domain does not read them from the environment.
    """
    cfg = config_parallelism if config_parallelism is not None else _DEFAULT_BUILD_PARALLELISM
    return min(cfg, eligible_items * 2, cpu_count)
