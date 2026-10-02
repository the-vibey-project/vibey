# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`scripts/host_health.py`: every probe's parser on macOS and Linux fixture output, the
record's append-only discipline, the forecast's driver states, the rendered page and its
drift check, the tracking issue's conditions, the host's weekly unit and the publisher.

The probes are driven through a fake command runner and a fake file tree (a tmp root), so
each decision about a missing tool, a missing privilege or missing hardware -- skip it, say
why, never invent a value -- is exercised without the host.

Module-level test functions rather than a class with an interface beside it (ADR-0016):
pytest collects `test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

import json
import plistlib
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from scripts import host_health as hh
from scripts import minimum_specs as ms
from scripts.interfaces import host_health_interface as contracts
from vibey.domain.host_health import DEFAULT_LOCAL_RECORD

REPO = Path(__file__).resolve().parents[2]
SETTINGS = hh.HealthSettings.load(REPO / hh.DEFAULT_CONFIG)
NOW = "2026-10-05T06:41:00.000Z"
NOW_EPOCH = 1_791_182_460.0  # 2026-10-05T06:41:00Z


class FixedClock:
    def __init__(self, stamp: str = NOW) -> None:
        self.stamp = stamp

    def now(self) -> str:
        return self.stamp


class FakeRunner:
    """Answers commands by their first matching prefix; records every call."""

    def __init__(self, answers: Mapping[tuple[str, ...], ms.CommandResult] | None = None) -> None:
        self.answers = dict(answers or {})
        self.calls: list[list[str]] = []

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float,
        env: Mapping[str, str] | None = None,
        cwd: str | None = None,
    ) -> ms.CommandResult:
        self.calls.append(list(argv))
        for prefix, result in self.answers.items():
            if tuple(argv[: len(prefix)]) == prefix:
                return result
        return ms.CommandResult(127, "", f"no answer for {argv[:3]}", 0.0)


def ok(stdout: str, code: int = 0) -> ms.CommandResult:
    return ms.CommandResult(code, stdout, "", 0.0)


def ctx(
    system: str,
    answers: Mapping[tuple[str, ...], ms.CommandResult] | None = None,
    root: Path = Path("/nonexistent"),
    home: Path = Path("/nonexistent-home"),
) -> hh.ProbeContext:
    return hh.ProbeContext(
        SETTINGS,
        FakeRunner(answers),
        ms.FigureFactory(FixedClock(), "sha256:test"),
        system,
        root=root,
        home=home,
        wall=lambda: NOW_EPOCH,
        which=lambda name: None,
    )


def by_id(figures: Sequence[ms.Figure]) -> dict[str, ms.Figure]:
    return {f.id: f for f in figures}


class FakeDescriber:
    """The host's description, fixed: the real HostDescriber reads sysctl or /proc."""

    def __init__(self, ram_bytes: int = 24 * 2**30) -> None:
        self.info = {
            "system": "Darwin",
            "arch": "arm64",
            "model": "Mac17,2",
            "chip": "Apple M5",
            "ram_bytes": ram_bytes,
            "cores_total": 10,
            "os": "macOS 26.6.2",
        }

    def describe(self) -> dict[str, Any]:
        return dict(self.info)


def make_cli(
    repo: Path,
    clock: Any,
    runner: Any,
    home: Path,
    which: Any = None,
    describer: Any = None,
) -> hh.HostHealthCli:
    """A command whose every input that could reach the host is a fake: the runner, the
    platform, the file-system root and home, the describer and the PATH lookup."""
    return hh.HostHealthCli(
        repo,
        clock,
        runner,
        home=home,
        which=which or (lambda name: None),
        system="Darwin",
        root=home / "no-host-root",
        describer=describer or FakeDescriber(),
    )


@pytest.fixture(autouse=True)
def _the_host_is_out_of_reach(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test here runs on fixtures. A test that reached the real host -- a command,
    the host's description, its platform, PATH, its home, or a probe reading under `/` --
    would pass or fail with the machine it ran on, as one did on CI's Linux runner. Each of
    those is made to fail loudly instead."""

    def reached(what: str) -> Any:
        def refuse(*args: Any, **kwargs: Any) -> Any:
            raise AssertionError(f"a test reached the real host: {what}")

        return refuse

    monkeypatch.setattr(ms.SubprocessRunner, "run", reached("a subprocess"))
    monkeypatch.setattr(ms.HostDescriber, "describe", reached("HostDescriber.describe"))
    monkeypatch.setattr(hh.platform, "system", reached("platform.system()"))
    monkeypatch.setattr(hh.shutil, "which", reached("shutil.which"))
    original = hh.ProbeContext.path

    def path(self: hh.ProbeContext, text: str) -> Path:
        if text.startswith("/") and self.root == Path("/"):
            raise AssertionError(f"a test reached the real host: a probe read {text}")
        if text.startswith("~") and self.home == Path.home():
            raise AssertionError(f"a test reached the real host: a probe read {text}")
        return original(self, text)

    monkeypatch.setattr(hh.ProbeContext, "path", path)


# ------------------------------------------------------------------------ fixtures

SMARTCTL_NVME = {
    "smart_status": {"passed": True},
    "nvme_smart_health_information_log": {
        "percentage_used": 3,
        "available_spare": 100,
        "available_spare_threshold": 99,
        "data_units_written": 40_000_000,
        "media_errors": 0,
    },
    "power_on_time": {"hours": 1234},
}
DF = """Filesystem 1024-blocks Used Available Capacity Mounted on
/dev/disk3s5 971298980 448679520 483892292 49% /System/Volumes/Data
"""
DISKUTIL = "   Device Identifier:  disk0\n   SMART Status:              Verified\n"
IOREG_BATTERY = """+-o AppleSmartBattery  <class AppleSmartBattery>
    {
      "CurrentCapacity" = 80
      "ExternalConnected" = Yes
      "BatteryData" = {"Serial"="F5DHQL004HC0000VD4","CycleCount"=18}
      "Serial" = "F5DHQL004HC0000VD4"
      "NominalChargeCapacity" = 6502
      "DesignCycleCount9C" = 1000
      "DesignCapacity" = 6249
      "PermanentFailureStatus" = 0
      "CycleCount" = 18
      "AppleRawMaxCapacity" = 6350
    }
"""
POWER = "      Health Information:\n          Cycle Count: 18\n          Condition: Normal\n"
PMSET_NOTES = (
    "Note: No thermal warning level has been recorded\n"
    "Note: No performance warning level has been recorded\n"
    "Note: No CPU power status has been recorded\n"
)
PMSET_LIMITED = "CPU Power notify\n\tCPU_Scheduler_Limit \t= 100\n\tCPU_Speed_Limit \t= 70\n"
VM_STAT = """Mach Virtual Memory Statistics: (page size of 16384 bytes)
Pages free:                                     4097.
"Translation faults":                     4213934850.
Compressions:                             1329384629.
Swapouts:                                   79714052.
"""
MEMINFO = """MemTotal:       16303540 kB
MemFree:         1000000 kB
MemAvailable:    8151770 kB
SwapTotal:       4194300 kB
SwapFree:        3145725 kB
"""
PSI = "some avg10=0.00 avg60=0.10 avg300=1.25 total=123\nfull avg10=0.00 avg60=0.00 avg300=0.40 total=45\n"
OLLAMA_LOG = """time=2026-09-29T10:00:00.000-04:00 level=INFO msg="template selection" model=registry.ollama.ai/library/gpt-oss:20b
slot print_timing: id  0 | task 1 | prompt eval time =     900.00 ms /  4000 tokens (    0.22 ms per token,  4444.44 tokens per second)
slot print_timing: id  0 | task 1 |        eval time =    4000.00 ms /   100 tokens (   40.00 ms per token,    25.00 tokens per second)
slot print_timing: id  0 | task 2 | prompt eval time =     100.00 ms /    71 tokens (    1.40 ms per token,   710.00 tokens per second)
slot print_timing: id  0 | task 2 |        eval time =    4000.00 ms /   100 tokens (   40.00 ms per token,    30.00 tokens per second)
slot print_timing: id  0 | task 3 | prompt eval time =     900.00 ms /  4000 tokens (    0.22 ms per token,  4444.44 tokens per second)
slot print_timing: id  0 | task 3 |        eval time =       0.00 ms /     1 tokens (    0.00 ms per token,     0.00 tokens per second)
time=2026-09-29T11:00:00.000-04:00 level=INFO msg="template selection" model=registry.ollama.ai/library/qwen3:14b
slot print_timing: id  0 | task 4 | prompt eval time =     900.00 ms /  4000 tokens (    0.22 ms per token,  4444.44 tokens per second)
slot print_timing: id  0 | task 4 |        eval time =    4000.00 ms /   100 tokens (   40.00 ms per token,    12.00 tokens per second)
"""


# ------------------------------------------------------------------------ settings


def test_the_hosts_own_record_is_where_vibey_doctor_looks() -> None:
    assert SETTINGS["local_record"] == DEFAULT_LOCAL_RECORD


def test_every_driver_names_a_kind_a_figure_and_where_its_threshold_comes_from() -> None:
    for key, spec in SETTINGS.drivers.items():
        assert spec["kind"] in ("trend", "level", "dated"), key
        assert spec["figure"], key
        if spec["kind"] != "dated":
            assert spec["direction"] in ("rising", "falling"), key
            sources = {
                "threshold",
                "threshold_figure",
                "threshold_config",
                "threshold_figure_local",
            }
            assert sources & set(spec), key
            assert spec["threshold_source"], key


def test_every_class_declares_its_interface() -> None:
    for cls, contract in (
        (hh.HostIdentity, contracts.HostIdentityInterface),
        (hh.HealthLedger, contracts.HealthLedgerInterface),
        (hh.Forecaster, contracts.ForecasterInterface),
        (hh.HealthRenderer, contracts.HealthRendererInterface),
        (hh.ConditionEvaluator, contracts.ConditionEvaluatorInterface),
        (hh.SchedulerRenderer, contracts.SchedulerRendererInterface),
        (hh.Publisher, contracts.PublisherInterface),
    ):
        assert contract in cls.__mro__, cls


# ------------------------------------------------------------------------ the host


def test_the_fingerprint_is_stable_and_never_carries_the_identifier() -> None:
    info = {"system": "Darwin", "model": "Mac17,2", "chip": "Apple M5", "ram_bytes": 1}
    first = hh.HostIdentity.fingerprint(info, "UUID-1", 16)
    assert first == hh.HostIdentity.fingerprint(info, "UUID-1", 16)
    assert first != hh.HostIdentity.fingerprint(info, "UUID-2", 16)
    assert first.startswith("sha256:") and len(first) == len("sha256:") + 16
    assert "UUID" not in first


def test_describe_drops_what_must_never_be_recorded() -> None:
    class Describer:
        def describe(self) -> dict[str, Any]:
            return {"system": "Darwin", "model": "Mac17,2", "Serial": "X", "HostName": "adams-mac"}

    c = ctx("Darwin", {("ioreg", "-rd1"): ok('  "IOPlatformUUID" = "ABC-123"\n')})
    info = hh.HostIdentity(c, Describer()).describe()  # type: ignore[arg-type]
    assert "Serial" not in info and "HostName" not in info
    assert "ABC-123" not in json.dumps(info)
    assert info["fingerprint"].startswith("sha256:")


def test_linux_identity_reads_machine_id(tmp_path: Path) -> None:
    (tmp_path / "etc").mkdir()
    (tmp_path / "etc" / "machine-id").write_text("abc\n")
    assert hh.HostIdentity(ctx("Linux", root=tmp_path)).platform_id() == "abc"


# ------------------------------------------------------------------------ storage


def test_smartctl_json_yields_wear_spare_writes_errors_and_hours() -> None:
    parsed = hh.StorageProbe.parse_smartctl(SMARTCTL_NVME)
    assert parsed == {
        "smart_passed": True,
        "percentage_used": 3,
        "available_spare": 100,
        "available_spare_threshold": 99,
        "tb_written": 20.48,
        "bytes_written": 20_480_000_000_000,
        "write_gb_per_power_on_hour": 16.6,
        "media_errors": 0,
        "power_on_hours": 1234,
    }
    assert hh.StorageProbe.parse_smartctl({}) == {}


def test_df_and_diskutil_parse() -> None:
    assert hh.StorageProbe.parse_df(DF) == (971298980 * 1024, 483892292 * 1024)
    assert hh.StorageProbe.parse_df("") is None
    assert hh.StorageProbe.parse_df("header\nshort line\n") is None
    assert hh.StorageProbe.parse_diskutil(DISKUTIL) == "Verified"
    assert hh.StorageProbe.parse_diskutil("") is None


def test_macos_without_smartctl_skips_wear_with_the_install_hint_and_keeps_diskutils_verdict() -> (
    None
):
    c = ctx("Darwin", {("diskutil", "info"): ok(DISKUTIL), ("df",): ok(DF)})
    figures = by_id(hh.StorageProbe(c).run())
    wear = figures["storage.percentage_used"]
    assert wear.status == "skipped" and "brew install smartmontools" in str(wear.reason)
    assert figures["storage.smart_status"].value == "Verified"
    assert figures["storage.free_gb"].value == pytest.approx(495.5, abs=0.1)


def test_macos_with_smartctl_measures_every_field() -> None:
    c = ctx("Darwin", {("smartctl",): ok(json.dumps(SMARTCTL_NVME)), ("df",): ok(DF)})
    figures = by_id(hh.StorageProbe(c).run())
    assert figures["storage.percentage_used"].value == 3
    assert figures["storage.spare_margin_pct"].value == 1
    assert figures["storage.smart_status"].value == "passed"


def test_linux_smartctl_without_root_is_skipped_with_the_reason() -> None:
    denied = ms.CommandResult(2, '{"smartctl": {"exit_status": 2}}', "Permission denied", 0.0)
    c = ctx(
        "Linux",
        {
            ("smartctl", "--scan"): ok("/dev/nvme0 -d nvme # /dev/nvme0, NVMe device\n"),
            ("smartctl", "--json=c"): denied,
            ("df",): ok(""),
        },
    )
    figures = by_id(hh.StorageProbe(c).run())
    assert "without privileges" in str(figures["storage.percentage_used"].reason)
    assert figures["storage.smart_status"].status == "skipped"
    assert figures["storage.free_gb"].status == "skipped"


def test_linux_with_no_device_or_no_smartctl_says_which() -> None:
    nothing = by_id(hh.StorageProbe(ctx("Linux", {("smartctl", "--scan"): ok("")})).run())
    assert "listed no device" in str(nothing["storage.percentage_used"].reason)
    missing = by_id(hh.StorageProbe(ctx("Linux")).run())
    assert "smartctl not found" in str(missing["storage.percentage_used"].reason)


def test_a_sata_drive_without_an_nvme_log_says_so() -> None:
    sata = {"smart_status": {"passed": False}}
    c = ctx("Darwin", {("smartctl",): ok(json.dumps(sata)), ("df",): ok(DF)})
    figures = by_id(hh.StorageProbe(c).run())
    assert figures["storage.smart_status"].value == "FAILED"
    assert "not an NVMe log" in str(figures["storage.percentage_used"].reason)


# ------------------------------------------------------------------------ battery


def test_ioreg_battery_parses_top_level_numbers_and_never_the_serial() -> None:
    values = hh.BatteryProbe.parse_ioreg(IOREG_BATTERY)
    assert values["CycleCount"] == 18 and values["DesignCycleCount9C"] == 1000
    assert values["ExternalConnected"] is True
    assert "Serial" not in values
    assert hh.BatteryProbe.capacity_ratio(values) == (round(6350 / 6249, 4), "AppleRawMaxCapacity")
    assert hh.BatteryProbe.capacity_ratio({"DesignCapacity": 100, "NominalChargeCapacity": 90}) == (
        0.9,
        "NominalChargeCapacity",
    )
    assert hh.BatteryProbe.capacity_ratio({"DesignCapacity": 100}) is None
    assert hh.BatteryProbe.capacity_ratio({}) is None


def test_macos_battery_figures_and_no_battery() -> None:
    c = ctx("Darwin", {("ioreg",): ok(IOREG_BATTERY), ("system_profiler",): ok(POWER)})
    figures = by_id(hh.BatteryProbe(c).run())
    assert figures["battery.capacity_ratio"].value == round(6350 / 6249, 4)
    assert figures["battery.cycle_count"].value == 18
    assert figures["battery.design_cycle_count"].value == 1000
    assert figures["battery.condition"].value == "Normal"
    assert "F5DHQL" not in json.dumps([f.to_dict() for f in figures.values()])
    desktop = by_id(hh.BatteryProbe(ctx("Darwin", {("ioreg",): ok("")})).run())
    assert all(f.status == "skipped" and "no battery" in str(f.reason) for f in desktop.values())


def test_macos_battery_with_a_sparse_gauge() -> None:
    c = ctx("Darwin", {("ioreg",): ok('    "DesignCapacity" = 6000\n')})
    figures = by_id(hh.BatteryProbe(c).run())
    assert figures["battery.capacity_ratio"].status == "skipped"
    assert figures["battery.cycle_count"].status == "skipped"
    assert figures["battery.condition"].status == "skipped"


def battery_tree(root: Path, **files: str) -> None:
    supply = root / "sys/class/power_supply"
    (supply / "AC").mkdir(parents=True)
    (supply / "AC" / "type").write_text("Mains\n")
    (supply / "BAT0").mkdir()
    for name, value in {"type": "Battery", **files}.items():
        (supply / "BAT0" / name).write_text(value + "\n")


def test_linux_battery_from_sysfs(tmp_path: Path) -> None:
    battery_tree(
        tmp_path,
        energy_full="45000000",
        energy_full_design="50000000",
        cycle_count="210",
        health="Good",
    )
    figures = by_id(hh.BatteryProbe(ctx("Linux", root=tmp_path)).run())
    assert figures["battery.capacity_ratio"].value == 0.9
    assert figures["battery.cycle_count"].value == 210
    assert figures["battery.design_cycle_count"].status == "skipped"
    assert figures["battery.condition"].value == "Good"


def test_linux_battery_that_reports_little(tmp_path: Path) -> None:
    battery_tree(tmp_path, cycle_count="0")
    figures = by_id(hh.BatteryProbe(ctx("Linux", root=tmp_path)).run())
    assert figures["battery.capacity_ratio"].status == "skipped"
    assert figures["battery.cycle_count"].status == "skipped"
    assert figures["battery.condition"].status == "skipped"
    none = by_id(hh.BatteryProbe(ctx("Linux", root=tmp_path / "empty")).run())
    assert "no battery" in str(none["battery.cycle_count"].reason)


# ------------------------------------------------------------------------ thermal


def test_pmset_notes_mean_no_limit_and_a_recorded_limit_is_read() -> None:
    assert hh.ThermalProbe.parse_pmset(PMSET_NOTES) == {
        "cpu_speed_limit_pct": 100,
        "warning_level": 0,
    }
    assert hh.ThermalProbe.parse_pmset(PMSET_LIMITED + "Thermal_Warning_Level = 2\n") == {
        "cpu_speed_limit_pct": 70,
        "warning_level": 2,
    }
    figures = by_id(hh.ThermalProbe(ctx("Darwin", {("pmset",): ok(PMSET_NOTES)})).run())
    assert figures["thermal.cpu_speed_limit_pct"].value == 100
    blank = by_id(hh.ThermalProbe(ctx("Darwin", {("pmset",): ok("")})).run())
    assert blank["thermal.warning_level"].status == "skipped"


def test_linux_thermal_from_sysfs(tmp_path: Path) -> None:
    zone = tmp_path / "sys/class/thermal/thermal_zone0"
    zone.mkdir(parents=True)
    (zone / "temp").write_text("71500\n")
    for n, cap in ((0, "3000000"), (1, "2400000")):
        cpu = tmp_path / f"sys/devices/system/cpu/cpu{n}"
        (cpu / "cpufreq").mkdir(parents=True)
        (cpu / "cpufreq" / "scaling_max_freq").write_text(cap)
        (cpu / "cpufreq" / "cpuinfo_max_freq").write_text("3000000")
        (cpu / "thermal_throttle").mkdir()
        (cpu / "thermal_throttle" / "core_throttle_count").write_text("4")
    figures = by_id(hh.ThermalProbe(ctx("Linux", root=tmp_path)).run())
    assert figures["thermal.max_zone_c"].value == 71.5
    assert figures["thermal.cpu_speed_limit_pct"].value == 80
    assert figures["thermal.throttle_events"].value == 8
    vm = by_id(hh.ThermalProbe(ctx("Linux", root=tmp_path / "vm")).run())
    assert all(f.status == "skipped" for f in vm.values())


# ------------------------------------------------------------------------ memory


def test_memory_parsers() -> None:
    assert hh.MemoryProbe.parse_swapusage(
        "vm.swapusage: total = 15360.00M  used = 14162.94M  free = 1197.06M  (encrypted)"
    ) == (15360.0, 14162.94)
    assert hh.MemoryProbe.parse_swapusage("total = 2.00G  used = 1.00G") == (2048.0, 1024.0)
    assert hh.MemoryProbe.parse_swapusage("") is None
    stats = hh.MemoryProbe.parse_vm_stat(VM_STAT)
    assert stats["compressions"] == 1329384629 and stats["translation faults"] == 4213934850
    assert hh.MemoryProbe.parse_meminfo(MEMINFO)["MemTotal"] == 16303540 * 1024
    assert hh.MemoryProbe.parse_psi(PSI) == {"some": 1.25, "full": 0.4}
    assert hh.MemoryProbe.parse_boottime("{ sec = 1790812405, usec = 881851 }") == 1790812405.0
    assert hh.MemoryProbe.parse_boottime("") is None


def test_macos_memory_figures() -> None:
    c = ctx(
        "Darwin",
        {
            ("sysctl", "-n", "hw.memsize"): ok("25769803776\n"),
            ("sysctl", "vm.swapusage"): ok("total = 15360.00M  used = 14162.94M  free = 1M"),
            ("memory_pressure",): ok("System-wide memory free percentage: 18%\n"),
            ("sysctl", "-n", "kern.boottime"): ok(
                f"{{ sec = {int(NOW_EPOCH) - 36000}, usec = 0 }}"
            ),
            ("vm_stat",): ok(VM_STAT),
        },
    )
    figures = by_id(hh.MemoryProbe(c).run())
    assert figures["memory.ram_gib"].value == 24.0
    assert figures["memory.ram_gb_as_sold"].value == 24.0
    assert figures["memory.swap_used_ratio"].value == pytest.approx(14162.94 / 24576, abs=1e-3)
    assert figures["memory.free_pct"].value == 18
    assert figures["memory.compressions_per_hour"].value == round(1329384629 / 10)
    assert figures["memory.swapout_gb_per_hour"].value == round(79714052 * 16384 / 1e9 / 10, 1)


def test_macos_memory_when_nothing_answers() -> None:
    figures = by_id(hh.MemoryProbe(ctx("Darwin")).run())
    assert {f.status for f in figures.values()} == {"skipped"}


def test_linux_memory_from_proc(tmp_path: Path) -> None:
    (tmp_path / "proc/pressure").mkdir(parents=True)
    (tmp_path / "proc/meminfo").write_text(MEMINFO)
    (tmp_path / "proc/pressure/memory").write_text(PSI)
    (tmp_path / "proc/vmstat").write_text("pswpout 10\noom_kill 2\n")
    figures = by_id(hh.MemoryProbe(ctx("Linux", root=tmp_path)).run())
    assert figures["memory.free_pct"].value == 50
    assert figures["memory.swap_used_gib"].value == pytest.approx(1.0, abs=0.01)
    assert figures["memory.psi_some_avg300"].value == 1.25
    assert figures["memory.oom_kills"].value == 2
    bare = by_id(hh.MemoryProbe(ctx("Linux", root=tmp_path / "none")).run())
    assert {f.status for f in bare.values()} == {"skipped"}


# ------------------------------------------------------------------------ reliability


def test_reports_are_classified_by_name_and_date_and_the_host_name_is_dropped() -> None:
    kinds = SETTINGS["reliability"]["kinds"]
    names = [
        "panic-full-2026-09-25-115831.0002.panic",
        "ResetCounter-2026-09-25-115833.diag",
        "shutdown_stall_2026-09-30-163108_Adams-MacBook-Pro.shutdownStall",
        "shutdown_stall_2026-09-30-163108_Adams-MacBook-Pro.shutdownStall",
        "JetsamEvent-2026-09-25-165954.ips",
        "git_2026-09-25-153119_Adams-MacBook-Pro.diag",
        ".contents.panic",
    ]
    events = hh.ReliabilityProbe.classify(names, kinds)
    assert events == [
        {"kind": "kernel_panic", "at": "2026-09-25T11:58:31"},
        {"kind": "reset", "at": "2026-09-25T11:58:33"},
        {"kind": "jetsam", "at": "2026-09-25T16:59:54"},
        {"kind": "shutdown_stall", "at": "2026-09-30T16:31:08"},
    ]
    assert "Adams" not in json.dumps(events)
    assert hh.ReliabilityProbe.window(events, "kernel_panic", "2026-09-26T00:00:00") == 0


def test_macos_reliability_probe(tmp_path: Path) -> None:
    reports = tmp_path / "Library/Logs/DiagnosticReports"
    reports.mkdir(parents=True)
    (reports / "panic-full-2026-10-01-115831.0002.panic").write_text("never read")
    c = ctx(
        "Darwin",
        {("sysctl",): ok(f"{{ sec = {int(NOW_EPOCH) - 86400}, usec = 0 }}")},
        root=tmp_path,
    )
    figures = by_id(hh.ReliabilityProbe(c).run())
    assert figures["reliability.kernel_panics_window"].value == 1
    assert figures["reliability.uptime_days"].value == 1.0
    unreadable = by_id(hh.ReliabilityProbe(ctx("Darwin")).run())
    assert unreadable["reliability.kernel_panics_window"].status == "skipped"
    assert unreadable["reliability.uptime_days"].status == "skipped"


def test_linux_reliability_reads_pstore_and_uptime(tmp_path: Path) -> None:
    (tmp_path / "sys/fs/pstore").mkdir(parents=True)
    (tmp_path / "sys/fs/pstore/dmesg-efi-1").write_text("x")
    (tmp_path / "proc").mkdir()
    (tmp_path / "proc/uptime").write_text("172800.00 1.00\n")
    c = hh.ProbeContext(
        SETTINGS,
        FakeRunner(),
        ms.FigureFactory(FixedClock(), "h"),
        "Linux",
        root=tmp_path,
        home=tmp_path,
        wall=lambda: (tmp_path / "sys/fs/pstore/dmesg-efi-1").stat().st_mtime + 60,
    )
    figures = by_id(hh.ReliabilityProbe(c).run())
    assert figures["reliability.kernel_panics_window"].value == 1
    assert figures["reliability.uptime_days"].value == 2.0
    assert figures["reliability.jetsam_window"].status == "skipped"


# ------------------------------------------------------------------------ throughput


def test_the_log_yields_samples_with_their_model_time_and_prompt_size() -> None:
    samples = hh.OllamaThroughputLog.samples(OLLAMA_LOG.splitlines())
    assert [(s.model, s.prompt_tokens, s.generated_tokens, s.tok_s) for s in samples] == [
        ("gpt-oss:20b", 4000, 100, 25.0),
        ("gpt-oss:20b", 71, 100, 30.0),
        ("gpt-oss:20b", 4000, 1, 0.0),
        ("qwen3:14b", 4000, 100, 12.0),
    ]
    assert samples[0].at == "2026-09-29T14:00:00.000Z"
    gin = hh.OllamaThroughputLog.samples(
        [
            '[GIN] 2026/09/29 - 10:00:00 | 200 | 1s | 127.0.0.1 | POST "/api/chat"',
            "slot print_timing: id 0 | task 1 |        eval time = 1.0 ms / 50 tokens (1 ms per token, 20.00 tokens per second)",
        ]
    )
    assert gin[0].tok_s == 20.0


def test_weekly_medians_keep_one_model_one_band_and_enough_samples() -> None:
    sample = hh.ThroughputSample
    samples = [
        sample("2026-09-29T10:00:00.000Z", "gpt-oss:20b", 4000, 100, r) for r in (24, 25, 26)
    ]
    samples += [sample("2026-09-22T10:00:00.000Z", "gpt-oss:20b", 4000, 100, 27)]
    samples += [sample("2026-09-29T10:00:00.000Z", "gpt-oss:20b", 71, 100, 40)]
    samples += [sample("2026-09-29T10:00:00.000Z", "qwen3:14b", 4000, 100, 12)]
    samples += [sample("2026-09-29T10:00:00.000Z", "gpt-oss:20b", 4000, 1, 0)]
    weekly = hh.OllamaThroughputLog.weekly(samples, "gpt-oss:20b", (1024, 32768), 32, 3)
    assert weekly == [{"week": "2026-09-28", "median_tok_s": 25.0, "n": 3}]


def test_throughput_probe_mines_the_log_or_says_there_is_none(tmp_path: Path) -> None:
    logs = tmp_path / ".ollama/logs"
    logs.mkdir(parents=True)
    (logs / "server.log").write_text(OLLAMA_LOG * 5)
    c = ctx("Darwin", home=tmp_path)
    figures = by_id(hh.ThroughputProbe(c, "gpt-oss:20b").run())
    assert figures["throughput.weekly"].value == [
        {"week": "2026-09-28", "median_tok_s": 25.0, "n": 5}
    ]
    assert figures["throughput.gen_tok_s_week_median"].value == 25.0
    too_few = by_id(hh.ThroughputProbe(c, "llama3:8b").run())
    assert too_few["throughput.gen_tok_s_week_median"].status == "skipped"
    none = by_id(hh.ThroughputProbe(ctx("Darwin", home=tmp_path / "x"), "m").run())
    assert none["throughput.weekly"].status == "skipped"


# ------------------------------------------------------------------------ the rest of the probes


def test_the_microbenchmark_runs_only_on_a_quiet_host() -> None:
    class Gate:
        def __init__(self, idle: bool) -> None:
            self.idle = idle

        def wait(self) -> tuple[bool, str, dict[str, Any]]:
            return self.idle, "" if self.idle else "load1 9.00 above 4.0", {"load1": 1.0}

    busy = by_id(hh.MicroBenchmark(ctx("Darwin"), Gate(False)).run())
    assert {f.status for f in busy.values()} == {"skipped"}
    quiet = by_id(
        hh.MicroBenchmark(ctx("Darwin"), Gate(True), lambda m, r: 1.5, lambda m, r: 2.5).run()
    )
    assert quiet["micro.cpu_sha256_mib_s"].value == 1.5
    assert quiet["micro.disk_fsync_write_mib_s"].value == 2.5
    assert hh.MicroBenchmark.sha256_mib_s(1, 1) > 0
    assert hh.MicroBenchmark.fsync_write_mib_s(1, 1) > 0


def test_os_keys_and_support_dates(tmp_path: Path) -> None:
    assert hh.PlatformProbe.os_key("Darwin", "") == ("macos", "macOS")
    ubuntu = 'ID=ubuntu\nVERSION_ID="24.04"\nPRETTY_NAME="Ubuntu 24.04.1 LTS"\n'
    assert hh.PlatformProbe.os_key("Linux", ubuntu) == ("ubuntu-24.04", "Ubuntu 24.04.1 LTS")
    assert hh.PlatformProbe.os_key("Linux", "ID=arch\n")[0] == "arch"
    (tmp_path / "etc").mkdir()
    (tmp_path / "etc/os-release").write_text(ubuntu)
    figures = by_id(hh.PlatformProbe(ctx("Linux", root=tmp_path), {}).run())
    end = figures["platform.os_support_end"]
    assert end.status == "declared" and end.value == "2029-05-01"
    assert end.source == "https://ubuntu.com/about/release-cycle"
    assert "no hardware support entry" in str(figures["platform.hardware_obsolete_on"].reason)
    mac = by_id(hh.PlatformProbe(ctx("Darwin"), {"model": "Mac17,2", "os": "macOS 26"}).run())
    assert mac["platform.os_support_end"].status == "skipped"
    assert "publishes no end-of-support date" in str(mac["platform.os_support_end"].reason)
    assert "set last_sold" in str(mac["platform.hardware_obsolete_on"].reason)
    (tmp_path / "etc/os-release").write_text("ID=gentoo\n")
    other = by_id(hh.PlatformProbe(ctx("Linux", root=tmp_path), {}).run())
    assert "no support entry" in str(other["platform.os_support_end"].reason)


def test_a_declared_last_sale_dates_the_hardware(monkeypatch: pytest.MonkeyPatch) -> None:
    table = json.loads(json.dumps(SETTINGS.table))
    table["platform"]["hardware"]["Mac17,2"]["last_sold"] = "2028-02-29"
    c = replace(ctx("Darwin"), settings=hh.HealthSettings(table))
    figures = by_id(hh.PlatformProbe(c, {"model": "Mac17,2"}).run())
    assert figures["platform.hardware_obsolete_on"].value == "2035-02-28"


def specs_record() -> ms.SpecsRecord:
    def figure(fid: str, value: float) -> ms.Figure:
        return ms.Figure(
            id=fid,
            label=fid,
            value=value,
            unit="GB",
            status="derived",
            method="m",
            measured_at="2026-10-01T00:00:00Z",
            formula="f",
            inputs={},
        )

    return ms.SpecsRecord(
        generated_at="2026-10-01T00:00:00Z",
        hosts={},
        figures=(
            figure("ram.minimum_gb", 24.0),
            figure("ram.recommended_gb", 32.0),
            figure("disk.minimum_gb", 20),
        ),
    )


def test_capacity_copies_vibeys_requirements_with_their_dates() -> None:
    figures = by_id(hh.CapacityProbe(ctx("Darwin"), specs_record(), "specs.json").run())
    assert figures["capacity.ram_minimum_gb"].value == 24.0
    assert figures["capacity.ram_minimum_gb"].measured_at == "2026-10-01T00:00:00Z"
    assert figures["capacity.disk_recommended_gb"].status == "skipped"
    unreadable = by_id(hh.CapacityProbe(ctx("Darwin"), None, "specs.json").run())
    assert "unreadable" in str(unreadable["capacity.ram_minimum_gb"].reason)


# ------------------------------------------------------------------------ the record


def make_record(
    at: str, values: Mapping[str, Any], fingerprint: str = "sha256:h"
) -> hh.HealthRecord:
    figures = []
    for fid, value in values.items():
        if value is None:
            figures.append(
                ms.Figure(
                    id=fid,
                    label=fid,
                    value=None,
                    unit="x",
                    status="skipped",
                    method="m",
                    measured_at=at,
                    reason="not measured here",
                )
            )
        else:
            figures.append(
                ms.Figure(
                    id=fid,
                    label=fid,
                    value=value,
                    unit="x",
                    status="measured",
                    method="m",
                    measured_at=at,
                )
            )
    host = {
        "fingerprint": fingerprint,
        "system": "Darwin",
        "model": "Mac17,2",
        "ram_bytes": 24 * 2**30,
    }
    return hh.HealthRecord(f"{fingerprint}@{at}", at, host, tuple(figures))


def test_a_record_round_trips_through_one_line() -> None:
    record = make_record(NOW, {"battery.cycle_count": 18})
    line = record.to_line()
    assert "\n" not in line
    assert hh.HealthRecord.from_line(line) == record
    with pytest.raises(ValueError, match="schema"):
        hh.HealthRecord.from_line(json.dumps({"schema": "x"}))
    with pytest.raises(ValueError, match="fingerprint"):
        hh.HealthRecord.from_line(json.dumps({"schema": hh.SCHEMA, "host": {}}))


def test_the_ledger_only_appends(tmp_path: Path) -> None:
    ledger = hh.HealthLedger(tmp_path / "nested" / "r.jsonl")
    first = make_record("2026-09-28T06:41:00.000Z", {"a": 1})
    second = make_record(NOW, {"a": 2})
    assert ledger.read() == []
    assert ledger.append(first) is True
    assert ledger.append(first) is False
    before = ledger.text()
    assert ledger.merge([second, first]) == 1
    assert ledger.text().startswith(before)
    assert [r.run_id for r in ledger.read()] == [first.run_id, second.run_id]
    assert hh.HealthLedger.append_only(before, ledger.text()) is None
    assert hh.HealthLedger.append_only(ledger.text(), before) == "line 2 was removed"
    assert "rewritten" in str(hh.HealthLedger.append_only(before, "x\n" + ledger.text()))


def test_a_ledger_missing_its_last_newline_is_appended_to_cleanly(tmp_path: Path) -> None:
    path = tmp_path / "r.jsonl"
    path.write_text(make_record("2026-09-28T06:41:00.000Z", {"a": 1}).to_line())
    ledger = hh.HealthLedger(path)
    ledger.append(make_record(NOW, {"a": 2}))
    assert len(ledger.read()) == 2


def test_a_malformed_or_duplicated_line_names_its_number() -> None:
    line = make_record(NOW, {"a": 1}).to_line()
    with pytest.raises(ValueError, match=":2: "):
        hh.HealthLedger.parse(f"{line}\nnot json\n")
    with pytest.raises(ValueError, match="appears twice"):
        hh.HealthLedger.parse(f"{line}\n\n{line}\n")


# ------------------------------------------------------------------------ the forecast


def forecaster(table: Mapping[str, Any] | None = None) -> hh.Forecaster:
    settings = hh.HealthSettings(table or SETTINGS.table)
    config = {"minimum_specs": {"assumptions": {"minimum_gen_tok_s": 10}}}
    return hh.Forecaster(settings, hh.Thresholds(specs_record(), config))


def weekly(values: Sequence[Mapping[str, Any]], start: str = "2026-06-01") -> list[hh.HealthRecord]:
    from datetime import date, timedelta

    day = date.fromisoformat(start)
    return [
        make_record(f"{(day + timedelta(days=7 * i)).isoformat()}T06:41:00.000Z", v)
        for i, v in enumerate(values)
    ]


def driver(fc: Mapping[str, Any], key: str) -> dict[str, Any]:
    return next(d for d in fc["drivers"] if d["id"] == key)


def test_a_battery_fading_on_a_known_line_is_projected_with_its_interval() -> None:
    # 0.2 points of ratio a year from 1.0: crosses 0.8 a year after the first point.
    history = weekly([{"battery.capacity_ratio": 1.0 - 0.2 * 7 * i / 365} for i in range(12)])
    fc = forecaster().forecast(history)
    d = driver(fc, "battery_capacity")
    assert d["state"] == "projected"
    assert d["date"] == "2027-06-01"
    assert d["earliest"] <= d["date"] and d["latest"] is not None and d["latest"] >= d["date"]
    assert fc["binding"] == "battery_capacity" and fc["replace_by"] == "2027-06-01"
    assert fc["warning"] is False


def test_too_few_weeks_is_insufficient_history_and_projects_nothing() -> None:
    fc = forecaster().forecast(weekly([{"battery.capacity_ratio": 1.0}] * 3))
    assert driver(fc, "battery_capacity")["state"] == "insufficient-history"
    assert fc["binding"] is None and fc["replace_by"] is None


def test_a_flat_or_improving_trend_is_not_approaching() -> None:
    fc = forecaster().forecast(weekly([{"storage.free_gb": 400 + i} for i in range(6)]))
    assert driver(fc, "disk_free")["state"] == "not-approaching"


def test_a_value_past_its_threshold_binds_now_and_warns() -> None:
    fc = forecaster().forecast(weekly([{"memory.ram_gb_as_sold": 16.0}]))
    d = driver(fc, "ram_capacity")
    assert d["state"] == "exceeded" and d["threshold"] == 24.0
    assert d["recommended"] == 32.0
    assert fc["binding"] == "ram_capacity" and fc["warning"] is True
    at_minimum = forecaster().forecast(weekly([{"memory.ram_gb_as_sold": 24.0}]))
    assert driver(at_minimum, "ram_capacity")["state"] == "within"


def test_a_level_needs_its_confirmations() -> None:
    once = forecaster().forecast(
        weekly([{"memory.swap_used_ratio": 0.2}, {"memory.swap_used_ratio": 0.6}])
    )
    assert driver(once, "swap")["state"] == "unconfirmed"
    thrice = forecaster().forecast(weekly([{"memory.swap_used_ratio": 0.6}] * 3))
    assert driver(thrice, "swap")["state"] == "exceeded"


def test_a_trend_already_past_is_exceeded() -> None:
    fc = forecaster().forecast(weekly([{"storage.percentage_used": 100}]))
    assert driver(fc, "ssd_wear")["state"] == "exceeded"


def test_the_throughput_series_is_the_union_of_the_mined_weeks() -> None:
    weeks = [
        {"week": f"2026-09-{d:02d}", "median_tok_s": 25.0 - i, "n": 9}
        for i, d in enumerate((1, 8, 15, 22))
    ]
    older = make_record("2026-09-23T06:41:00.000Z", {"throughput.weekly": weeks[:3]})
    newer = make_record(
        "2026-09-29T06:41:00.000Z",
        {"throughput.weekly": weeks[1:], "throughput.gen_tok_s_week_median": 22.0},
    )
    fc = forecaster().forecast([older, newer])
    d = driver(fc, "throughput")
    assert d["points"] == 4 and d["threshold"] == 10.0
    assert d["state"] == "projected"
    assert "scripts/minimum_specs.toml" in d["threshold_source"]


def test_thresholds_from_every_source_and_their_absence() -> None:
    newest = make_record(NOW, {"battery.design_cycle_count": 1000})
    t = hh.Thresholds(specs_record(), {"a": {"b": 3}})
    assert t.resolve({"threshold": 5}, newest) == (5.0, "declared in scripts/host_health.toml")
    assert t.resolve({"threshold_figure": "ram.minimum_gb"}, newest)[0] == 24.0
    assert t.resolve({"threshold_figure": "nope"}, newest)[0] is None
    assert t.resolve({"threshold_config": "a.b"}, newest)[0] == 3.0
    assert t.resolve({"threshold_config": "a.c"}, newest)[0] is None
    assert t.resolve({"threshold_figure_local": "battery.design_cycle_count"}, newest)[0] == 1000.0
    assert t.resolve({"threshold_figure_local": "x"}, newest)[0] is None
    fc = forecaster().forecast(weekly([{"battery.cycle_count": 18}]))
    assert driver(fc, "battery_cycles")["state"] == "unknown"


def test_dated_drivers_and_unknowns() -> None:
    history = weekly([{"platform.os_support_end": "2029-05-01", "storage.percentage_used": None}])
    fc = forecaster().forecast(history)
    os_support = driver(fc, "os_support")
    assert os_support["state"] == "dated" and os_support["date"] == "2029-05-01"
    assert driver(fc, "ssd_wear") == {
        **driver(fc, "ssd_wear"),
        "state": "unknown",
        "reason": "not measured here",
    }
    assert driver(fc, "hardware_support")["reason"] == "not declared"
    assert fc["binding"] == "os_support" and fc["latest"] == "2029-05-01"
    past = forecaster().forecast(weekly([{"platform.os_support_end": "2026-01-01"}]))
    assert driver(past, "os_support")["state"] == "exceeded"


def test_the_machine_interval_is_open_when_no_driver_bounds_it() -> None:
    noisy = [1.0, 0.99, 1.0, 0.985, 1.0, 0.99]
    fc = forecaster().forecast(weekly([{"battery.capacity_ratio": v} for v in noisy]))
    d = driver(fc, "battery_capacity")
    if d["state"] == "projected" and d["latest"] is None:
        assert fc["latest"] is None


# ------------------------------------------------------------------------ the page


def test_the_page_renders_every_block_and_check_sees_a_hand_edit() -> None:
    history = weekly(
        [
            {"battery.capacity_ratio": 1.0 - 0.01 * i, "storage.percentage_used": None}
            for i in range(5)
        ]
    )
    history.append(
        make_record(
            "2026-07-06T06:41:00.000Z",
            {
                "reliability.events": [],
                "throughput.weekly": [],
                "x.flag": True,
                "platform.os": "macOS 26",
            },
        )
    )
    renderer = hh.HealthRenderer(forecaster())
    page = (REPO / SETTINGS["docs_page"]).read_text(encoding="utf-8")
    rendered = renderer.apply(page, history)
    assert renderer.drift(rendered, history) == []
    assert "Replacement by" in rendered and "| Battery full-charge capacity vs design |" in rendered
    assert "none" in rendered and "no qualifying week" in rendered and "| yes |" in rendered
    assert renderer.drift(rendered.replace("Replacement by", "Replaced by"), history) == [
        "forecast"
    ]
    empty = renderer.blocks([])
    assert set(empty) == {"hosts", "latest", "forecast"}
    nothing = renderer.apply(page, weekly([{"battery.capacity_ratio": 1.0}]))
    assert "No driver projects a replacement date yet" in nothing


# ------------------------------------------------------------------------ conditions


def test_conditions_raise_for_a_quiet_host_a_missing_probe_and_a_threshold() -> None:
    history = weekly(
        [{"memory.ram_gb_as_sold": 16.0, "storage.percentage_used": None}] * 2, start="2026-08-03"
    )
    result = hh.ConditionEvaluator(SETTINGS, forecaster()).evaluate(history, NOW)
    assert result["raise"] is True and result["key"] == "host-health"
    text = "\n".join(result["conditions"])
    assert "has not recorded its health for" in text
    assert "SSD wear" in text and "not measured here" in text
    assert "Memory vs vibey's minimum" in text and "past its threshold" in text
    assert "predicted to need replacing" in text
    assert "closes when no condition holds" in result["body"]


def test_conditions_resolve_when_nothing_holds() -> None:
    table = json.loads(json.dumps(SETTINGS.table))
    table["drivers"] = {"thermal": table["drivers"]["thermal"]}
    settings = hh.HealthSettings(table)
    history = weekly([{"thermal.cpu_speed_limit_pct": 100}] * 2, start="2026-09-21")
    result = hh.ConditionEvaluator(settings, forecaster(table)).evaluate(history, NOW)
    assert result == {**result, "raise": False, "body": "", "conditions": []}


# ------------------------------------------------------------------------ the host's unit


def test_the_launchd_agent_runs_weekly_at_the_declared_time() -> None:
    renderer = hh.SchedulerRenderer(SETTINGS["schedule"])
    plist = plistlib.loads(
        renderer.launchd(["/u/uv", "run", "a&b"], "/clone", "/log", "/bin").encode()
    )
    assert plist["Label"] == "dev.vibey.host-health"
    assert plist["StartCalendarInterval"] == {"Weekday": 1, "Hour": 6, "Minute": 41}
    assert plist["ProgramArguments"] == ["/u/uv", "run", "a&b"]
    assert plist["EnvironmentVariables"]["PATH"] == "/bin"
    sunday = hh.SchedulerRenderer({**SETTINGS["schedule"], "weekday": 7})
    assert (
        plistlib.loads(sunday.launchd(["x"], "/", "/l", "").encode())["StartCalendarInterval"][
            "Weekday"
        ]
        == 0
    )
    with pytest.raises(ValueError, match="ISO 1-7"):
        hh.SchedulerRenderer({**SETTINGS["schedule"], "weekday": 0})


def test_the_systemd_timer_is_persistent_and_weekly() -> None:
    service, timer = hh.SchedulerRenderer(SETTINGS["schedule"]).systemd(
        ["/u/uv", "run", "100%"], "/clone", "/log", "/bin"
    )
    assert 'ExecStart="/u/uv" "run" "100%%"' in service
    assert "Type=oneshot" in service
    assert "OnCalendar=Mon *-*-* 06:41:00" in timer and "Persistent=true" in timer
    assert "Unit=dev.vibey.host-health.service" in timer


def test_a_unit_refuses_volatile_and_worktree_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import tempfile

    assert "a reboot empties" in str(hh.UnitPlacement.refusal(tempfile.gettempdir() + "/x"))
    assert hh.UnitPlacement.refusal("/srv/vibey-durable-example/clone") is None
    monkeypatch.setattr(hh.UnitPlacement, "volatile_roots", staticmethod(lambda: []))
    (tmp_path / "lane").mkdir()
    (tmp_path / "lane" / ".git").write_text("gitdir: elsewhere\n")
    refused = hh.UnitPlacement.refusal(str(tmp_path / "lane" / "scripts"))
    assert refused is not None and "linked worktree" in refused


def test_render_unit_writes_files_and_prints_the_load_command(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    home = Path("/srv/vibey-durable-example")  # never written: render-unit writes to --out
    monkeypatch.setattr(hh.UnitPlacement, "refusal", staticmethod(lambda path: None))
    cli = make_cli(REPO, FixedClock(), FakeRunner(), home=home)
    out = tmp_path / "units"
    assert (
        cli.run(
            [
                "--repo",
                str(REPO),
                "render-unit",
                "--out",
                str(out),
                "--platform",
                "launchd",
                "--clone",
                str(home / "clone"),
            ]
        )
        == 0
    )
    printed = capsys.readouterr().out
    assert 'launchctl bootstrap "gui/$(id -u)"' in printed
    assert (out / "dev.vibey.host-health.plist").is_file()
    assert (
        cli.run(["--repo", str(REPO), "render-unit", "--out", str(out), "--platform", "systemd"])
        == 0
    )
    assert "systemctl --user enable --now dev.vibey.host-health.timer" in capsys.readouterr().out
    assert (out / "dev.vibey.host-health.timer").is_file()


def test_render_unit_refuses_a_volatile_clone(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cli = make_cli(REPO, FixedClock(), FakeRunner(), home=tmp_path)
    assert (
        cli.run(
            [
                "--repo",
                str(REPO),
                "render-unit",
                "--out",
                str(tmp_path / "u"),
                "--clone",
                str(tmp_path / "clone"),
            ]
        )
        == 78
    )
    assert "10.h" in capsys.readouterr().err


# ------------------------------------------------------------------------ publishing


class GitWorld(FakeRunner):
    """A fake runner whose `git -C <clone>` commands succeed, `git diff --cached --quiet`
    says there is a change, and `gh pr list` finds the given pull request."""

    def __init__(self, existing_pr: str = "", fail: str = "") -> None:
        super().__init__()
        self.existing_pr = existing_pr
        self.fail = fail

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float,
        env: Mapping[str, str] | None = None,
        cwd: str | None = None,
    ) -> ms.CommandResult:
        self.calls.append(list(argv))
        joined = " ".join(argv)
        if self.fail and self.fail in joined:
            return ms.CommandResult(1, "", f"{self.fail} failed", 0.0)
        if "diff --cached --quiet" in joined:
            return ms.CommandResult(1, "", "", 0.0)
        if argv[:3] == ["gh", "pr", "list"]:
            return ok(self.existing_pr + "\n")
        if argv[:3] == ["gh", "pr", "create"]:
            return ok("https://github.com/the-vibey-project/vibey/pull/9\n")
        return ok("")


def publisher(tmp_path: Path, runner: FakeRunner) -> hh.Publisher:
    def render_check(root: Path, records: Sequence[hh.HealthRecord]) -> list[str]:
        return []

    pub = hh.Publisher(SETTINGS, runner, tmp_path, render_check)
    (pub.clone / ".git").mkdir(parents=True)
    return pub


def test_publish_merges_commits_pushes_and_opens_one_pull_request(tmp_path: Path) -> None:
    runner = GitWorld()
    pub = publisher(tmp_path, runner)
    assert pub.refresh() == pub.clone
    message = pub.publish([make_record(NOW, {"a": 1})], {})
    assert message.startswith("added 1 record(s); opened https://")
    pushed = next(c for c in runner.calls if "push" in c)
    assert "--force-with-lease=refs/heads/automation/host-health" in pushed
    assert "HEAD:automation/host-health" in pushed and "develop" not in pushed[-1]
    assert hh.HealthLedger(pub.clone / SETTINGS["record"]).read()[0].run_id.endswith(NOW)
    assert pub.gh_env()["GH_CONFIG_DIR"] == str(tmp_path / ".config/gh-runner")


def test_publish_updates_an_open_pull_request_and_reports_failures(tmp_path: Path) -> None:
    pub = publisher(tmp_path, GitWorld(existing_pr="42"))
    assert pub.publish([make_record(NOW, {"a": 1})], {}).endswith("updated pull request #42")
    failing = publisher(tmp_path / "f", GitWorld(fail="push"))
    with pytest.raises(RuntimeError, match="push failed"):
        failing.publish([make_record(NOW, {"a": 1})], {})
    no_pr = publisher(tmp_path / "g", GitWorld(fail="pr create"))
    with pytest.raises(RuntimeError, match="gh pr create"):
        no_pr.publish([make_record(NOW, {"a": 1})], {})


def test_publish_with_nothing_new_commits_nothing(tmp_path: Path) -> None:
    class Unchanged(GitWorld):
        def run(self, argv: Sequence[str], **kwargs: Any) -> ms.CommandResult:
            if "diff" in argv:
                self.calls.append(list(argv))
                return ok("")
            return super().run(argv, **kwargs)

    runner = Unchanged()
    assert "nothing to publish" in publisher(tmp_path, runner).publish([], {})
    assert not any("commit" in c for c in runner.calls)


def test_a_missing_clone_is_cloned_from_the_declared_repository(tmp_path: Path) -> None:
    runner = GitWorld()
    pub = hh.Publisher(SETTINGS, runner, tmp_path, lambda root, records: [])
    pub.ensure_clone()
    assert runner.calls[0][:4] == ["git", "clone", "--branch", "develop"]
    assert "https://github.com/the-vibey-project/vibey.git" in runner.calls[0]
    broken = hh.Publisher(SETTINGS, GitWorld(fail="clone"), tmp_path / "b", lambda r, x: [])
    with pytest.raises(RuntimeError, match="git clone"):
        broken.ensure_clone()


def test_a_render_problem_stops_the_publish(tmp_path: Path) -> None:
    pub = hh.Publisher(SETTINGS, GitWorld(), tmp_path, lambda root, records: ["blocks out of date"])
    (pub.clone / ".git").mkdir(parents=True)
    with pytest.raises(RuntimeError, match="blocks out of date"):
        pub.publish([make_record(NOW, {"a": 1})], {})


def test_the_toml_declares_every_key_the_publisher_reads() -> None:
    raw = tomllib.loads((REPO / hh.DEFAULT_CONFIG).read_text(encoding="utf-8"))["host_health"]
    for key in (
        "repository",
        "base",
        "branch",
        "clone_dir",
        "gh_config_dir",
        "commit_title",
        "made_with",
        "git_timeout_s",
        "git_user_name",
        "git_user_email",
        "enabled",
    ):
        assert key in raw["publish"], key
    assert raw["publish"]["base"] == "develop" and raw["publish"]["branch"] != "develop"


# ------------------------------------------------------------------------ the command


class QuietGate:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def wait(self) -> tuple[bool, str, dict[str, Any]]:
        return False, "a test host is never idle", {}


def mini_repo(root: Path) -> Path:
    """The files the command reads, copied: the two configurations, the minimum-specs
    record, and the page."""
    for relative in (
        hh.DEFAULT_CONFIG,
        "scripts/minimum_specs.toml",
        "docs/architecture/evidence/minimum-specs.json",
        SETTINGS["docs_page"],
    ):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text((REPO / relative).read_text(encoding="utf-8"), encoding="utf-8")
    return root


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(hh, "IdleGate", QuietGate)
    return mini_repo(tmp_path / "repo")


def test_measure_appends_a_record_with_a_forecast_and_forecast_prints_it(
    repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cli = make_cli(repo, FixedClock(), FakeRunner(), home=tmp_path / "home")
    out = tmp_path / "r.jsonl"
    assert cli.run(["--repo", str(repo), "measure", "--out", str(out)]) == 0
    records = hh.HealthLedger(out).read()
    assert len(records) == 1 and records[0].forecast["records"] == 1
    assert "micro.cpu_sha256_mib_s" in records[0].by_id()
    assert "no driver projects" in capsys.readouterr().out
    assert cli.run(["--repo", str(repo), "forecast", "--record", str(out)]) == 0
    assert '"as_of"' in capsys.readouterr().out
    assert cli.run(["--repo", str(repo), "forecast", "--record", str(tmp_path / "none")]) == 1


def test_a_probe_that_crashes_is_recorded_not_fatal(
    repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(self: Any) -> list[ms.Figure]:
        raise RuntimeError("bang")

    monkeypatch.setattr(hh.ThermalProbe, "run", boom)
    session = hh.MeasurementSession(
        repo,
        SETTINGS,
        FixedClock(),
        FakeRunner(),
        "Linux",
        tmp_path,
        tmp_path / "root",
        FakeDescriber(),
        which_of(),
    )
    figure = session.run([]).by_id()["thermal.probe"]
    assert figure.status == "skipped" and "RuntimeError: bang" in str(figure.reason)


def test_render_then_check_and_the_append_only_guard(
    repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    record = repo / SETTINGS["record"]
    record.parent.mkdir(parents=True, exist_ok=True)
    first = make_record("2026-09-28T06:41:00.000Z", {"battery.cycle_count": 18})
    record.write_text(first.to_line() + "\n")
    cli = make_cli(repo, FixedClock(), FakeRunner(), home=tmp_path)
    assert cli.run(["--repo", str(repo), "check"]) == 1  # the page is not rendered yet
    assert cli.run(["--repo", str(repo), "render"]) == 0
    assert cli.run(["--repo", str(repo), "check"]) == 0
    rewritten = FakeRunner(
        {("git",): ok(make_record("2026-09-21T06:41:00.000Z", {}).to_line() + "\n")}
    )
    guarded = make_cli(repo, FixedClock(), rewritten, home=tmp_path)
    assert guarded.run(["--repo", str(repo), "check", "--against", "origin/develop"]) == 1
    assert "append-only" in capsys.readouterr().err
    record.write_text("not json\n")
    assert cli.run(["--repo", str(repo), "check"]) == 1


def test_conditions_print_the_issue_as_json(
    repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cli = make_cli(repo, FixedClock(), FakeRunner(), home=tmp_path)
    assert cli.run(["--repo", str(repo), "conditions", "--now", NOW]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["raise"] is False and result["key"] == "host-health"


def test_weekly_keeps_the_week_locally_when_publishing_is_off_or_fails(
    repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = repo / hh.DEFAULT_CONFIG
    original = config.read_text(encoding="utf-8")
    config.write_text(original.replace("enabled = true", "enabled = false"), encoding="utf-8")
    home = tmp_path / "home"
    cli = make_cli(repo, FixedClock(), FakeRunner(), home=home)
    assert cli.run(["--repo", str(repo), "weekly"]) == 0
    assert "recorded locally only" in capsys.readouterr().out
    local = home / DEFAULT_LOCAL_RECORD[2:]
    assert len(hh.HealthLedger(local).read()) == 1
    config.write_text(original, encoding="utf-8")
    failing = make_cli(
        repo, FixedClock("2026-10-12T06:41:00.000Z"), GitWorld(fail="fetch"), home=home
    )
    assert failing.run(["--repo", str(repo), "weekly"]) == 1
    err = capsys.readouterr().err
    assert "could not refresh" in err and "kept in" in err
    assert len(hh.HealthLedger(local).read()) == 2


def test_weekly_publishes_through_the_clone(
    repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = tmp_path / "home"
    clone = mini_repo(home / ".local/share/vibey/host-health/clone")
    (clone / ".git").mkdir()
    cli = make_cli(repo, FixedClock(), GitWorld(), home=home)
    assert cli.run(["--repo", str(repo), "weekly"]) == 0
    assert "opened https://" in capsys.readouterr().out
    assert len(hh.HealthLedger(clone / SETTINGS["record"]).read()) == 1


def test_install_clones_and_writes_into_the_service_managers_directory(
    repo: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    home = repo.parent / "home"
    monkeypatch.setattr(hh.UnitPlacement, "refusal", staticmethod(lambda path: None))
    runner = GitWorld()
    cli = make_cli(repo, FixedClock(), runner, home=home)
    assert cli.run(["--repo", str(repo), "install", "--platform", "systemd"]) == 0
    assert runner.calls[0][:2] == ["git", "clone"]
    assert (home / ".config/systemd/user/dev.vibey.host-health.timer").is_file()
    assert (home / ".local/state/vibey/logs").is_dir()


# ------------------------------------------------------------------------ the SSD on Apple silicon

# The shape `smartctl --json=c -a disk0` printed on Mac17,2 (smartctl 7.5, no sudo,
# 2026-10-01), cut to the fields read; the serial number it also prints is left out here
# and never read by the parser. Exit status 4: the error-information page failed.
APPLE_SMARTCTL = {
    "smartctl": {
        "exit_status": 4,
        "messages": [
            {
                "string": "Read 1 entries from Error Information Log failed: GetLogPage failed:"
                " system=0x38, sub=0x0, code=745",
                "severity": "error",
            }
        ],
    },
    "device": {"name": "disk0", "type": "nvme", "protocol": "NVMe"},
    "model_name": "APPLE SSD AP1024Z",
    "serial_number": "NEVER-READ",
    "smart_status": {"passed": True, "nvme": {"value": 0}},
    "nvme_smart_health_information_log": {
        "critical_warning": 0,
        "available_spare": 100,
        "available_spare_threshold": 99,
        "percentage_used": 1,
        "data_units_written": 71380939,
        "media_errors": 0,
        "unsafe_shutdowns": 10,
        "num_err_log_entries": 0,
        "power_on_hours": 337,
    },
    "power_on_time": {"hours": 337},
}


def test_apple_ssd_is_read_without_sudo_and_its_error_log_failure_is_a_skip() -> None:
    c = ctx("Darwin", {("smartctl",): ok(json.dumps(APPLE_SMARTCTL), code=4), ("df",): ok(DF)})
    figures = by_id(hh.StorageProbe(c).run())
    assert figures["storage.model"].value == "APPLE SSD AP1024Z"
    assert figures["storage.percentage_used"].value == 1
    assert figures["storage.spare_margin_pct"].value == 1
    assert figures["storage.bytes_written"].value == 71380939 * 512_000
    assert figures["storage.tb_written"].value == 36.55
    assert figures["storage.write_gb_per_power_on_hour"].value == 108.4
    assert figures["storage.unsafe_shutdowns"].value == 10
    assert figures["storage.critical_warning"].value == 0
    assert figures["storage.smart_status"].value == "passed"
    error_log = figures["storage.error_log_entries"]
    assert error_log.status == "skipped" and "code=745" in str(error_log.reason)
    endurance = figures["storage.rated_endurance_tb"]
    assert endurance.status == "skipped" and "Apple publishes no endurance" in str(endurance.reason)
    assert "NEVER-READ" not in json.dumps([f.to_dict() for f in figures.values()])


def test_a_declared_endurance_rating_is_a_declared_figure() -> None:
    table = json.loads(json.dumps(SETTINGS.table))
    table["storage"]["endurance"]["APPLE SSD AP1024Z"].update(tbw="600", source="https://x")
    c = replace(
        ctx("Darwin", {("smartctl",): ok(json.dumps(APPLE_SMARTCTL), code=4), ("df",): ok(DF)}),
        settings=hh.HealthSettings(table),
    )
    endurance = by_id(hh.StorageProbe(c).run())["storage.rated_endurance_tb"]
    assert endurance.status == "declared" and endurance.value == 600.0
    other = json.loads(json.dumps(APPLE_SMARTCTL))
    other["model_name"] = "SOME OTHER SSD"
    c2 = ctx("Darwin", {("smartctl",): ok(json.dumps(other)), ("df",): ok(DF)})
    reason = by_id(hh.StorageProbe(c2).run())["storage.rated_endurance_tb"].reason
    assert "no endurance entry" in str(reason)


# ------------------------------------------------------------------------ declared tools


def which_of(*present: str) -> Any:
    return lambda name: f"/bin/{name}" if name in present else None


def test_the_catalog_knows_each_platforms_tools_and_install_commands() -> None:
    mac = hh.ToolCatalog(SETTINGS, "Darwin", which_of("brew"))
    assert list(mac.tools()) == ["smartctl"]
    assert mac.missing() == ["smartctl"]
    assert mac.command("smartctl") == ("brew", ["brew", "install", "smartmontools"])
    assert mac.hint("smartctl") == "install it with `brew install smartmontools`"
    assert hh.ToolCatalog(SETTINGS, "Darwin", which_of("brew", "smartctl")).missing() == []
    bare = hh.ToolCatalog(SETTINGS, "Linux", which_of())
    assert bare.command("smartctl") is None
    assert "sudo apt-get install -y smartmontools` (apt)" in bare.hint("smartctl")
    fedora = hh.ToolCatalog(SETTINGS, "Linux", which_of("dnf"))
    assert fedora.command("smartctl") == ("dnf", ["sudo", "dnf", "install", "-y", "smartmontools"])
    table = json.loads(json.dumps(SETTINGS.table))
    table["tools"]["smartctl"]["install"] = {}
    assert (
        hh.ToolCatalog(hh.HealthSettings(table), "Linux", which_of()).hint("smartctl")
        == "no install declared"
    )
    assert contracts.ToolCatalogInterface in hh.ToolCatalog.__mro__


