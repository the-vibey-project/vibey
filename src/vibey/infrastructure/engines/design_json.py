# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Decoders shared by every DESIGN and DECOMPOSE provider.

Extracted so the sovereign providers do not have to import from the paid ones. They
cross the same boundary — model text becoming domain objects — and must refuse
malformed input in the same way, so the refusals belong in one place (ADR-0027:
decoders are shared, not imported from the paid path).
"""

import json
import re
from collections.abc import Sequence

from vibey.application.design import DesignEvent
from vibey.domain.effort import Effort
from vibey.domain.plan import VerificationSpec, WorkItem, validate_decomposition
from vibey.domain.spec import DesignSpec


def events_json(events: Sequence[DesignEvent]) -> str:
    """The ledger a provider reasons over, as JSON it can be shown."""
    return json.dumps(
        [
            {
                "kind": event.kind.value,
                "provenance": event.provenance.value,
                "produced_at": event.produced_at.isoformat(),
                "payload": event.payload,
            }
            for event in events
        ],
        default=str,
    )


def as_list(value: object, field: str) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    return value


def as_object_list(value: object, field: str) -> list[dict[str, object]]:
    values = as_list(value, field)
    if not all(isinstance(item, dict) for item in values):
        raise ValueError(f"every {field} item must be an object")
    return [item for item in values if isinstance(item, dict)]


class WorkPlanDecoder:
    """Model JSON becoming `WorkItem`s, and the structural checks a plan must pass.

    Stateless. Every decompose provider -- paid or sovereign -- decodes through this, so
    a plan is refused for the same reasons whichever model produced it, and a producer
    fails fast here (with the violation named) rather than handing BuildDecomposeHandler
    something it already knows is wrong.
    """

    #: domain/worktree.py's id shape: lowercase alphanumeric and hyphens, <= 64.
    ITEM_ID_MAX = 64

    def items(self, raw_items: object) -> tuple[WorkItem, ...]:
        if not isinstance(raw_items, list) or not raw_items:
            raise ValueError("decomposition requires a non-empty items list")
        return tuple(self.item(entry) for entry in raw_items)

    def item(self, entry: object) -> WorkItem:
        if not isinstance(entry, dict):
            raise ValueError("every decomposition item must be an object")
        try:
            verification = entry.get("verification", {})
            if not isinstance(verification, dict):
                raise ValueError("verification must be an object")
            return WorkItem(
                item_id=self.slug(entry["item_id"]),
                title=str(entry["title"]),
                acceptance_ids=tuple(str(a) for a in self._list(entry.get("acceptance_ids", []))),
                depends_on=tuple(self.slug(d) for d in self._list(entry.get("depends_on", []))),
                est_effort=self._effort(entry.get("est_effort", "low")),
                files_touched_hint=tuple(
                    str(f) for f in self._list(entry.get("files_touched_hint", []))
                ),
                verification=VerificationSpec(
                    commands=tuple(str(c) for c in self._list(verification.get("commands", []))),
                    criteria_checked=tuple(
                        str(c) for c in self._list(verification.get("criteria_checked", []))
                    ),
                ),
            )
        except KeyError as exc:
            raise ValueError(f"decomposition item is missing {exc.args[0]}") from exc

    def slug(self, raw: object) -> str:
        """Deterministic projection onto domain/worktree.py's id shape.

        Caught live: a model returned ids like "WI-01" despite being asked for the
        lowercase-hyphen shape, and every downstream consumer (branch names, worktrees)
        requires it -- so the shape is guaranteed here, not requested politely.
        """
        text = re.sub(r"[^a-z0-9-]+", "-", str(raw).lower()).strip("-")[: self.ITEM_ID_MAX]
        if not text:
            raise ValueError(f"decomposition item id {raw!r} normalizes to nothing")
        return text

    def spec_json(self, spec: DesignSpec) -> dict[str, object]:
        """The accepted spec, as the JSON a decompose prompt shows the model."""
        return {
            "objective": spec.objective,
            "constraints": [{"text": c.text, "kind": c.kind.value} for c in spec.constraints],
            "non_goals": list(spec.non_goals),
            "criteria": [
                {
                    "criterion_id": c.criterion_id,
                    "given": c.given,
                    "when": c.when,
                    "then": c.then,
                    "fit": c.fit,
                }
                for c in spec.criteria
            ],
            "walking_skeleton": spec.walking_skeleton,
        }

    def require_unique(self, items: Sequence[WorkItem]) -> None:
        """Two model ids that normalise to one would become one branch; refuse that."""
        seen: set[str] = set()
        for item in items:
            if item.item_id in seen:
                raise ValueError(
                    f"model produced an invalid decomposition: duplicate item id "
                    f"{item.item_id!r} after normalization"
                )
            seen.add(item.item_id)

    def require_valid(
        self, items: Sequence[WorkItem], criteria_ids: Sequence[str], *, strict: bool = False
    ) -> None:
        """Raise naming every violation, or return; never let part of a plan through."""
        found = self.violations(items, criteria_ids, strict=strict)
        if found:
            raise ValueError(f"model produced an invalid decomposition: {'; '.join(found)}")

    def violations(
        self, items: Sequence[WorkItem], criteria_ids: Sequence[str], *, strict: bool = False
    ) -> tuple[str, ...]:
        """`validate_decomposition`, with the first item as the walking skeleton.

        `strict` adds what BuildDecomposeHandler would otherwise only discover while
        fanning the plan out -- after enqueueing part of it -- and what build.verify would
        discover later still: every dependency listed before its dependent, every item
        carrying a command its verify gate can run and a criterion it checks, and no
        criterion id the spec does not define.
        """
        if not items:
            return ("decomposition produced no work items",)
        found = list(
            validate_decomposition(
                items, criteria_ids=criteria_ids, walking_skeleton_item_id=items[0].item_id
            )
        )
        if strict:
            found.extend(self._strict_violations(items, criteria_ids))
        return tuple(found)

    def _strict_violations(
        self, items: Sequence[WorkItem], criteria_ids: Sequence[str]
    ) -> list[str]:
        found: list[str] = []
        known_criteria = set(criteria_ids)
        known_items = {item.item_id for item in items}
        earlier: set[str] = set()
        for item in items:
            # Unknown dependencies are validate_decomposition's to report; this names
            # only the ones that exist but come too late (or are the item itself).
            late = [dep for dep in item.depends_on if dep in known_items and dep not in earlier]
            if late:
                found.append(
                    f"item {item.item_id!r} depends on {', '.join(late)}, "
                    "which does not come before it"
                )
            earlier.add(item.item_id)
            if not any(command.strip() for command in item.verification.commands):
                found.append(
                    f"item {item.item_id!r} has no verification command, "
                    "so its verify gate would run nothing"
                )
            if not item.verification.criteria_checked:
                found.append(f"item {item.item_id!r} checks no acceptance criterion")
            named = {*item.acceptance_ids, *item.verification.criteria_checked}
            unknown = sorted(named - known_criteria)
            if unknown:
                found.append(
                    f"item {item.item_id!r} names criteria the spec does not define: "
                    f"{', '.join(unknown)}"
                )
        return found

    def _effort(self, raw: object) -> Effort:
        name = str(raw).upper()
        if name not in Effort.__members__:
            raise ValueError(f"decomposition item has an unknown est_effort {raw!r}")
        return Effort[name]

    def _list(self, value: object) -> list[object]:
        if not isinstance(value, list):
            raise ValueError("expected a list")
        return value
