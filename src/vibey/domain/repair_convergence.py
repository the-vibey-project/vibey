# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""When a repair that changes nothing is a reason to stop repairing.

A work item whose gates fail is repaired: a finding is raised, an engine session tries to fix
it, verification runs again. That is bounded by a number of rounds, and an operator running
unattended grants more rounds when the bound is hit. Neither says whether the rounds are
getting anywhere. A real run spent about four hours and twenty sessions on one item whose build
failed identically every time (a `node_modules` with nothing installed in it, so the Next.js
package could not be found): a failure no edit to the code could change.

So the rounds are compared. A failure whose normalised text equals that of the last two
findings for the item has survived two repairs untouched, which is almost never a code problem,
and the next repair would be a third attempt at the same thing. The item parks, with the
failure quoted, for someone to look at the environment. Any human answer gives the item a
fresh history: what came before the answer is not held against it.

Pure functions only: the handlers read the ledger and the gate, and ask these.
"""

import re
from collections.abc import Iterable, Sequence
from datetime import datetime
from typing import Final

REPAIR_NOT_CONVERGING_GATE_KIND: Final = "repair_not_converging"
"""The gate an item parks on when repairs stop changing its failure. Never auto-answered."""

IDENTICAL_FAILURES_BEFORE_PARKING: Final = 2
"""How many findings in a row must read the same as a new failure for it to park. Two means two
repairs have already changed nothing; the third attempt is the one not made."""

_SIGNATURE_CHARS: Final = 1_000
"""How much of a normalised failure is compared. The head names the failure; the tail of a
long gate output is progress noise that differs from run to run."""

_PATH: Final = re.compile(r"(?:[A-Za-z]:)?(?:/[^\s/:'\"()<>]+)+/?")
_HEX: Final = re.compile(r"\b[0-9a-f]{7,}\b")
_NUMBER: Final = re.compile(r"\d+")
_SPACE: Final = re.compile(r"\s+")


def failure_signature(text: str) -> str:
    """The failure with everything that changes between identical failures taken out.

    Absolute paths (a worktree's path names its project and cycle), hex ids, numbers (line
    numbers, durations, counts) and whitespace are replaced, case is folded, and only the head
    is kept. Two failures with the same signature are the same failure.
    """
    folded = text.lower()
    for pattern, token in ((_PATH, "<path>"), (_HEX, "<id>"), (_NUMBER, "<n>")):
        folded = pattern.sub(token, folded)
    return _SPACE.sub(" ", folded).strip()[:_SIGNATURE_CHARS]


def failures_since(history: Iterable[tuple[datetime, str]], since: datetime | None) -> list[str]:
    """The failure texts raised after `since`, oldest first; all of them when `since` is None.

    `since` is when a person last answered a gate for the job: they have looked, so what was
    raised before that does not count towards the next parking.
    """
    return [text for at, text in history if since is None or at > since]


def is_not_converging(
    previous: Sequence[str],
    current: str,
    *,
    repeats: int = IDENTICAL_FAILURES_BEFORE_PARKING,
) -> bool:
    """Whether `current` reads the same as the last `repeats` of the `previous` failures.

    A failure with no text has no signature, and two of them prove nothing: it never counts.
    """
    signature = failure_signature(current)
    if not signature or len(previous) < repeats:
        return False
    return all(failure_signature(text) == signature for text in previous[-repeats:])


def not_converging_prompt(item_id: str, stage: str, repairs: int, detail: str) -> str:
    """What the parked gate says: the failure, how often it has repeated, and where to look."""
    return (
        f"work item {item_id!r} has failed {stage} the same way {repairs + 1} times running, "
        f"through {repairs} repair rounds that changed nothing; latest: {detail[:500]}. "
        "A repair that cannot change the failure is almost never a code problem: check the "
        "environment (dependencies installed, the tooling the checks run, disk space, a file "
        "they need). Fix that, then answer anything and the repairs resume with a fresh count."
    )
