# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What a BUILD job tells the engine about the work, besides its title.

A real run of a local 20B model spent twenty sessions on one item without producing anything
usable, and its logs show why: the whole prompt was the item's id and title, generic house
rules and the verification commands. The objective, the constraints (several of them name the
very files to reuse), the item's own acceptance criteria and the files it is meant to write were
nowhere in what it was handed. The only other source was `.vibey/context/`, which the model
had to find, and which in a worktree is whatever was last *committed* there: the accepted spec
is published to the checkout's working tree, a worktree is cut from a commit, and in that run
the folder held an earlier, unrelated job's spec (host routing in `next.config.ts`), so the
model went looking for the wrong thing in the wrong file.

So the prompt carries the brief itself, rendered here from the accepted spec and the work
item's own payload: pure text, no I/O. An item planned before the payload carried these
fields, or a project with no accepted spec, renders only what it has; with neither, nothing,
and the prompt is what it always was.
"""

from collections.abc import Mapping, Sequence
from typing import Final

from vibey.domain.spec import AcceptanceCriterion, DesignSpec

MAX_BRIEF_CHARS: Final = 14_000
"""A brief past this is cut at a line, with a note. A local model's window is the scarce thing;
the spec's rules and this item's criteria come first, so a cut loses the least."""

_TRUNCATED: Final = (
    "\n(the rest of this brief was cut for length; AGENTS.md and the files above remain)\n"
)


def render_work_item_brief(spec: DesignSpec | None, payload: Mapping[str, object]) -> str:
    """The brief for one work item, or "" when there is nothing to say."""
    sections = [
        *_what_is_being_built(spec),
        *_rules(spec),
        *_this_item(spec, payload),
        *_how_to_work(spec, payload),
    ]
    if not sections:
        return ""
    brief = "# Your task\n\n" + "\n\n".join(sections) + "\n"
    if len(brief) <= MAX_BRIEF_CHARS:
        return brief
    cut = brief[:MAX_BRIEF_CHARS].rsplit("\n", 1)[0]
    return cut + "\n" + _TRUNCATED


def _what_is_being_built(spec: DesignSpec | None) -> list[str]:
    if spec is None:
        return []
    parts = [f"## What is being built\n\n{spec.objective.strip()}"]
    if spec.walking_skeleton.strip():
        parts.append(
            f"The first slice proves the primary path end to end: {spec.walking_skeleton.strip()}"
        )
    return ["\n\n".join(parts)]


def _rules(spec: DesignSpec | None) -> list[str]:
    if spec is None:
        return []
    sections = []
    if spec.constraints:
        lines = "\n".join(
            f"- [{'must' if constraint.kind.value == 'hard' else 'prefer'}] {constraint.text.strip()}"
            for constraint in spec.constraints
        )
        sections.append(f"## Rules for all of this work (from the accepted spec)\n\n{lines}")
    if spec.non_goals:
        lines = "\n".join(f"- {goal.strip()}" for goal in spec.non_goals)
        sections.append(f"## Out of scope\n\n{lines}")
    return sections


def _this_item(spec: DesignSpec | None, payload: Mapping[str, object]) -> list[str]:
    title = str(payload.get("title", "")).strip()
    claimed = _strings(payload.get("acceptance_ids"))
    files = _strings(payload.get("files_touched_hint"))
    built_on = _strings(payload.get("depends_on_items"))
    if not (claimed or files or built_on):
        return []
    parts = [f"## Your work item: {title}" if title else "## Your work item"]
    if claimed:
        known = {criterion.criterion_id: criterion for criterion in spec.criteria} if spec else {}
        lines = [_criterion_line(known.get(criterion_id), criterion_id) for criterion_id in claimed]
        parts.append("Make these acceptance criteria true:\n" + "\n".join(lines))
    if files:
        paths = "\n".join(f"- {path}" for path in files)
        parts.append(
            "Files you are expected to create or change (start there; create any that do not "
            f"exist yet rather than searching the repository for them):\n{paths}"
        )
    if built_on:
        parts.append(
            "Earlier work items are already merged into your branch, so their code is here: "
            + ", ".join(built_on)
            + "."
        )
    return ["\n\n".join(parts)]


def _criterion_line(criterion: AcceptanceCriterion | None, criterion_id: str) -> str:
    if criterion is None:
        return f"- {criterion_id} (not found in the accepted spec)"
    return (
        f"- {criterion.criterion_id}: given {criterion.given.strip()}, when {criterion.when.strip()}, "
        f"then {criterion.then.strip()}. Measured by: {criterion.fit.strip()}"
    )


def _how_to_work(spec: DesignSpec | None, payload: Mapping[str, object]) -> list[str]:
    if spec is None and not _strings(payload.get("acceptance_ids")):
        return []
    return [
        "## How to work\n\n"
        "1. Read AGENTS.md first: it holds the repository's own conventions.\n"
        "2. Read the files above that already exist, then write the code and its tests.\n"
        "3. Everything you need to know about the task is in this brief. `.vibey/context/` in "
        "this repository may describe earlier, unrelated work: do not follow it where it "
        "disagrees with this brief.\n"
        "4. Run the verification commands below and fix what they report; do not weaken them."
    ]


def _strings(value: object) -> Sequence[str]:
    if not isinstance(value, list | tuple):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())
