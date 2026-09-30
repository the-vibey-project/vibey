# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The host a run's shell commands execute on, told to the model (vibey 893c4fc1)."""

import platform

from qwenloop.application.interfaces import HostPlatformInterface
from qwenloop.infrastructure.host_platform import HostPlatform


def _uname(system: str, release: str = "25.6.0", machine: str = "arm64") -> platform.uname_result:
    return platform.uname_result(system, "host", release, "#1", machine)


def test_macos_is_named_with_what_bsd_sed_needs() -> None:
    host = HostPlatform(lambda: _uname("Darwin"))
    assert isinstance(host, HostPlatformInterface)
    described = host.describe()
    assert described.startswith("Darwin 25.6.0 arm64 (macOS, BSD userland: ")
    assert "`sed -i ''`" in described


def test_linux_is_named_gnu_and_an_unknown_system_by_uname_alone() -> None:
    assert HostPlatform(lambda: _uname("Linux", "6.8.0", "x86_64")).describe() == (
        "Linux 6.8.0 x86_64 (GNU userland)"
    )
    assert HostPlatform(lambda: _uname("FreeBSD", "", "amd64")).describe() == "FreeBSD amd64"


def test_the_userland_notes_are_configurable() -> None:
    host = HostPlatform(lambda: _uname("Linux"), userlands={"Linux": "busybox"})
    assert host.describe() == "Linux 25.6.0 arm64 (busybox)"


def test_the_real_host_describes_itself() -> None:
    assert HostPlatform().describe().startswith(platform.system())
