# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import pytest

from vibey.application.interfaces.local_install import (
    DependencyInstaller,
    LocalStackInstallerInterface,
)
from vibey.application.local_install import LocalStackInstaller
from vibey.domain.local_stack import (
    DependencyReport,
    DependencySpec,
    DependencyState,
)


# Helper fake installer
class FakeInstaller(DependencyInstaller):
    def __init__(self, key, check_report, install_report):
        self.key = key
        self.check_report = check_report
        self.install_report = install_report
        self.calls = []

    def check(self):
        self.calls.append("check")
        return self.check_report

    def install(self):
        self.calls.append("install")
        return self.install_report


# 1. order


def test_install_runs_every_installer_in_declared_order():
    specs = (
        DependencySpec("a", "A", "group", True, None),
        DependencySpec("b", "B", "group", True, None),
    )
    installer_a = FakeInstaller(
        "a",
        DependencyReport("a", DependencyState.READY, "ok"),
        DependencyReport("a", DependencyState.READY, "ok", changed=True),
    )
    installer_b = FakeInstaller(
        "b",
        DependencyReport("b", DependencyState.READY, "ok"),
        DependencyReport("b", DependencyState.READY, "ok", changed=True),
    )
    installers = {"a": installer_a, "b": installer_b}
    orch = LocalStackInstaller(specs, installers, host_label="test")
    report = orch.install()
    assert [r.key for r in report.reports] == ["a", "b"]
    assert installer_a.calls == ["install"]
    assert installer_b.calls == ["install"]


# 2. skip dependent when requirement fails


def test_install_skips_a_dependent_whose_requirement_failed():
    specs = (
        DependencySpec("ollama", "Ollama", "group", True, None),
        DependencySpec("model", "Model", "group", True, None, requires=("ollama",)),
    )
    installer_ollama = FakeInstaller(
        "ollama",
        DependencyReport("ollama", DependencyState.FAILED, "no such package"),
        DependencyReport("ollama", DependencyState.FAILED, "no such package"),
    )
    installer_model = FakeInstaller(
        "model",
        DependencyReport("model", DependencyState.READY, "ok"),
        DependencyReport("model", DependencyState.READY, "ok", changed=True),
    )
    installers = {"ollama": installer_ollama, "model": installer_model}
    orch = LocalStackInstaller(specs, installers, host_label="test")
    report = orch.install()
    assert report.reports[0].state == DependencyState.FAILED
    assert report.reports[1].state == DependencyState.SKIPPED
    assert installer_ollama.calls == ["install"]
    assert installer_model.calls == []


# 3. continues past failures for unrelated deps


def test_install_continues_past_a_failure_to_unrelated_dependencies():
    specs = (
        DependencySpec("a", "A", "group", True, None),
        DependencySpec("b", "B", "group", True, None),
    )
    installer_a = FakeInstaller(
        "a",
        DependencyReport("a", DependencyState.FAILED, "bad"),
        DependencyReport("a", DependencyState.FAILED, "bad"),
    )
    installer_b = FakeInstaller(
        "b",
        DependencyReport("b", DependencyState.READY, "ok"),
        DependencyReport("b", DependencyState.READY, "ok", changed=True),
    )
    installers = {"a": installer_a, "b": installer_b}
    orch = LocalStackInstaller(specs, installers, host_label="test")
    report = orch.install()
    assert report.reports[0].state == DependencyState.FAILED
    assert report.reports[1].state == DependencyState.READY


# 4. requirement outside run does not skip


def test_a_requirement_outside_the_run_does_not_skip():
    specs = (DependencySpec("model", "Model", "group", True, None, requires=("ollama",)),)
    installer_model = FakeInstaller(
        "model",
        DependencyReport("model", DependencyState.READY, "ok"),
        DependencyReport("model", DependencyState.READY, "ok", changed=True),
    )
    installers = {"model": installer_model}
    orch = LocalStackInstaller(specs, installers, host_label="test")
    report = orch.install()
    assert report.reports[0].state == DependencyState.READY


# 5. check never installs


def test_check_never_installs():
    specs = (DependencySpec("a", "A", "group", True, None),)
    installer_a = FakeInstaller(
        "a",
        DependencyReport("a", DependencyState.READY, "ok"),
        DependencyReport("a", DependencyState.READY, "ok", changed=True),
    )
    installers = {"a": installer_a}
    orch = LocalStackInstaller(specs, installers, host_label="test")
    orch.check()
    assert installer_a.calls == ["check"]
    assert installer_a.calls != ["install"]


# 6. missing installer raises ValueError


def test_missing_installer_is_rejected():
    specs = (
        DependencySpec("a", "A", "group", True, None),
        DependencySpec("b", "B", "group", True, None),
    )
    installer_a = FakeInstaller(
        "a",
        DependencyReport("a", DependencyState.READY, "ok"),
        DependencyReport("a", DependencyState.READY, "ok", changed=True),
    )
    installers = {"a": installer_a}
    with pytest.raises(ValueError):
        LocalStackInstaller(specs, installers, host_label="test")


def test_fake_installer_and_orchestrator_satisfy_the_ports():
    spec = DependencySpec("a", "A", "group", True, None)
    report = DependencyReport("a", DependencyState.READY, "ok")
    fake = FakeInstaller("a", report, report)
    orchestrator = LocalStackInstaller((spec,), {"a": fake}, host_label="test")

    assert isinstance(fake, DependencyInstaller)
    assert isinstance(orchestrator, LocalStackInstallerInterface)
