# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from unittest.mock import patch

from vibey_gh import issue_triage as it


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