def test_install_runs_brew_but_only_prints_sudo() -> None:
    class Installs(FakeRunner):
        def __init__(self, present: set[str]) -> None:
            super().__init__({("brew",): ok("")})
            self.present = present

        def run(self, argv: Sequence[str], **kwargs: Any) -> ms.CommandResult:
            self.present.add("smartctl")
            return super().run(argv, **kwargs)

    present = {"brew"}
    runner = Installs(present)
    mac = hh.ToolCatalog(SETTINGS, "Darwin", lambda n: n if n in present else None)
    assert hh.ToolInstaller(mac, runner, 9).ensure() == [
        "tool smartctl: installed with brew (brew install smartmontools)"
    ]
    assert runner.calls == [["brew", "install", "smartmontools"]]
    again = hh.ToolInstaller(mac, FakeRunner(), 9).ensure()
    assert again == ["tool smartctl: present (optional)"]
    ubuntu = hh.ToolCatalog(SETTINGS, "Linux", which_of("apt-get"))
    sudo = FakeRunner()
    lines = hh.ToolInstaller(ubuntu, sudo, 9).ensure()
    assert lines == [
        "tool smartctl: MISSING (optional); it needs privileges, so run it yourself:"
        " sudo apt-get install -y smartmontools"
    ]
    assert sudo.calls == []
    nothing = hh.ToolInstaller(hh.ToolCatalog(SETTINGS, "Linux", which_of()), FakeRunner(), 9)
    assert "MISSING (optional); install it with one of" in nothing.ensure()[0]
    broken = hh.ToolInstaller(
        hh.ToolCatalog(SETTINGS, "Darwin", which_of("brew")), FakeRunner(), 9
    ).ensure()
    assert "did not install it" in broken[0]


