# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Sub-doctrine 12.g for the workflows: no automation wastes a person's time, and no
automation buys that speed with what a check measures (ADR-0050).

Both halves are here because either alone is a trap. A workflow with no concurrency group
lets superseded runs keep a starved runner pool busy deciding things about commits that no
longer exist; a workflow that cancels the wrong runs turns a required check into one that
never reports, which looks exactly like a check that passed quickly.

The measurements that produced these rules, taken over the hundred runs of each workflow
before they were written:

  - `ci.yml` had no concurrency group at all. Thirteen pull-request runs kept going after
    a newer commit replaced them, for 181 minutes of wall clock. The cost is not mainly
    the machine: in the worst run observed, the last job began 63.1 minutes after the run
    started while the longest job took 12.1, so the pool is queue-bound and a dead run's
    slots are taken from live work.
  - `delivery-estimate.yml` keyed one group on the repository, so every event contended
    with every other. 72 of 100 runs were cancelled, 50 of them pull requests whose
    read-only estimate never reported.
  - `provenance.yml` cancels and handles `push` and `merge_group`, which looks like the
    same defect and is not. On those events it runs `vibey-gh check --ci` over the WHOLE
    repository, so a cancelled run is subsumed by the next; on a pull request its group
    is per-pull-request, so it only ever cancels its own older run. It is deliberately
    unchanged, and `test_a_cancelling_workflow_loses_no_coverage` states why in a form
    that fails if that stops being true.

