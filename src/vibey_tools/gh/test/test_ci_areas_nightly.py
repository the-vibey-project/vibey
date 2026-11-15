# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The nightly's skip guard: a scheduled run whose tip is the last green one's skips (SP1-B Task 4).

The watermark is a position in the data -- the head commit of the last green scheduled run --
never a timestamp. The decision is pure and lives in `CiAreas`; reading the watermark from the
forge is `vibey_gh.ci_nightly`'s job (test_ci_nightly.py).

FAIL SAFE still rules: a skip is only ever the answer when the event is one declared to skip
(`[events] skip_unchanged`, never an event whose checks gate a merge), the head and the
watermark are both full commit ids, and they are the same commit. Anything else runs the
nightly in full.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from test_ci_areas import AREAS_TOML, PATHS, FakeRunner, real, run_areas, synthetic

from vibey_gh.ci_areas import CiAreas, CiAreasCommand
from vibey_gh.cli import main

pytestmark = pytest.mark.skipif(
    not AREAS_TOML.is_file(), reason="the repository's CI maps are not beside this tenant"
)

TIP = "a" * 40
OLDER = "b" * 40


def test_an_unchanged_tip_on_a_schedule_is_a_skip_with_a_reason() -> None:
    reasons = real().unchanged("schedule", TIP, TIP)
    assert reasons and TIP[:12] in reasons[0]


@pytest.mark.parametrize(
    ("event", "head", "last_green"),
    [
        ("schedule", TIP, OLDER),  # the tip moved: due
        ("schedule", TIP, ""),  # no green scheduled run on record: due
        ("schedule", "", TIP),  # the head is unknown: due
        ("schedule", "", ""),
        ("schedule", "abc", "abc"),  # not a commit id: never trusted to skip
        ("schedule", TIP.upper(), TIP.upper()),
        ("pull_request", TIP, TIP),  # only a declared event can skip
        ("push", TIP, TIP),
        ("merge_group", TIP, TIP),
        ("workflow_dispatch", TIP, TIP),
    ],
)
def test_anything_but_an_unchanged_scheduled_tip_runs(
    event: str, head: str, last_green: str
) -> None:
    assert real().unchanged(event, head, last_green) == ()


def test_the_skip_decision_runs_nothing_and_says_so() -> None:
    ci = real()
    decision = ci.skip_decision("unchanged")
    assert decision.skip and not decision.full and decision.areas == frozenset()
    assert decision.reasons == ("unchanged",)
    outputs = ci.outputs(decision)
    assert outputs == {
        "areas": "[]",
        "full": "false",
        "tier": "skip",
        "tools_any": "false",
        "postgres_any": "false",
        "desktop_any": "false",
    }
    for job in ("tools", "postgres-compatibility", "desktop"):
        assert ci.matrix(job, decision) == {"include": []}


def test_the_repository_declares_the_schedule_and_only_it_as_skippable() -> None:
    assert real().skip_unchanged_events == ("schedule",)


def test_the_skippable_events_default_to_the_schedule_and_are_declared_data() -> None:
    assert synthetic({"docs": ["docs/**"]}, []).skip_unchanged_events == ("schedule",)
    custom = CiAreas(
        {
            "areas": {"docs": {"paths": ["docs/**"]}},
            "full": {"paths": []},
            "events": {"skip_unchanged": ["nightly"]},
        },
        {},
    )
    assert custom.unchanged("nightly", TIP, TIP)
    assert custom.unchanged("schedule", TIP, TIP) == ()
    nothing = CiAreas(
        {
            "areas": {"docs": {"paths": ["docs/**"]}},
            "full": {"paths": []},
            "events": {"skip_unchanged": []},
        },
        {},
    )
    assert nothing.unchanged("schedule", TIP, TIP) == ()


@pytest.mark.parametrize("event", ["pull_request", "pull_request_target", "push", "merge_group"])
def test_an_event_whose_checks_gate_a_merge_can_never_be_declared_skippable(event: str) -> None:
    # A skipped required check passes on GitHub: refused at load, whatever the map says.
    with pytest.raises(ValueError, match=rf"`skip_unchanged`.*{event}"):
        CiAreas(
            {
                "areas": {"docs": {"paths": ["docs/**"]}},
                "full": {"paths": []},
                "events": {"skip_unchanged": [event]},
            },
            {},
        )


def test_a_malformed_skippable_list_is_refused() -> None:
    with pytest.raises(ValueError, match=r"\[events\] `skip_unchanged` must be a list"):
        CiAreas(
            {
                "areas": {"docs": {"paths": ["docs/**"]}},
                "full": {"paths": []},
                "events": {"skip_unchanged": "schedule"},
            },
            {},
        )


# ------------------------------------------------------------------------------ the command


def test_the_command_skips_an_unchanged_scheduled_tip_without_a_diff(capsys) -> None:
    runner = FakeRunner(stdout="docs/x.md\0")
    status, lines, err = run_areas(
        runner, capsys, event="schedule", base="", head=TIP, base_ref="develop", last_green=TIP
    )
    assert status == 0
    assert (lines["tier"], lines["full"], lines["areas"]) == ("skip", "false", "[]")
    assert lines["tools_any"] == lines["postgres_any"] == lines["desktop_any"] == "false"
    assert not [key for key in lines if key.endswith("_matrix")]
    assert runner.calls == []
    assert "skip" in err


def test_the_command_runs_a_moved_scheduled_tip_in_full(capsys) -> None:
    runner = FakeRunner()
    status, lines, _ = run_areas(
        runner, capsys, event="schedule", base="", head=TIP, base_ref="develop", last_green=OLDER
    )
    assert status == 0
    assert (lines["tier"], lines["full"]) == ("full", "true")
    assert runner.calls == []


def test_a_pull_request_is_never_skipped_even_when_handed_a_matching_watermark(capsys) -> None:
    runner = FakeRunner(stdout="docs/x.md\0")
    _, lines, _ = run_areas(runner, capsys, head=TIP, last_green=TIP)
    assert lines["tier"] == "pr"
    assert runner.calls, "the diff decides a pull request"


def test_the_json_format_reports_the_skip_tier(capsys) -> None:
    status = CiAreasCommand(runner=FakeRunner()).areas(
        base="",
        head=TIP,
        event="schedule",
        base_ref="develop",
        fmt="json",
        paths=PATHS,
        last_green=TIP,
    )
    document: dict[str, Any] = json.loads(capsys.readouterr().out)
    assert status == 0
    assert (document["tier"], document["full"], document["areas"]) == ("skip", False, [])


def test_the_cli_passes_last_green_through(capsys) -> None:
    status = main(
        [
            "ci-areas",
            "--checkout",
            str(PATHS[0]),
            "--event",
            "schedule",
            "--head",
            TIP,
            "--base-ref",
            "develop",
            "--last-green",
            TIP,
        ]
    )
    assert status == 0
    assert "tier=skip" in capsys.readouterr().out