def test_the_tools_command_reports(
    repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cli = make_cli(repo, FixedClock(), FakeRunner(), home=tmp_path)
    assert cli.run(["--repo", str(repo), "tools"]) == 0
    assert "tool smartctl:" in capsys.readouterr().out


# ------------------------------------------------------------------------ writes per week


def test_weekly_writes_are_derived_from_the_previous_record() -> None:
    factory = ms.FigureFactory(FixedClock(), "sha256:h")
    before = make_record("2026-09-28T06:41:00.000Z", {"storage.bytes_written": 1_000})
    now = [factory.measured("storage.bytes_written", "b", 8_000, "bytes", "m")]
    host = {"fingerprint": "sha256:h"}
    figure = hh.MeasurementSession.weekly_writes([before], host, now, factory, NOW)
    assert figure.status == "derived" and figure.value == 7_000
    assert figure.inputs is not None and figure.inputs["days_between"] == 7
    first = hh.MeasurementSession.weekly_writes([], host, now, factory, NOW)
    assert "needs an earlier record" in str(first.reason)
    unmeasured = hh.MeasurementSession.weekly_writes([before], host, [], factory, NOW)
    assert "not measured this time" in str(unmeasured.reason)
    same = hh.MeasurementSession.weekly_writes(
        [make_record(NOW, {"storage.bytes_written": 1})], host, now, factory, NOW
    )
    assert same.reason == "no time between records"


# ------------------------------------------------------------------------ fallback and hypotheses


def test_without_a_rating_the_endurance_driver_falls_back_to_wear() -> None:
    newest = make_record(NOW, {"storage.tb_written": 36.55, "storage.percentage_used": 1})
    rated = replace(
        newest,
        figures=newest.figures
        + (
            ms.Figure(
                id="storage.rated_endurance_tb",
                label="r",
                value=None,
                unit="TB",
                status="skipped",
                method="m",
                measured_at=NOW,
                reason="Apple publishes none",
            ),
        ),
    )
    fc = forecaster().forecast([rated])
    d = driver(fc, "ssd_endurance")
    assert d["state"] == "unknown" and d["fallback"] == "ssd_wear"
    assert "Apple publishes none" in d["reason"]
    assert "rests on SSD wear (NVMe percentage used) instead" in d["reason"]
    assert driver(fc, "ssd_wear")["state"] == "insufficient-history"


def test_a_hypothesis_is_offered_only_with_its_driver_and_every_figure() -> None:
    values = {
        "memory.swap_used_ratio": 0.6,
        "memory.swap_used_gib": 14.39,
        "memory.ram_gib": 24.0,
        "memory.swapout_gb_per_hour": 59.0,
        "storage.write_gb_per_power_on_hour": 108.4,
    }
    fc = forecaster().forecast(weekly([values]))
    assert len(fc["hypotheses"]) == 1
    text = fc["hypotheses"][0]
    assert text.startswith("Hypothesis, not a conclusion:")
    assert "14.39 GiB of swap" in text and "108.4 GB per power-on hour" in text
    calm = forecaster().forecast(weekly([{**values, "memory.swap_used_ratio": 0.1}]))
    assert calm["hypotheses"] == []
    partial = dict(values)
    partial.pop("memory.swapout_gb_per_hour")
    assert forecaster().forecast(weekly([partial]))["hypotheses"] == []
    page = (REPO / SETTINGS["docs_page"]).read_text(encoding="utf-8")
    assert "> Hypothesis, not a conclusion" in hh.HealthRenderer(forecaster()).apply(
        page, weekly([values])
    )


def test_install_reports_the_tools_first(
    repo: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    home = repo.parent / "home"
    monkeypatch.setattr(hh.UnitPlacement, "refusal", staticmethod(lambda path: None))
    cli = make_cli(repo, FixedClock(), GitWorld(), home=home, which=which_of("apt-get"))
    assert cli.run(["--repo", str(repo), "install", "--platform", "systemd"]) == 0
    assert "sudo apt-get install -y smartmontools" in capsys.readouterr().out


def test_a_host_below_vibeys_minimum_memory_is_due_for_replacement_now(
    repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The capacity driver is meant to fire at once on a machine smaller than vibey needs:
    16 GiB against the record's 24 GB minimum binds the forecast to the measurement's day."""
    sixteen = 16 * 2**30
    runner = FakeRunner({("sysctl", "-n", "hw.memsize"): ok(f"{sixteen}\n")})
    cli = make_cli(repo, FixedClock(), runner, tmp_path / "home", describer=FakeDescriber(sixteen))
    out = tmp_path / "r.jsonl"
    assert cli.run(["--repo", str(repo), "measure", "--out", str(out)]) == 0
    assert "replace by 2026-10-05 (2026-10-05 to 2026-10-05), bound by ram_capacity" in (
        capsys.readouterr().out
    )
    fc = hh.HealthLedger(out).read()[0].forecast
    ram = driver(fc, "ram_capacity")
    assert ram["state"] == "exceeded" and ram["value"] == 16.0 and ram["threshold"] == 24.0
    assert fc["warning"] is True


def test_at_exactly_the_minimum_nothing_binds(
    repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    runner = FakeRunner({("sysctl", "-n", "hw.memsize"): ok(f"{24 * 2**30}\n")})
    cli = make_cli(repo, FixedClock(), runner, tmp_path / "home")
    assert cli.run(["--repo", str(repo), "measure", "--out", str(tmp_path / "r.jsonl")]) == 0
    assert "no driver projects a replacement date yet" in capsys.readouterr().out
