# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The triaged-delivery bridge, measured against a real `triaged_ticket` table.

`scripts/triaged_delivery.py` takes triaged GitHub issues into Vibey one at a time. Its
autonomy gaps were measured with one scenario (`DeliveryScenario`, beside this file) run
against the bridge before and after the fix, ten passes each:

| metric                                        | before (DB mode) | after |
|-----------------------------------------------|------------------|-------|
| tickets still leased after the lease expired  | 4 of 4           | 0     |
| dispatched issues published as a PR           | 0 of 3           | 2 of 3|
| DESIGN gates answered by the bridge, no opt-in| 0 (6 once `set_state` is fixed; 2 without a store), as `adam` | 0 |
| closed issues claimed                         | 1                | 0     |
| projects active at once                       | 3                | 1     |

The tests below hold the after column, and each gap on its own.

Module-level test functions rather than a class with an interface beside it (ADR-0016):
pytest collects `test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path

import pytest

from scripts import triaged_delivery
from scripts.triage_queue import GithubTicketSource, TriageQueue
from scripts.triaged_delivery import (
    EVIDENCE_DIR,
    BridgeSettings,
    CommandResult,
    DeliveryBridge,
    DeliveryEvidence,
    Issue,
    SubprocessRunner,
)
from tests.db_roles import TestDatabaseRoles
from tests.scripts.triaged_delivery_world import DeliveryScenario, FakeWorld, ScratchTickets
from vibey.bootstrap import migrations_dir

pytestmark = pytest.mark.integration
REPOSITORY = "the-vibey-project/vibey"
AUTOMATION = "automation:triaged-delivery"


class WorldRunner:
    """The bridge's command runner, answered by the world. Can time out one worker run."""

    def __init__(self, world: FakeWorld) -> None:
        self.world = world
        self.time_out_next_worker = False

    def run(
        self, argv: Sequence[str], *, timeout: float | None = None, cwd: Path | None = None
    ) -> CommandResult:
        if self.time_out_next_worker and "worker" in argv:
            self.time_out_next_worker = False
            self.world.commands.append(list(argv))
            return CommandResult(-15, "", "", timed_out=True)
        returncode, stdout, stderr = self.world.run(list(argv))
        return CommandResult(returncode, stdout, stderr)


@pytest.fixture
def scratch() -> Iterator[tuple[FakeWorld, ScratchTickets]]:
    # Other suites drop and rebuild `public` in this worker's database; bring it back to
    # migrated-and-granted first, as they do.
    owner = os.environ["VIBEY_TEST_DATABASE_URL"]
    asyncio.run(TestDatabaseRoles.from_environ(os.environ).restore(owner, migrations_dir()))
    tickets = ScratchTickets(owner)
    tickets.reset()
    world = FakeWorld(tickets, REPOSITORY)
    yield world, tickets
    tickets.delete_projects(list(world.projects))
    tickets.reset()


def bridge(
    world: FakeWorld, tmp_path: Path, *, store: bool = True, **settings: object
) -> tuple[DeliveryBridge, WorldRunner]:
    dsn = os.environ["VIBEY_TEST_DATABASE_URL"]
    runner = WorldRunner(world)
    configured = BridgeSettings(
        repo=tmp_path,
        repository=REPOSITORY,
        database_url=dsn if store else None,
        storm_home=tmp_path / "storm",
        push_gate="push_gate.py",
        **settings,  # type: ignore[arg-type]
    )
    return (
        DeliveryBridge(
            configured,
            forge=world,
            runner=runner,
            evidence=DeliveryEvidence(tmp_path / EVIDENCE_DIR),
            store=TriageQueue(dsn, REPOSITORY) if store else None,
            source=GithubTicketSource(REPOSITORY, world) if store else None,
        ),
        runner,
    )


def evidence(tmp_path: Path, name: str) -> dict[str, object]:
    value = json.loads((tmp_path / EVIDENCE_DIR / f"{name}.json").read_text())
    assert isinstance(value, dict)
    return value


# -- the measured scenario ---------------------------------------------------------------


def test_the_scenario_meets_the_after_column(
    scratch: tuple[FakeWorld, ScratchTickets], tmp_path: Path
) -> None:
    world, tickets = scratch
    delivery, _ = bridge(world, tmp_path)
    metrics = DeliveryScenario(world, tickets).run(delivery.run_once, passes=10)
    print("AFTER-METRICS " + json.dumps(metrics, default=str))

    assert metrics["stale_leased_after_expiry"] == 0
    assert metrics["design_gates_answered_by_bridge"] == 0
    assert metrics["closed_issue_claimed"] == 0
    assert metrics["max_concurrent_active_projects"] == 1
    assert metrics["issues_dispatched"] == [1, 2, 3]
    assert metrics["issues_published"] == [1, 2]
    assert metrics["tickets_completed"] == [1, 2]
    assert metrics["ticket_states"] == {
        1: "completed",
        2: "completed",
        3: "dispatched",
        4: "blocked",
    }
    assert metrics["draft_prs"] == [True, True]
    # One pull request per project, each on a branch naming its issue and project.
    heads = sorted(world.pull_requests)
    assert [head.split("-")[0] for head in heads] == ["delivery/1", "delivery/2"]
    assert metrics["crashed_passes"] == ["pass 1: vibey new: database unavailable"]
    assert world.merge_train_calls == []  # a draft is the PR automation's to promote first


def test_with_the_opt_in_design_answers_carry_the_automations_name(
    scratch: tuple[FakeWorld, ScratchTickets], tmp_path: Path
) -> None:
    world, tickets = scratch
    delivery, _ = bridge(world, tmp_path, answer_design_defaults=True)
    metrics = DeliveryScenario(world, tickets).run(delivery.run_once, passes=10)
    print("OPT-IN-METRICS " + json.dumps(metrics, default=str))

    assert metrics["design_gates_answered_by_bridge"] > 0
    assert metrics["bridge_answer_labels"] == [AUTOMATION]
    # The review verdict is never the bridge's to give, opt-in or not.
    assert world.answered_through("bridge", kinds=("verdict",)) == 0
    assert all(a.by == "adam" for a in world.answers if a.kind == "verdict")
    project = next(p for p in world.projects.values() if p.issue_number == 1)
    recorded = evidence(tmp_path, project.project_id)
    assert recorded["design_answered_by"] == AUTOMATION
    assert recorded["design_accepted_by"] == AUTOMATION


# -- gap 1: a DESIGN gate is a person's by default ---------------------------------------


def test_design_gates_stay_parked_and_the_design_unaccepted_without_the_opt_in(
    scratch: tuple[FakeWorld, ScratchTickets], tmp_path: Path
) -> None:
    world, _ = scratch
    world.open_issue(7, "high", created_at="2026-09-01T00:00:00Z")
    delivery, _ = bridge(world, tmp_path)

    assert delivery.run_once() == 0
    (project,) = world.projects.values()
    assert len(project.open_gates()) == 2
    recorded = evidence(tmp_path, project.project_id)
    assert recorded["outcome"] == "parked_at_gate"
    assert recorded["design_gates_left_for_a_person"] == 2

    for gate in project.open_gates():  # the person answers; the spec is synthesized next
        gate.answered_by, gate.answered_through = "adam", "human"
    assert delivery.run_once() == 0
    assert project.phase == "design"
    assert not [command for command in world.commands if "accept" in command]
    assert evidence(tmp_path, project.project_id)["outcome"] == "design_awaiting_acceptance"
    assert world.answered_through("bridge") == 0


# -- gap 2: a parked project is resumed and published ------------------------------------


def test_without_a_ticket_store_the_markers_resume_and_publish_exactly_once(
    scratch: tuple[FakeWorld, ScratchTickets], tmp_path: Path
) -> None:
    world, _ = scratch
    world.open_issue(9, "medium", created_at="2026-09-01T00:00:00Z")
    delivery, _ = bridge(world, tmp_path, store=False)
    for _ in range(8):
        delivery.run_once()
        world.human_turn()

    (project,) = world.projects.values()
    assert project.phase == "done"
    comments = world.issues[9].comments
    assert sum("Delivery PR:" in comment for comment in comments) == 1
    assert delivery.run_once() == 1  # nothing left to take, and nothing published twice
    assert sum("Delivery PR:" in comment for comment in world.issues[9].comments) == 1


def test_a_human_gate_holds_the_slot_and_nothing_new_is_selected(
    scratch: tuple[FakeWorld, ScratchTickets], tmp_path: Path
) -> None:
    world, tickets = scratch
    world.open_issue(1, "high", created_at="2026-09-01T00:00:00Z")
    world.open_issue(2, "high", created_at="2026-09-02T00:00:00Z")
    delivery, _ = bridge(world, tmp_path)
    for _ in range(3):
        assert delivery.run_once() == 0

    assert [p.issue_number for p in world.projects.values()] == [1]
    assert tickets.rows()[2]["state"] == "ready"


def test_an_abandoned_project_frees_the_slot_and_blocks_its_ticket(
    scratch: tuple[FakeWorld, ScratchTickets], tmp_path: Path
) -> None:
    world, tickets = scratch
    world.open_issue(1, "high", created_at="2026-09-01T00:00:00Z")
    world.open_issue(2, "low", created_at="2026-09-02T00:00:00Z")
    delivery, _ = bridge(world, tmp_path)
    delivery.run_once()
    (project,) = world.projects.values()
    project.phase = "abandoned"

    delivery.run_once()
    rows = tickets.rows()
    assert rows[1]["state"] == "blocked"
    assert rows[2]["state"] == "dispatched"


# -- gap 3: leases are reaped, released, and carry their project -------------------------


def test_a_lease_left_by_a_killed_pass_is_reaped_by_the_next(
    scratch: tuple[FakeWorld, ScratchTickets], tmp_path: Path
) -> None:
    world, tickets = scratch
    world.open_issue(5, "high", created_at="2026-09-01T00:00:00Z")
    delivery, _ = bridge(world, tmp_path)
    store = TriageQueue(os.environ["VIBEY_TEST_DATABASE_URL"], REPOSITORY)
    store.reconcile(GithubTicketSource(REPOSITORY, world).tickets().tickets, complete=True)
    assert store.claim("a-pass-that-was-killed", 900) is not None
    tickets.let_leases_expire()

    assert delivery.run_once() == 0
    row = tickets.rows()[5]
    (project,) = world.projects.values()
    assert row["state"] == "dispatched"
    assert row["project_id"] == project.project_id


def test_a_failed_dispatch_hands_the_ticket_back_then_blocks_it(
    scratch: tuple[FakeWorld, ScratchTickets], tmp_path: Path
) -> None:
    world, tickets = scratch
    world.open_issue(6, "high", created_at="2026-09-01T00:00:00Z")
    world.fail_new_always.add(6)
    delivery, _ = bridge(world, tmp_path, max_dispatch_failures=2)

    with pytest.raises(RuntimeError, match="database unavailable"):
        delivery.run_once()
    assert tickets.rows()[6]["state"] == "ready"
    with pytest.raises(RuntimeError):
        delivery.run_once()
    assert tickets.rows()[6]["state"] == "blocked"
    assert evidence(tmp_path, "ticket-6")["dispatch_failures"] == 2


def test_a_ticket_dispatched_by_an_earlier_pass_is_adopted_not_dispatched_again(
    scratch: tuple[FakeWorld, ScratchTickets], tmp_path: Path
) -> None:
    world, tickets = scratch
    world.open_issue(3, "high", created_at="2026-09-01T00:00:00Z")
    delivery, _ = bridge(world, tmp_path)
    project_id = delivery.dispatch(
        Issue(3, "issue 3", "", bumped=False, priority="high", created_at="")
    )

    assert delivery.run_once() == 0
    assert list(world.projects) == [project_id]
    assert tickets.rows()[3]["project_id"] == project_id


# -- gap 4: a closed issue is never claimable ---------------------------------------------


def test_reconcile_retires_a_closed_issue_only_when_the_listing_is_whole(
    scratch: tuple[FakeWorld, ScratchTickets],
) -> None:
    world, tickets = scratch
    for number in (1, 2, 3):
        world.open_issue(number, "medium", created_at=f"2026-09-0{number}T00:00:00Z")
    store = TriageQueue(os.environ["VIBEY_TEST_DATABASE_URL"], REPOSITORY)
    store.reconcile(GithubTicketSource(REPOSITORY, world).tickets().tickets, complete=True)
    world.close_issue(2)
    world.close_issue(3)

    cut_off = GithubTicketSource(REPOSITORY, world, limit=1).tickets()
    assert not cut_off.complete
    assert store.reconcile(cut_off.tickets, complete=cut_off.complete) == []
    assert {n: r["state"] for n, r in tickets.rows().items()} == {
        1: "ready",
        2: "ready",
        3: "ready",
    }

    whole = GithubTicketSource(REPOSITORY, world).tickets()
    assert whole.complete
    assert store.reconcile(whole.tickets, complete=True) == [2, 3]
    assert {n: r["state"] for n, r in tickets.rows().items()} == {
        1: "ready",
        2: "blocked",
        3: "blocked",
    }
    claimed = store.claim("x", 60)
    assert claimed is not None and claimed["issue_number"] == 1
    assert store.claim("x", 60) is None


def test_set_state_records_the_project_and_clears_the_lease(
    scratch: tuple[FakeWorld, ScratchTickets], tmp_path: Path
) -> None:
    world, tickets = scratch
    world.open_issue(4, "high", created_at="2026-09-01T00:00:00Z")
    store = TriageQueue(os.environ["VIBEY_TEST_DATABASE_URL"], REPOSITORY)
    store.reconcile(GithubTicketSource(REPOSITORY, world).tickets().tickets, complete=True)
    store.claim("x", 60)
    delivery, _ = bridge(world, tmp_path)
    project_id = delivery.dispatch(Issue(4, "t", "", bumped=False, priority="high", created_at=""))

    store.set_state(4, "dispatched", project_id=project_id)
    row = tickets.rows()[4]
    assert (row["state"], row["project_id"], row["lease_expires_at"]) == (
        "dispatched",
        project_id,
        None,
    )
    store.set_state(4, "completed")  # no project given: the recorded one stays
    assert tickets.rows()[4]["project_id"] == project_id
    with pytest.raises(ValueError, match="invalid ticket state"):
        store.set_state(4, "published")


def test_release_hands_back_only_a_lease(scratch: tuple[FakeWorld, ScratchTickets]) -> None:
    world, tickets = scratch
    world.open_issue(8, "high", created_at="2026-09-01T00:00:00Z")
    store = TriageQueue(os.environ["VIBEY_TEST_DATABASE_URL"], REPOSITORY)
    store.reconcile(GithubTicketSource(REPOSITORY, world).tickets().tickets, complete=True)
    store.claim("x", 60)
    store.release(8)
    assert tickets.rows()[8]["state"] == "ready"
    store.set_state(8, "completed")
    store.release(8)
    assert tickets.rows()[8]["state"] == "completed"
    assert store.reap() == 0


# -- gap 5: publication is a draft pull request by default -------------------------------


def only(pull_requests: dict[str, dict[str, object]]) -> dict[str, object]:
    (pull_request,) = pull_requests.values()
    return pull_request


def done_project(
    world: FakeWorld, tmp_path: Path, **settings: object
) -> tuple[DeliveryBridge, str]:
    world.open_issue(11, "high", created_at="2026-09-01T00:00:00Z")
    delivery, _ = bridge(world, tmp_path, store=False, **settings)
    project_id = delivery.dispatch(Issue(11, "t", "", bumped=False, priority="high", created_at=""))
    world.projects[project_id].phase = "done"
    return delivery, project_id


def test_the_pull_request_is_a_draft_and_the_merge_train_is_left_to_it(
    scratch: tuple[FakeWorld, ScratchTickets], tmp_path: Path
) -> None:
    world, _ = scratch
    delivery, project_id = done_project(world, tmp_path)

    url = delivery.publish(project_id, 11, "t")
    assert url is not None
    assert only(world.pull_requests)["isDraft"] is True
    assert world.merge_train_calls == []
    assert evidence(tmp_path, project_id)["outcome"] == "pr_draft_awaiting_promotion"
    assert delivery.publish(project_id, 11, "t") == url  # reused, never opened twice
    assert len(world.pull_requests) == 1


def test_no_draft_opens_a_ready_pull_request_and_a_green_one_meets_the_train(
    scratch: tuple[FakeWorld, ScratchTickets], tmp_path: Path
) -> None:
    world, _ = scratch
    delivery, project_id = done_project(world, tmp_path, draft=False)

    url = delivery.publish(project_id, 11, "t")
    assert url is not None
    pr = only(world.pull_requests)
    assert pr["isDraft"] is False and pr["base"] == "develop"
    assert world.merge_train_calls == []  # no checks yet: not merge-ready
    pr["statusCheckRollup"] = [{"conclusion": "SUCCESS"}]
    delivery.publish(project_id, 11, "t")
    assert world.merge_train_calls == [url.rsplit("/", 1)[-1]]


def test_publish_refuses_a_project_that_is_not_done(
    scratch: tuple[FakeWorld, ScratchTickets], tmp_path: Path
) -> None:
    world, _ = scratch
    delivery, project_id = done_project(world, tmp_path)
    world.projects[project_id].phase = "review"
    assert delivery.publish(project_id, 11, "t") is None
    assert evidence(tmp_path, project_id)["outcome"] == "not_done"


# -- gap 6: a timed-out worker's lease is reaped, as the message says --------------------


def test_a_worker_timeout_makes_the_next_pass_run_the_queue_reaper(
    scratch: tuple[FakeWorld, ScratchTickets], tmp_path: Path
) -> None:
    world, _ = scratch
    world.open_issue(12, "high", created_at="2026-09-01T00:00:00Z")
    delivery, runner = bridge(world, tmp_path)
    runner.time_out_next_worker = True

    assert delivery.run_once() == 0
    (project,) = world.projects.values()
    recorded = evidence(tmp_path, project.project_id)
    assert (recorded["outcome"], recorded["reap_pending"]) == ("worker_timeout", True)
    reap = ["uv", "run", "vibey", "queue", "reap", "--project", project.project_id]
    assert reap not in world.commands

    assert delivery.run_once() == 0
    assert reap in world.commands
    after = evidence(tmp_path, project.project_id)
    assert (after["outcome"], after["reap_pending"]) == ("parked_at_gate", False)


# -- the seams ---------------------------------------------------------------------------


def test_settings_read_every_knob_from_the_environment(tmp_path: Path) -> None:
    default = BridgeSettings.from_environ(tmp_path, {})
    assert (default.answer_design_defaults, default.draft, default.database_url) == (
        False,
        True,
        None,
    )
    assert default.answer_by == AUTOMATION
    configured = BridgeSettings.from_environ(
        tmp_path,
        {
            "VIBEY_PG_URL": "postgresql:///x",
            "VIBEY_TRIAGED_DELIVERY_ANSWER_DESIGN_DEFAULTS": "yes",
            "VIBEY_TRIAGED_DELIVERY_DRAFT": "0",
            "VIBEY_TRIAGED_DELIVERY_VIBEY": "vibey --verbose",
            "VIBEY_TRIAGED_DELIVERY_BASE": "main",
            "VIBEY_TRIAGED_DELIVERY_LEASE_SECONDS": "60",
        },
    )
    assert configured.answer_design_defaults is True
    assert configured.draft is False
    assert configured.vibey == ("vibey", "--verbose")
    assert (configured.base, configured.lease_seconds) == ("main", 60)
    with pytest.raises(ValueError, match="ANSWER_DESIGN_DEFAULTS"):
        BridgeSettings.from_environ(
            tmp_path, {"VIBEY_TRIAGED_DELIVERY_ANSWER_DESIGN_DEFAULTS": "maybe"}
        )


def test_main_applies_flags_over_the_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    seen: list[BridgeSettings] = []

    class Stub:
        def run_once(self) -> int:
            return 7

    def production(cls: type[DeliveryBridge], settings: BridgeSettings) -> Stub:
        seen.append(settings)
        return Stub()

    monkeypatch.setattr(DeliveryBridge, "production", classmethod(production))
    monkeypatch.setenv("VIBEY_TRIAGED_DELIVERY_ANSWER_DESIGN_DEFAULTS", "1")
    monkeypatch.delenv("VIBEY_PG_URL", raising=False)
    code = triaged_delivery.main(
        ["--once", "--repo", str(tmp_path), "--no-answer-design-defaults", "--no-draft"]
    )
    assert code == 7
    (settings,) = seen
    assert (settings.answer_design_defaults, settings.draft) == (False, False)


def test_the_subprocess_runner_runs_and_stops_a_command() -> None:
    runner = SubprocessRunner()
    done = runner.run([sys.executable, "-c", "print('ok')"])
    assert (done.returncode, done.stdout.strip(), done.timed_out) == (0, "ok", False)
    stopped = runner.run([sys.executable, "-c", "import time; time.sleep(60)"], timeout=0.5)
    assert stopped.timed_out is True
    assert stopped.returncode != 0
