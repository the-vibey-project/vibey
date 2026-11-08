# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Tests for the family memory probe."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from vibey_runners.common.infrastructure.interfaces.memory_probe_interface import (
    MemoryProbeInterface,
)
from vibey_runners.common.infrastructure.memory_probe import MemoryProbe


def test_arch_linux_reads_memtotal_in_kib() -> None:
    requested_path: list[str] = []

    def fake_reader(path: str) -> str | None:
        requested_path.append(path)
        return "MemTotal:       32793692 kB\nMemAvailable:    8000000 kB\n"

    probe = MemoryProbe(platform_name="linux", reader=fake_reader)
    assert probe.total_bytes() == 32793692 * 1024
    assert requested_path == ["/proc/meminfo"]


def test_a_unitless_memtotal_is_bytes() -> None:
    def fake_reader(path: str) -> str | None:
        return "MemTotal: 2048\n"

    probe = MemoryProbe(platform_name="linux", reader=fake_reader)
    assert probe.total_bytes() == 2048


@pytest.mark.parametrize(
    "content",
    [
        None,
        "MemAvailable: 1 kB\n",
        "MemTotal:\n",
        "MemTotal: lots kB\n",
        "MemTotal: 0 kB\n",
    ],
)
def test_linux_that_states_no_usable_total_is_none(content: str | None) -> None:
    probe = MemoryProbe(platform_name="linux", reader=lambda path: content)
    assert probe.total_bytes() is None


def test_macos_asks_sysctl_for_hw_memsize() -> None:
    calls: list[tuple[str, ...]] = []

    def fake_runner(argv: tuple[str, ...]) -> str:
        calls.append(argv)
        return "25769803776\n"

    probe = MemoryProbe(platform_name="darwin", runner=fake_runner)
    assert probe.total_bytes() == 25769803776
    assert calls == [("sysctl", "-n", "hw.memsize")]


@pytest.mark.parametrize("output", ["", "n/a\n", "0\n"])
def test_macos_that_answers_nothing_usable_is_none(output: str) -> None:
    probe = MemoryProbe(platform_name="darwin", runner=lambda argv: output)
    assert probe.total_bytes() is None


def test_another_platform_is_none_without_asking() -> None:
    def fail_runner(argv: tuple[str, ...]) -> str:
        pytest.fail("runner should not be called")

    def fail_reader(path: str) -> str | None:
        pytest.fail("reader should not be called")

    probe = MemoryProbe(platform_name="win32", runner=fail_runner, reader=fail_reader)
    assert probe.total_bytes() is None


def test_the_default_reader_reads_a_real_file(tmp_path: Path) -> None:
    meminfo = tmp_path / "meminfo"
    meminfo.write_text("MemTotal: 1000 kB\n", encoding="utf-8")
    probe = MemoryProbe(platform_name="linux", meminfo_path=str(meminfo))
    assert probe.total_bytes() == 1024000

    missing_probe = MemoryProbe(platform_name="linux", meminfo_path=str(tmp_path / "no-such-file"))
    assert missing_probe.total_bytes() is None


def test_the_default_runner_never_raises(tmp_path: Path) -> None:
    probe = MemoryProbe(platform_name="darwin", command_timeout_seconds=30)
    assert probe._run_command((sys.executable, "-c", "print(42)")) == "42\n"
    assert probe._run_command((sys.executable, "-c", "raise SystemExit(3)")) == ""
    assert probe._run_command((str(tmp_path / "no-such-binary"),)) == ""

    timeout_probe = MemoryProbe(platform_name="darwin", command_timeout_seconds=0.5)
    assert timeout_probe._run_command((sys.executable, "-c", "import time; time.sleep(5)")) == ""


def test_the_default_platform_is_this_interpreters() -> None:
    probe = MemoryProbe(runner=lambda argv: "", reader=lambda path: None)
    assert probe.total_bytes() is None


def test_the_probe_satisfies_its_interface() -> None:
    assert isinstance(MemoryProbe(), MemoryProbeInterface)
