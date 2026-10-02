# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import subprocess
from argparse import Namespace
from unittest.mock import Mock, patch

from vibey_gh import cli, gh_transport, issue_triage as it


def issue(number=1, title="A feature", labels=(), created="2026-01-01T00:00:00Z"):
    return {
        "number": number,
        "title": title,
        "body": "",
        "labels": [{"name": x} for x in labels],
        "createdAt": created,
    }


def test_classification_prefers_explicit_labels_and_falls_back_conservatively():
    assert it.classify(issue(title="security outage")) == "critical"
    assert it.classify(issue(title="bug: crash")) == "high"
    assert it.classify(issue(title="add Fedora support")) == "medium"
    assert it.classify(issue(title="Question")) == "low"
    assert it.classify(issue(labels=("priority: critical",), title="feature")) == "critical"


def test_rank_orders_bumped_then_priority_then_oldest():
    values = [
        it.rank(issue(1, "new high", ("vibey-gh:priority-high",), "2026-02-01")),
        it.rank(issue(2, "bumped", (it.BUMPED,), "2026-12-01")),
        it.rank(issue(3, "old high", ("vibey-gh:priority-high",), "2026-01-01")),
    ]
    assert [x.number for x in sorted(values, key=lambda x: x.rank)] == [2, 3, 1]


def test_sweep_reconciles_all_issues_and_removes_stale_managed_labels():
    rows = [issue(2, "bug", ("vibey-gh:priority-low",)), issue(1, "feature", (it.BUMPED,))]
    with patch.object(it, "ensure_labels"), patch.object(it, "_run") as run:
        result = it.triage(rows)
    assert [x.number for x in result] == [1, 2]
    args = [call.args for call in run.call_args_list]
    assert any("--remove-label" in call and "vibey-gh:priority-low" in call for call in args)
    assert any("--add-label" in call and it.BUMPED in call for call in args)


def test_bump_and_unbump_are_explicit_reversible_operations():
    with patch.object(it, "ensure_labels"), patch.object(it, "_run") as run:
        it.set_bump(7, True)
        it.set_bump(7, False)
    assert run.call_args_list[0].args[-2:] == ("--add-label", it.BUMPED)
    assert run.call_args_list[1].args[-2:] == ("--remove-label", it.BUMPED)


def test_fetch_open_issues_uses_the_whole_open_issue_set_and_excludes_pull_requests():
    transport = Mock()
    transport.json.return_value = [issue(1), "not an issue"]
    assert [row["number"] for row in it.fetch_open_issues(transport=transport)] == [1]
    assert transport.json.call_args.args[0][-1] == "number,title,body,labels,createdAt"


def test_a_sweep_reads_and_writes_through_the_transport_it_is_given():
    transport = Mock()
    transport.json.return_value = [issue(3, "bug")]
    transport.run.return_value = subprocess.CompletedProcess([], 0, "", "")
    assert [x.number for x in it.triage(transport=transport)] == [3]
    argv = [call.args[0] for call in transport.run.call_args_list]
    assert len(argv) == len(it.LABEL_DEFINITIONS) + 1
    assert argv[-1][:3] == ("issue", "edit", "3")


def test_ensure_labels_and_command_failures_are_reported():
    completed = subprocess.CompletedProcess([], 0, "", "")
    with patch.object(gh_transport.subprocess, "run", return_value=completed) as run:
        it.ensure_labels()
    assert run.call_count == len(it.LABEL_DEFINITIONS)
    failed = subprocess.CompletedProcess([], 1, "", "denied")
    with patch.object(gh_transport.subprocess, "run", return_value=failed):
        try:
            it._run("issue", "edit", "1")
        except RuntimeError as error:
            assert str(error) == "denied"
        else:  # pragma: no cover
            raise AssertionError("failed GitHub command was not reported")


def test_summary_handles_empty_and_bumped_rows():
    item = it.rank(issue(4, "urgent", (it.BUMPED,)))
    assert "bumped" in it.summary([item])
    assert it.summary([]).endswith("|---:|---|---|\n")


def test_cli_reports_triage_command_failures(capsys):
    with patch.object(it, "set_bump", side_effect=RuntimeError("denied")):
        assert cli._issue_triage(Namespace(action="bump", issue=7)) == 1
    assert "vibey-gh: denied" in capsys.readouterr().err


def test_cli_dispatches_triage_actions(capsys):
    item = it.rank(issue(7, "feature"))
    with (
        patch.object(it, "triage", return_value=[item]),
        patch.object(it, "set_bump") as set_bump,
        patch.object(it, "ensure_labels") as ensure_labels,
    ):
        assert cli._issue_triage(Namespace(action="sweep", issue=None)) == 0
        assert cli._issue_triage(Namespace(action="bump", issue=7)) == 0
        assert cli._issue_triage(Namespace(action="unbump", issue=7)) == 0
        assert cli._issue_triage(Namespace(action="ensure-labels", issue=None)) == 0
    assert set_bump.call_args_list[0].args == (7, True)
    assert set_bump.call_args_list[1].args == (7, False)
    ensure_labels.assert_called_once()
    assert "Issue triage order" in capsys.readouterr().out