Module-level test functions rather than a class with an interface beside it (ADR-0016),
for the reason tests/meta/test_tools_matrix_covers_every_package.py gives: pytest collects
`test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO / ".github" / "workflows"

# Events whose run nobody will ever read once a newer commit exists, so cancelling one
# costs nothing. Every other event is presumed to be a run somebody or something needs.
DISPOSABLE = frozenset({"pull_request", "pull_request_target"})

# Whether cancelling a run loses coverage is a fact about what the workflow computes, and
# it is not derivable from the file: `vibey-gh check --ci` and `vibey-gh forecast` are both
# whole-state recomputes, while `check --ci --commits A..B` is a window that a cancelled run
# would simply skip. The first draft of this test tried to infer it by matching the command,
# which is a whitelist wearing a rule's clothes -- it passed `provenance` and failed
# `delivery-estimate` for no better reason than that one command was in the pattern.
#
# So the claim is DECLARED where a reviewer reads it, in the concurrency block itself, the
# same way `[install] self_source` is declared rather than searched for. The marker is not
# ceremony: it states which claim is being made, and it arrives in a diff.
SAFE_TO_CANCEL = "# 12.g-whole-state:"
CONCURRENCY_BLOCK = re.compile(r"^concurrency:\n((?:[ \t]+.*\n|\n)*)", re.M)


def workflows() -> list[Path]:
    found = sorted(WORKFLOWS.glob("*.yml"))
    assert found, f"no workflows under {WORKFLOWS}"
    return found


def load(path: Path) -> dict:
    parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    # `on` is the YAML 1.1 boolean `True`; safe_load gives that key, not the string.
    parsed["on"] = parsed.get("on", parsed.get(True, {})) or {}
    return parsed


def triggers(spec: dict) -> set[str]:
    on = spec["on"]
    if isinstance(on, str):
        return {on}
    return set(on if isinstance(on, list) else on.keys())


def cancels(spec: dict) -> str | None:
    """The workflow's `cancel-in-progress`, as written, or None when it has no group."""
    group = spec.get("concurrency")
    if not isinstance(group, dict):
        return None
    value = group.get("cancel-in-progress", False)
    return "true" if value is True else "false" if value is False else str(value)


# --------------------------------------------------------------------------- the waste


def test_ci_supersedes_its_own_pull_request_runs() -> None:
    """The regression guard for the thing that was actually measured.

    CI is this repository's most expensive automation -- 45 jobs, 57 machine-minutes --
    and it is queue-bound, so a superseded run does not merely cost money, it delays the
    run somebody is waiting for.
    """
    spec = load(WORKFLOWS / "ci.yml")
    assert isinstance(spec.get("concurrency"), dict), (
        "ci.yml must declare a concurrency group -- without one every superseded "
        "pull-request run keeps 45 jobs' worth of runner slots (12.g)"
    )
    assert cancels(spec) != "false", (
        "ci.yml must supersede its own pull-request runs; a group that never cancels "
        "only queues the dead runs behind the live one"
    )


@pytest.mark.parametrize("path", workflows(), ids=lambda p: p.name)
def test_a_pull_request_workflow_supersedes_its_own_runs(path: Path) -> None:
    """A run of a pull request's previous commit is measurement nobody will read.

    This is the cheap, universal half of 12.g: it costs nothing to stop, and leaving it
    running takes a runner from work that is still wanted.
    """
    spec = load(path)
    if not (triggers(spec) & DISPOSABLE):
        pytest.skip("does not respond to pull requests")
    assert isinstance(spec.get("concurrency"), dict), (
        f"{path.name} runs on pull requests and declares no concurrency group, so every "
        "superseded commit's run continues to completion (12.g)"
    )
    assert cancels(spec) != "false", (
        f"{path.name} declares a group that never cancels, so a superseded "
        "pull-request run is queued rather than stopped"
    )


# ---------------------------------------------------------------------------- the bound


@pytest.mark.parametrize("path", workflows(), ids=lambda p: p.name)
def test_a_cancelling_workflow_loses_no_coverage(path: Path) -> None:
    """12.g's bound: speed is never bought with what a check measures.

    A `push` or `merge_group` run is not disposable. Cancelling one means a merged commit
    carries no conclusion from this workflow at all, and ADR-0036 records what a queue run
    that never reports costs: the pull request is ejected.

    A workflow may still cancel those runs on one condition -- that losing the run loses
    no coverage, because what it checks is whole-state rather than a range. `provenance`
    qualifies and is why this is a condition rather than a prohibition.
    """
    spec = load(path)
    exposed = triggers(spec) & {"push", "merge_group"}
    if not exposed or cancels(spec) != "true":
        pytest.skip("does not cancel runs it cannot afford to lose")
    block = CONCURRENCY_BLOCK.search(path.read_text(encoding="utf-8"))
    assert block and SAFE_TO_CANCEL in block.group(1), (
        f"{path.name} cancels {sorted(exposed)} runs unconditionally, so a commit can end up "
        "with no conclusion from it. That is allowed only where the check is whole-state, so "
        "a later run subsumes the cancelled one -- and because that cannot be read off the "
        "file, it must be claimed in the concurrency block:\n\n"
        f"    {SAFE_TO_CANCEL} <what makes a cancelled run lose nothing>\n\n"
        "Otherwise scope `cancel-in-progress` to pull requests, as ci.yml does "
        "(12.g, ADR-0036)."
    )


def test_the_ledger_refresh_keeps_its_mutex() -> None:
    """Splitting the estimate's lanes must not have unlocked the one that writes.

    Non-pull-request events refresh the published ledger and commit it, so they must keep
    contending for a single repository-wide slot. The read-only pull-request lane was
    separated from them; this asserts the separation went the right way round, because a
    group keyed per pull request for BOTH lanes would let two ledger writers overlap.
    """
    workflow = load(WORKFLOWS / "delivery-estimate.yml")
    group = workflow["concurrency"]["group"]
    assert "github.repository" in group, (
        "the ledger lane must stay keyed on the repository so two refreshes cannot commit at once"
    )
    # Since 2026-09-24 the estimate runs hourly and by hand only, so there is no read-only
    # pull-request lane left to separate. If one ever returns, it must get its own key
    # again: 50 of them were cancelled by the shared slot before the lanes were split (12.g).
    triggers = workflow.get("on", workflow.get(True))
    if "pull_request" in triggers:
        assert "pull_request" in group, (
            "read-only pull-request estimates must not share the ledger's single slot (12.g)"
        )
