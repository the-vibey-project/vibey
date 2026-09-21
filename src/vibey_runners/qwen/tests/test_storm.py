# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from qwenloop.application.storm import build_item_plans, build_plan
from qwenloop.domain.model import RepoItem


def test_build_plan_reports_unavailable_backlog_sections() -> None:
    plan = build_plan(repo="widgets", issues=None, pull_requests=None, author="A Author")
    assert "# qwenstorm plan for widgets" in plan
    assert "### Open issues\n(none, or issues disabled)\n" in plan
    assert "### Open PRs\n(none)\n" in plan
    assert "## Completion" in plan
    assert "Never emit the completion marker after inspection\nalone." in plan


def test_build_plan_renders_empty_backlog_as_blank() -> None:
    plan = build_plan(repo="widgets", issues=[], pull_requests=[], author="A Author")
    assert "### Open issues\n\n### Open PRs\n" in plan
    assert "Work every open issue and PR below locally" in plan
    assert "never push, create a pull request, mutate GitHub" in plan
    assert "plain-text final fence, never a tool" in plan


def test_build_plan_renders_items_with_indented_multiline_bodies() -> None:
    issues = [
        RepoItem(number=7, title="later", body="later body"),
        RepoItem(number=1, title="fix it", body="line one\nline two"),
    ]
    pull_requests = [RepoItem(number=7, title="a pr", body="")]
    plan = build_plan(repo="widgets", issues=issues, pull_requests=pull_requests, author="Author")
    assert "- #1 fix it\n\n  line one\n  line two\n" in plan
    assert plan.index("- #1 fix it") < plan.index("- #7 later")
    assert "- #7 a pr\n\n  \n" in plan


def test_build_item_plans_keeps_fetch_failures_in_one_diagnostic_plan() -> None:
    plans = build_item_plans(repo="widgets", issues=None, pull_requests=[], author="Author")
    assert [label for label, _plan in plans] == ["backlog"]


def test_build_item_plans_splits_sorted_issues_and_pull_requests() -> None:
    plans = build_item_plans(
        repo="widgets",
        issues=[
            RepoItem(number=7, title="later", body=""),
            RepoItem(number=1, title="first", body=""),
        ],
        pull_requests=[RepoItem(number=4, title="pr", body="")],
        author="Author",
    )
    assert [label for label, _plan in plans] == ["issue#1", "issue#7", "pr#4"]
    assert all("## Completion" in plan for _label, plan in plans)


def test_build_item_plans_returns_no_plans_for_empty_successful_fetch() -> None:
    assert build_item_plans(repo="widgets", issues=[], pull_requests=[], author="Author") == []
