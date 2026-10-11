# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What `vibey worker --auto-accept-design` says on stderr."""

from uuid import uuid4

from vibey.application.dto import DesignAutoAcceptReport
from vibey.cli.design_auto_accept import auto_accept_design_lines, auto_accept_design_startup_line


def test_a_sweep_with_nothing_new_says_nothing_and_one_with_news_says_it_once() -> None:
    quiet = DesignAutoAcceptReport(project_id=uuid4())
    news = DesignAutoAcceptReport(project_id=uuid4(), message="waiting for 2 DESIGN job(s)")

    assert auto_accept_design_lines(quiet) == []
    assert auto_accept_design_lines(news) == ["auto-accept-design: waiting for 2 DESIGN job(s)"]


def test_the_startup_line_says_what_the_flag_will_do() -> None:
    plain = auto_accept_design_startup_line(None)
    imported = auto_accept_design_startup_line("/x/spec.json")

    assert "accepting the synthesized spec" in plain
    assert "importing /x/spec.json first" in imported
    for line in (plain, imported):
        assert "once DESIGN has settled" in line and "visual stage is declined" in line
