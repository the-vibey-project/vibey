# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Why reviews produced a verdict or did not, counted (G2).

An audit of 150 review runs could say how often the gate was skipped (75) but not why:
every reason was prose. These pin the closed vocabulary every run records in, and the
read-only reader that tabulates those records -- including every way a record can be
missing, which is counted as exactly that and never folded into a figure.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from vibey_gh import review_outcome
from vibey_gh.review_outcome import (
    CODES,
    LANE_ARTIFACT,
    LANES,
    OUTCOME_ARTIFACT,
    REVIEW_OUTCOMES,
    OutcomeTable,
    OutcomeVocabulary,
    ReviewOutcomeReader,
    RunRecord,
)


def _gate(code: str = "reviewed", **fields: Any) -> dict:
    return {
        "schema": "vibey-gh.review-outcome/1",
        "source": "gate",
        "lane": "sovereign_whole",
        "code": code,
        "verdict": "pass" if code == "reviewed" else "none",
    } | fields


def _lane(code: str = "scans_pending") -> dict:
    return {
        "schema": "vibey-gh.review-lane/1",
        "source": "evaluate",
        "lane": "none",
        "code": code,
        "verdict": "none",
    }


class _Forge:
    """The forge client, answering from tables: runs by page, artifacts by run, and the
    record each downloadable artifact holds. Every call is recorded."""

    executable = "gh"

    def __init__(
        self,
        runs: Sequence[dict],
        artifacts: dict[int, list[dict] | Exception],
        records: dict[tuple[int, str], str | None],
    ) -> None:
        self.runs = list(runs)
        self.artifacts = artifacts
        self.records = records
        self.calls: list[list[str]] = []

    def json(self, args: Sequence[str], **_: Any) -> Any:
        self.calls.append(list(args))
        path = args[1]
        if "/actions/workflows/" in path:
            page = int(path.rsplit("page=", 1)[1])
            return {"workflow_runs": self.runs[(page - 1) * 100 : page * 100]}
        run_id = int(path.split("/actions/runs/")[1].split("/")[0])
        listed = self.artifacts.get(run_id, [])
        if isinstance(listed, Exception):
            raise listed
        return {"artifacts": listed}

    def run(self, args: Sequence[str], **_: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append(list(args))
        run_id, name = int(args[2]), args[args.index("--name") + 1]
        directory = Path(args[args.index("--dir") + 1])
        body = self.records.get((run_id, name))
        if body is None:
            return subprocess.CompletedProcess(args, 1, "", "no artifact matches\nnot found")
        if body != "<nothing>":
            (directory / review_outcome.RECORD_FILE).write_text(body, encoding="utf-8")
        return subprocess.CompletedProcess(args, 0, "", "")


def _run(run_id: int, status: str = "completed", conclusion: str | None = "failure") -> dict:
    return {
        "id": run_id,
        "created_at": f"2026-09-2{run_id % 10}T00:00:00Z",
        "status": status,
        "conclusion": conclusion,
    }


def _reader(forge: _Forge, repository: str = "owner/repo") -> ReviewOutcomeReader:
    return ReviewOutcomeReader(repository, transport=forge, clock=lambda: 1_790_000_000.0)


def test_the_vocabulary_is_closed_and_describes_every_code():
    assert REVIEW_OUTCOMES.problems(_gate()) == []
    assert REVIEW_OUTCOMES.problems(_lane()) == []
    assert all(CODES.values()) and all(LANES.values())
    for code in ("diff_exceeds_window", "model_unreachable", "model_timeout"):
        assert code in CODES
    for code in ("untrusted_author", "paid_lane_declared_off", "chunk_budget_exceeded"):
        assert code in CODES
    assert REVIEW_OUTCOMES.describe("model_timeout").startswith("the local model did not")
    assert REVIEW_OUTCOMES.describe("tired") == "not in the vocabulary: 'tired'"


def test_a_record_outside_the_vocabulary_is_malformed_never_a_new_category():
    bad = _gate(code="tired", lane="somewhere", verdict="maybe") | {"schema": "other/1"}

    assert REVIEW_OUTCOMES.problems(bad) == [
        "schema 'other/1' is not a review record",
        "lane 'somewhere' is not in the vocabulary",
        "code 'tired' is not in the vocabulary",
        "verdict 'maybe' is not in the vocabulary",
    ]
    assert REVIEW_OUTCOMES.problems({}) == [
        "missing 'schema'",
        "missing 'lane'",
        "missing 'code'",
        "missing 'verdict'",
    ]


def test_an_adopter_constructs_its_own_vocabulary():
    wider = OutcomeVocabulary(codes={**CODES, "sabbath": "the gate rests"})

    assert wider.problems(_gate(code="sabbath")) == []
    assert REVIEW_OUTCOMES.problems(_gate(code="sabbath")) != []


def test_every_run_is_answered_by_the_best_record_it_left(tmp_path):
    runs = [_run(9, status="in_progress", conclusion=None)] + [_run(n) for n in range(8, 0, -1)]
    artifacts: dict[int, list[dict] | Exception] = {
        8: [{"name": OUTCOME_ARTIFACT}, {"name": LANE_ARTIFACT}],
        7: [{"name": LANE_ARTIFACT}],
        6: [{"name": "pr-review-sovereign-12-6"}],
        5: [{"name": OUTCOME_ARTIFACT, "expired": True}],
        4: [{"name": OUTCOME_ARTIFACT}],
        3: RuntimeError("gh api: HTTP 502"),
        2: [{"name": OUTCOME_ARTIFACT}],
        1: [{"name": OUTCOME_ARTIFACT}],
    }
    records: dict[tuple[int, str], str | None] = {
        (8, OUTCOME_ARTIFACT): json.dumps(_gate(code="diff_exceeds_window", verdict="none")),
        (7, LANE_ARTIFACT): json.dumps(_lane()),
        (4, OUTCOME_ARTIFACT): None,
        (2, OUTCOME_ARTIFACT): json.dumps(_gate(code="made_up")),
        (1, OUTCOME_ARTIFACT): "<nothing>",
    }
    forge = _Forge(runs, artifacts, records)

    table = _reader(forge).tabulate(20)

    sources = {run.run_id: run.source for run in table.runs}
    assert sources == {
        9: "in_progress",
        8: "gate",
        7: "evaluate",
        6: "none",
        5: "expired",
        4: "unreadable",
        3: "unreadable",
        2: "unreadable",
        1: "unreadable",
    }
    assert table.sources() == {
        "gate": 1,
        "evaluate": 1,
        "none": 1,
        "expired": 1,
        "unreadable": 4,
        "in_progress": 1,
    }
    problems = {run.run_id: run.problem for run in table.runs}
    assert problems[4] == "could not download pr-review-outcome: not found"
    assert problems[3] == "gh api: HTTP 502"
    assert "code 'made_up' is not in the vocabulary" in problems[2]
    assert problems[1].startswith("pr-review-outcome holds no readable record.json")
    # Only readable records are counted; a malformed one never lands in a category.
    assert table.counts("code") == {"diff_exceeds_window": 1, "scans_pending": 1}
    assert table.counts("verdict") == {"none": 2}
    # Read-only: every call is a GET or a download into a scratch directory.
    assert all(call[0] in ("api", "run") for call in forge.calls)
    assert all(call[:2] == ["run", "download"] for call in forge.calls if call[0] == "run")
    assert all("--method" not in call for call in forge.calls)


def test_a_record_in_the_wrong_artifact_is_not_trusted():
    forge = _Forge(
        [_run(1)],
        {1: [{"name": OUTCOME_ARTIFACT}]},
        {(1, OUTCOME_ARTIFACT): json.dumps(_lane())},
    )

    (run,) = _reader(forge).tabulate(1).runs
    assert run.source == "unreadable"
    assert "carries a 'vibey-gh.review-lane/1' record" in run.problem


def test_a_record_that_is_not_an_object_is_unreadable():
    forge = _Forge([_run(1)], {1: [{"name": OUTCOME_ARTIFACT}]}, {(1, OUTCOME_ARTIFACT): "[1]"})

    (run,) = _reader(forge).tabulate(1).runs
    assert (run.source, run.problem) == ("unreadable", "pr-review-outcome is not a JSON object")


def test_runs_are_read_a_page_at_a_time_until_the_limit(tmp_path):
    forge = _Forge([_run(n) for n in range(250, 0, -1)], {}, {})

    table = _reader(forge).tabulate(150)

    pages = [call for call in forge.calls if "/actions/workflows/" in call[1]]
    assert [call[1].rsplit("page=", 1)[1] for call in pages] == ["1", "2"]
    assert len(table.runs) == 150 and table.runs[0].run_id == 250
    assert table.span() == {
        "runs": 150,
        "oldest": {"run_id": 101, "created_at": "2026-09-21T00:00:00Z"},
        "newest": {"run_id": 250, "created_at": "2026-09-20T00:00:00Z"},
    }
    # Fewer than a page means there are no more to ask for.
    short = _Forge([_run(n) for n in range(3, 0, -1)], {}, {})
    assert len(_reader(short).tabulate(50).runs) == 3
    assert len([c for c in short.calls if "/actions/workflows/" in c[1]]) == 1


def test_the_repository_is_named_or_left_to_the_forge_client():
    named = _Forge([_run(1)], {1: [{"name": OUTCOME_ARTIFACT}]}, {(1, OUTCOME_ARTIFACT): None})
    _reader(named, "owner/repo").tabulate(1)
    assert named.calls[0][1].startswith("repos/owner/repo/actions/workflows/pr-review.yml/runs")
    assert named.calls[-1][-2:] == ["--repo", "owner/repo"]

    inferred = _Forge([_run(1)], {1: [{"name": OUTCOME_ARTIFACT}]}, {(1, OUTCOME_ARTIFACT): None})
    table = _reader(inferred, "").tabulate(1)
    assert inferred.calls[0][1].startswith("repos/{owner}/{repo}/")
    assert "--repo" not in inferred.calls[-1]
    assert table.repository == "(the current repository)"


def test_the_table_states_its_object_source_span_and_cutoff():
    forge = _Forge(
        [_run(2), _run(1)],
        {2: [{"name": OUTCOME_ARTIFACT}], 1: []},
        {(2, OUTCOME_ARTIFACT): json.dumps(_gate(code="model_timeout", verdict="none"))},
    )

    text = _reader(forge).tabulate(5).render()

    assert text.startswith(
        "Review outcomes: owner/repo, workflow pr-review.yml, the last 2 run(s) (asked for 5);"
        " read 2026-09-21T14:13:20Z"
    )
    assert "Span: run 1 (2026-09-21T00:00:00Z) to run 2 (2026-09-22T00:00:00Z)." in text
    assert "Records: 1 gate, 0 evaluate, 1 none, 0 expired, 0 unreadable, 0 in_progress." in text
    assert "model_timeout     1  the local model did not answer in time, retries included" in text
    assert "sovereign_whole     1  no paid review is declared (8.b)" in text
    assert "Runs with no readable record:" in text
    assert "run 1 (2026-09-21T00:00:00Z, failure) none: the run left no review record" in text


def test_a_table_of_nothing_says_so():
    table = _reader(_Forge([], {}, {})).tabulate(10)

    assert table.span() == {"runs": 0}
    assert "No runs of the workflow were found, so nothing is counted." in table.render()
    unreadable = OutcomeTable(
        "o/r", "pr-review.yml", 1, "now", (RunRecord(1, "t", "failure", "none", problem=""),)
    )
    assert "(no readable records)" in unreadable.render()
    assert "run 1 (t, failure) none\n" in unreadable.render()


def test_a_record_carrying_a_code_an_older_vocabulary_lacked_is_named_not_hidden():
    record = _gate(code="retired_code")
    table = OutcomeTable(
        "o/r",
        "pr-review.yml",
        1,
        "now",
        (RunRecord(1, "t", "success", "gate", record),),
    )

    assert "retired_code     1  not in the vocabulary: 'retired_code'" in table.render()


def test_the_table_is_json_for_a_program():
    forge = _Forge(
        [_run(1)], {1: [{"name": LANE_ARTIFACT}]}, {(1, LANE_ARTIFACT): json.dumps(_lane())}
    )

    data = _reader(forge).tabulate(1).as_json()

    assert data["codes"] == {"scans_pending": 1}
    assert data["lanes"] == {"none": 1}
    assert data["sources"]["evaluate"] == 1
    assert data["runs"][0]["record"] == _lane()
    assert data["runs"][0]["source"] == "evaluate"
    assert data["span"]["runs"] == 1
    assert json.loads(json.dumps(data)) == data


def test_a_limit_below_one_is_refused():
    with pytest.raises(ValueError, match="at least 1"):
        _reader(_Forge([], {}, {})).tabulate(0)


def test_the_cli_prints_the_table_and_its_json(monkeypatch, capsys):
    from vibey_gh import cli

    forge = _Forge(
        [_run(1)],
        {1: [{"name": OUTCOME_ARTIFACT}]},
        {(1, OUTCOME_ARTIFACT): json.dumps(_gate())},
    )
    built: list[tuple[str, str]] = []

    class _Reader(ReviewOutcomeReader):
        def __init__(self, repository: str = "", *, workflow: str = "pr-review.yml") -> None:
            built.append((repository, workflow))
            super().__init__(repository, workflow=workflow, transport=forge)

    monkeypatch.setattr(review_outcome, "ReviewOutcomeReader", _Reader)

    assert cli.main(["review-outcomes", "--runs", "1", "--repo", "o/r"]) == 0
    assert "Outcome code:" in capsys.readouterr().out
    assert cli.main(["review-outcomes", "--runs", "1", "--json", "--workflow", "w.yml"]) == 0
    assert json.loads(capsys.readouterr().out)["codes"] == {"reviewed": 1}
    assert built == [("o/r", "pr-review.yml"), ("", "w.yml")]


def test_the_cli_says_why_it_could_not_read(monkeypatch, capsys):
    from vibey_gh import cli

    class _Broken(ReviewOutcomeReader):
        def tabulate(self, limit: int) -> OutcomeTable:
            raise RuntimeError("gh api: HTTP 401: Bad credentials")

    monkeypatch.setattr(review_outcome, "ReviewOutcomeReader", _Broken)

    assert cli.main(["review-outcomes"]) == 1
    assert "vibey-gh review-outcomes: gh api: HTTP 401" in capsys.readouterr().err


def test_the_seams_are_satisfied():
    from vibey_gh.interfaces import (
        OutcomeTableInterface,
        OutcomeVocabularyInterface,
        ReviewOutcomeReaderInterface,
        RunRecordInterface,
    )

    assert isinstance(REVIEW_OUTCOMES, OutcomeVocabularyInterface)
    assert isinstance(ReviewOutcomeReader(), ReviewOutcomeReaderInterface)
    table = OutcomeTable("o/r", "w", 1, "now", (RunRecord(1, "t", "c", "none"),))
    assert isinstance(table, OutcomeTableInterface)
    assert isinstance(table.runs[0], RunRecordInterface)


def test_the_real_transport_is_the_default(monkeypatch):
    from vibey_gh.gh_transport import GhTransport

    reader = ReviewOutcomeReader()
    assert isinstance(reader._gh, GhTransport)  # the default seam
