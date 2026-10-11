# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What `vibey worker --auto-accept-design` says on stderr."""

from vibey.application.dto import DesignAutoAcceptReport


def auto_accept_design_lines(report: DesignAutoAcceptReport) -> list[str]:
    """The one line a sweep has to say, if any."""
    return [] if report.message is None else [f"auto-accept-design: {report.message}"]


def auto_accept_design_startup_line(spec_path: str | None) -> str:
    """Said once at startup: what the flag will do, so it is never a surprise."""
    source = f"importing {spec_path} first" if spec_path else "accepting the synthesized spec"
    return (
        f"auto-accept-design: on, {source}, once DESIGN has settled; the visual stage is declined"
    )
