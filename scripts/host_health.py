# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The health of the machine vibey and krypton run on, and how long until it needs replacing.

    python scripts/host_health.py measure      # probe this host, append to its own record
    python scripts/host_health.py forecast     # print this host's forecast from its record
    python scripts/host_health.py render       # rewrite the page's GENERATED blocks
    python scripts/host_health.py check        # exit 1 if the record or the page is out of step
    python scripts/host_health.py conditions   # the one tracking issue: raise or resolve
    python scripts/host_health.py render-unit  # write the weekly launchd/systemd unit to --out
    python scripts/host_health.py install      # clone, render the unit into the service manager's
                                               # directory, and print the operator's load command
    python scripts/host_health.py weekly       # what the unit runs: measure, then publish

Every probe runs on the host, without sudo, and records each figure as measured, declared,
derived or skipped -- skipped with the reason, never with an invented number (sub-doctrine
10.f). The record (`[host_health] record`, JSON lines, schema `vibey-host-health/1`) is
append-only: a week is a new line, never an edit. The forecast fits each driver's weekly
history to its declared replacement threshold (`scripts/host_health_forecast.py`); the
machine's replacement date is the earliest driver's, with its interval, naming the driver
that binds. Everything configurable is in `scripts/host_health.toml` (ADR-0051).
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import glob
import hashlib
import json
import os
import platform
import re
import shutil
import sys
import tempfile
import time
import tomllib
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from statistics import median
from typing import Any
from xml.sax.saxutils import escape  # nosec B406 -- escaping text we write, parsing none

try:
    from scripts.host_health_forecast import TheilSenEstimator, ThresholdProjector
    from scripts.interfaces.host_health_interface import (
        ConditionEvaluatorInterface,
        ForecasterInterface,
        HealthLedgerInterface,
        HealthRendererInterface,
        HostIdentityInterface,
        PublisherInterface,
        SchedulerRendererInterface,
        ToolCatalogInterface,
    )
    from scripts.interfaces.minimum_specs_interface import (
        ClockInterface,
        CommandRunnerInterface,
        ProbeInterface,
    )
    from scripts.minimum_specs import (
        GIB,
        Figure,
        FigureFactory,
        HostDescriber,
        IdleGate,
        LlamaServerLog,
        SpecsRecord,
        SpecsSettings,
        SubprocessRunner,
        SystemClock,
    )
except ModuleNotFoundError:  # Direct execution keeps the script directory on sys.path.
    from host_health_forecast import (  # type: ignore[import-not-found,no-redef]
        TheilSenEstimator,
        ThresholdProjector,
    )
    from interfaces.host_health_interface import (  # type: ignore[import-not-found,no-redef]
        ConditionEvaluatorInterface,
        ForecasterInterface,
        HealthLedgerInterface,
        HealthRendererInterface,
        HostIdentityInterface,
        PublisherInterface,
        SchedulerRendererInterface,
        ToolCatalogInterface,
    )
    from interfaces.minimum_specs_interface import (  # type: ignore[import-not-found,no-redef]
        ClockInterface,
        CommandRunnerInterface,
        ProbeInterface,
    )
    from minimum_specs import (  # type: ignore[import-not-found,no-redef]
        GIB,
        Figure,
        FigureFactory,
        HostDescriber,
        IdleGate,
        LlamaServerLog,
        SpecsRecord,
        SpecsSettings,
        SubprocessRunner,
        SystemClock,
    )

SCRIPT = "scripts/host_health.py"
SCHEMA = "vibey-host-health/1"
DEFAULT_CONFIG = "scripts/host_health.toml"
MIB = 1024**2
STATES = (
    "exceeded",
    "projected",
    "dated",
    "not-approaching",
    "insufficient-history",
    "unconfirmed",
    "within",
    "unknown",
)


# ------------------------------------------------------------------------ settings


@dataclass(frozen=True)
class HealthSettings:
    """Everything `scripts/host_health.toml` declares. A key missing there is a KeyError
    here, not a silent default."""

    table: Mapping[str, Any]

    @classmethod
    def load(cls, path: Path) -> HealthSettings:
        return cls(tomllib.loads(path.read_text(encoding="utf-8"))["host_health"])

    def __getitem__(self, key: str) -> Any:
        return self.table[key]

    @property
    def drivers(self) -> Mapping[str, Mapping[str, Any]]:
        return self.table["drivers"]


class Stamp:
    """The record's one time format (ISO-8601 UTC ending in Z) and day arithmetic on it."""

    @staticmethod
    def parse(text: str) -> datetime:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC)

    @classmethod
    def days(cls, text: str) -> float:
        """Days since the Unix epoch: the x axis every fit uses."""
        return cls.parse(text).timestamp() / 86400

    @staticmethod
    def day_of(days: float) -> str:
        return datetime.fromtimestamp(days * 86400, UTC).date().isoformat()

    @staticmethod
    def iso(moment: datetime) -> str:
        return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    @staticmethod
    def week_of(moment: datetime) -> str:
        """The Monday (UTC) of the ISO week `moment` falls in."""
        day = moment.astimezone(UTC).date()
        return (day - timedelta(days=day.weekday())).isoformat()


@dataclass(frozen=True)
class ProbeContext:
    """What every probe is given: the settings, how to run a command and read a file, the
    platform, and the clock -- so a test can stand up any host from fixtures."""

    settings: HealthSettings
    runner: CommandRunnerInterface
    figures: FigureFactory
    system: str
    root: Path = Path("/")
    home: Path = field(default_factory=Path.home)
    wall: Callable[[], float] = time.time
    which: Callable[[str], str | None] = shutil.which

    @property
    def timeout(self) -> float:
        return float(self.settings["command_timeout_s"])

    def path(self, text: str) -> Path:
        """A declared path on this host: `~` is the home, an absolute path is under root."""
        if text.startswith("~"):
            return self.home / text[1:].lstrip("/")
        return self.root / text.lstrip("/") if text.startswith("/") else Path(text)

    def read(self, text: str) -> str | None:
        with contextlib.suppress(OSError):
            return self.path(text).read_text(encoding="utf-8", errors="replace")
        return None

    def glob(self, pattern: str) -> list[Path]:
        return sorted(Path(p) for p in glob.glob(str(self.path(pattern))))

    def run(self, argv: Sequence[str]) -> Any:
        return self.runner.run(argv, timeout=self.timeout)

    @property
    def mac(self) -> bool:
        return self.system == "Darwin"


# ------------------------------------------------------------------------ tools


class ToolCatalog(ToolCatalogInterface):
    """The tools `[host_health.tools]` declares for this platform, which are missing, and the
    package-manager command that installs each (the first manager present, in order)."""

    def __init__(
        self,
        settings: HealthSettings,
        system: str,
        which: Callable[[str], str | None] = shutil.which,
    ) -> None:
        self._cfg = settings["tools"]
        self._system = system
        self._which = which

    def tools(self) -> dict[str, Mapping[str, Any]]:
        return {
            name: spec
            for name, spec in self._cfg.items()
            if isinstance(spec, Mapping) and self._system in spec.get("platforms", [])
        }

    def managers(self) -> list[str]:
        """The platform's package managers that are present, in the declared order."""
        declared = self._cfg["managers"].get(self._system, [])
        return [m for m in declared if self._which(str(self._cfg["detect"][m]))]

    def missing(self) -> list[str]:
        return [name for name, spec in self.tools().items() if not self._which(str(spec["binary"]))]

    def command(self, tool: str) -> tuple[str, list[str]] | None:
        """(manager, argv) of the first present manager that can install `tool`."""
        install = self.tools()[tool]["install"]
        for manager in self.managers():
            if manager in install:
                return manager, [str(part) for part in install[manager]]
        return None

    def hint(self, tool: str) -> str:
        """How to install `tool` here, for a skipped figure's reason."""
        found = self.command(tool)
        if found is not None:
            return f"install it with `{' '.join(found[1])}`"
        install = self.tools()[tool]["install"]
        options = [
            f"`{' '.join(str(p) for p in install[m])}` ({m})"
            for m in self._cfg["managers"].get(self._system, [])
            if m in install
        ]
        return "install it with one of " + ", ".join(options) if options else "no install declared"


class ToolInstaller:
    """What `install` does about the declared tools: installs a missing one with a command
    that needs no privileges, and prints the command for one that does (never runs sudo)."""

    def __init__(
        self, catalog: ToolCatalog, runner: CommandRunnerInterface, timeout: float
    ) -> None:
        self._catalog = catalog
        self._runner = runner
        self._timeout = timeout

    def ensure(self) -> list[str]:
        """One line per tool for this platform: present, installed, or what to run."""
        lines: list[str] = []
        missing = set(self._catalog.missing())
        for name, spec in self._catalog.tools().items():
            role = "required" if spec.get("required") else "optional"
            if name not in missing:
                lines.append(f"tool {name}: present ({role})")
                continue
            found = self._catalog.command(name)
            if found is None:
                lines.append(f"tool {name}: MISSING ({role}); {self._catalog.hint(name)}")
                continue
            manager, argv = found
            if argv[0] == "sudo":
                lines.append(
                    f"tool {name}: MISSING ({role}); it needs privileges, so run it yourself:"
                    f" {' '.join(argv)}"
                )
                continue
            result = self._runner.run(argv, timeout=self._timeout)
            if result.returncode == 0 and name not in self._catalog.missing():
                lines.append(f"tool {name}: installed with {manager} ({' '.join(argv)})")
            else:
                lines.append(
                    f"tool {name}: `{' '.join(argv)}` did not install it ({result.tail()})"
                )
        return lines


# ------------------------------------------------------------------------ the host


class HostIdentity(HostIdentityInterface):
    """minimum_specs' HostDescriber for the description, plus a fingerprint that is stable
    across OS upgrades and identifies the machine to its own history and to nobody else: a
    truncated SHA-256 over the hardware facts and the platform identifier, which is hashed
    and never stored, like every serial number and the host name (SD-01 §1)."""

    def __init__(self, ctx: ProbeContext, describer: HostDescriber | None = None) -> None:
        self._ctx = ctx
        self._describer = describer or HostDescriber(ctx.runner)

    def platform_id(self) -> str:
        if self._ctx.mac:
            out = str(self._ctx.run(["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"]).stdout)
            found = re.search(r'"IOPlatformUUID"\s*=\s*"([^"]+)"', out)
            return found.group(1) if found else ""
        return (self._ctx.read("/etc/machine-id") or "").strip()

    @staticmethod
    def fingerprint(info: Mapping[str, Any], platform_id: str, chars: int) -> str:
        basis = "|".join(
            str(info.get(key) or "")
            for key in ("system", "arch", "model", "chip", "ram_bytes", "cores_total")
        )
        return "sha256:" + hashlib.sha256(f"{basis}|{platform_id}".encode()).hexdigest()[:chars]

    def describe(self) -> dict[str, Any]:
        info = self._describer.describe()
        never = set(self._ctx.settings["privacy"]["never_record"])
        clean = {k: v for k, v in info.items() if k not in never}
        clean["fingerprint"] = self.fingerprint(
            clean, self.platform_id(), int(self._ctx.settings["privacy"]["fingerprint_chars"])
        )
        return clean


# ------------------------------------------------------------------------ probes


class StorageProbe(ProbeInterface):
    """SSD health through smartctl (NVMe wear, spare, writes, media errors, hours), the OS's
    own SMART verdict where smartctl is absent (macOS `diskutil`), and the data volume's
    free space for the trend."""

    name = "storage"

    def __init__(self, ctx: ProbeContext) -> None:
        self._ctx = ctx
        self._cfg = ctx.settings["storage"]

    @staticmethod
    def parse_smartctl(data: Mapping[str, Any]) -> dict[str, Any]:
        """The fields the drivers use, from `smartctl --json -a`; absent ones are absent. The
        serial number smartctl prints is never read."""
        out: dict[str, Any] = {}
        if data.get("model_name"):
            out["model"] = str(data["model_name"])
        status = data.get("smart_status")
        if isinstance(status, Mapping) and "passed" in status:
            out["smart_passed"] = bool(status["passed"])
        log = data.get("nvme_smart_health_information_log")
        if isinstance(log, Mapping):
            for key in (
                "percentage_used",
                "available_spare",
                "available_spare_threshold",
                "critical_warning",
                "unsafe_shutdowns",
                "media_errors",
            ):
                if key in log:
                    out[key] = int(log[key])
            if "data_units_written" in log:  # NVMe data units are 1000 x 512 bytes
                out["bytes_written"] = int(log["data_units_written"]) * 512_000
                out["tb_written"] = round(out["bytes_written"] / 1e12, 2)
            if "num_err_log_entries" in log:
                out["error_log_entries"] = int(log["num_err_log_entries"])
        hours = data.get("power_on_time", {})
        if isinstance(hours, Mapping) and "hours" in hours:
            out["power_on_hours"] = int(hours["hours"])
        if out.get("bytes_written") and out.get("power_on_hours"):
            out["write_gb_per_power_on_hour"] = round(
                out["bytes_written"] / 1e9 / out["power_on_hours"], 1
            )
        smartctl = data.get("smartctl", {})
        messages = smartctl.get("messages", []) if isinstance(smartctl, Mapping) else []
        for message in messages:
            text = str(message.get("string", "")) if isinstance(message, Mapping) else ""
            if "Error Information Log" in text:
                # The error-information page is unreadable (Apple's controller answers
                # GetLogPage with code 745): its entries are unknown, not zero.
                out.pop("error_log_entries", None)
                out["error_log_failure"] = text
        return out

    @staticmethod
    def parse_df(text: str) -> tuple[int, int] | None:
        """(size, available) in bytes from `df -Pk <volume>`."""
        lines = [line for line in text.strip().splitlines() if line.strip()]
        if len(lines) < 2:
            return None
        parts = lines[-1].split()
        if len(parts) < 4 or not parts[1].isdigit() or not parts[3].isdigit():
            return None
        return int(parts[1]) * 1024, int(parts[3]) * 1024

    @staticmethod
    def parse_diskutil(text: str) -> str | None:
        found = re.search(r"SMART Status:\s*(.+)", text)
        return found.group(1).strip() if found else None

    def _device(self, smartctl: str, missing: str) -> tuple[str, str]:
        """(device, why there is none)."""
        if self._ctx.mac:
            return str(self._cfg["device_macos"]), ""
        declared = str(self._cfg["device_linux"])
        if declared:
            return declared, ""
        scan = self._ctx.run([smartctl, "--scan"])
        if scan.returncode == 127:
            return "", missing
        first = str(scan.stdout).strip().splitlines()
        if not first:
            return "", "smartctl --scan listed no device"
        return first[0].split()[0], ""

    SMART_IDS: Mapping[str, tuple[str, str, str]] = {
        "percentage_used": ("storage.percentage_used", "SSD wear: NVMe percentage used", "%"),
        "spare_margin_pct": (
            "storage.spare_margin_pct",
            "SSD available spare above its threshold",
            "percentage points",
        ),
        "available_spare": ("storage.available_spare_pct", "SSD available spare", "%"),
        "tb_written": ("storage.tb_written", "SSD data written", "TB"),
        "bytes_written": ("storage.bytes_written", "SSD data written, in bytes", "bytes"),
        "media_errors": ("storage.media_errors", "SSD media and data integrity errors", "count"),
        "critical_warning": ("storage.critical_warning", "SSD critical warning bits", "bits"),
        "unsafe_shutdowns": ("storage.unsafe_shutdowns", "SSD unsafe shutdowns", "count"),
        "power_on_hours": ("storage.power_on_hours", "SSD power-on hours", "h"),
        "write_gb_per_power_on_hour": (
            "storage.write_gb_per_power_on_hour",
            "SSD writes per power-on hour (lifetime average)",
            "GB/h",
        ),
        "error_log_entries": ("storage.error_log_entries", "SSD error-log entries", "count"),
        "model": ("storage.model", "SSD model", "text"),
    }

    def run(self) -> list[Figure]:
        f = self._ctx.figures
        tools = ToolCatalog(self._ctx.settings, self._ctx.system, self._ctx.which)
        smartctl = str(self._ctx.settings["tools"]["smartctl"]["binary"])
        missing = f"smartctl not found; {tools.hint('smartctl')}"
        figures: list[Figure] = []
        device, why = self._device(smartctl, missing)
        values: dict[str, Any] = {}
        method = f"{smartctl} --json=c -a {device}"
        if device:
            result = self._ctx.run([smartctl, "--json=c", "-a", device])
            if result.returncode == 127:
                why = missing
            else:
                try:
                    values = self.parse_smartctl(json.loads(str(result.stdout) or "{}"))
                except json.JSONDecodeError:
                    values = {}
                # smartctl's exit status is a bit mask; bit 1 is "device open failed". Bit 2
                # ("a command failed") alone is the unreadable error-log page, kept below.
                if result.returncode & 0b10 or not values:
                    why = f"smartctl could not read {device} without privileges ({result.tail()})"
        if "available_spare" in values and "available_spare_threshold" in values:
            values["spare_margin_pct"] = (
                values["available_spare"] - values["available_spare_threshold"]
            )
        notes = {
            "write_gb_per_power_on_hour": "Data Units Written x 512,000 bytes / Power On Hours",
            "bytes_written": "Data Units Written x 512,000 bytes (NVMe data unit)",
        }
        for key, (fid, label, unit) in self.SMART_IDS.items():
            if key in values:
                figures.append(
                    f.measured(fid, label, values[key], unit, method, note=notes.get(key))
                )
            elif key == "error_log_entries" and "error_log_failure" in values:
                reason = f"smartctl could not read the error-information log page: {values['error_log_failure']}"
                figures.append(f.skipped(fid, label, unit, method, reason))
            else:
                reason = why or f"{device} reported no {key.replace('_', ' ')} (not an NVMe log?)"
                figures.append(f.skipped(fid, label, unit, method, reason))
        figures.append(self._endurance(values.get("model")))
        figures.append(self._smart_status(values, device, method))
        figures.extend(self._free_space())
        return figures

    def _endurance(self, model: str | None) -> Figure:
        f = self._ctx.figures
        fid, label = "storage.rated_endurance_tb", "SSD rated endurance (TBW)"
        method = "[host_health.storage.endurance] in scripts/host_health.toml"
        if not model:
            return f.skipped(fid, label, "TB", method, "the drive's model was not read")
        entry = self._cfg.get("endurance", {}).get(model)
        if entry is None:
            return f.skipped(
                fid, label, "TB", method, f"no endurance entry is declared for {model!r}"
            )
        if not entry["tbw"]:
            return f.skipped(
                fid, label, "TB", method, f"{entry['reason']} (verified {entry['last_verified']})"
            )
        figure = f.declared(fid, label, float(entry["tbw"]), "TB", method, str(entry["source"]))
        return replace(figure, note=f"{entry['reason']}; last verified {entry['last_verified']}")

    def _smart_status(self, values: Mapping[str, Any], device: str, method: str) -> Figure:
        f = self._ctx.figures
        label = "SSD SMART overall status"
        if "smart_passed" in values:
            verdict = "passed" if values["smart_passed"] else "FAILED"
            return f.measured("storage.smart_status", label, verdict, "verdict", method)
        if self._ctx.mac:
            argv = ["diskutil", "info", device]
            status = self.parse_diskutil(str(self._ctx.run(argv).stdout))
            if status:
                return f.measured("storage.smart_status", label, status, "verdict", " ".join(argv))
        return f.skipped(
            "storage.smart_status", label, "verdict", method, "no SMART verdict was readable"
        )

    def _free_space(self) -> list[Figure]:
        f = self._ctx.figures
        volume = str(self._cfg["volume_macos" if self._ctx.mac else "volume_linux"])
        argv = ["df", "-Pk", volume]
        parsed = self.parse_df(str(self._ctx.run(argv).stdout))
        method = " ".join(argv)
        if parsed is None:
            reason = f"df gave nothing readable for {volume}"
            return [
                f.skipped("storage.free_gb", "Free disk on the data volume", "GB", method, reason),
                f.skipped("storage.size_gb", "Data volume size", "GB", method, reason),
            ]
        size, free = parsed
        return [
            f.measured(
                "storage.free_gb",
                "Free disk on the data volume",
                round(free / 1e9, 1),
                "GB",
                method,
            ),
            f.measured("storage.size_gb", "Data volume size", round(size / 1e9, 1), "GB", method),
        ]


class BatteryProbe(ProbeInterface):
    """Cycle count, full-charge capacity against design, the design cycle count and the
    gauge's own condition. A machine without a battery records that, as skipped."""

    name = "battery"
    _IOREG = re.compile(r'^\s*"(?P<key>[A-Za-z0-9]+)" = (?P<value>-?\d+|Yes|No)\s*$', re.M)

    def __init__(self, ctx: ProbeContext) -> None:
        self._ctx = ctx
        self._cfg = ctx.settings["battery"]

    @classmethod
    def parse_ioreg(cls, text: str) -> dict[str, Any]:
        """The battery entry's top-level numeric and yes/no keys (nested blobs ignored)."""
        out: dict[str, Any] = {}
        for match in cls._IOREG.finditer(text):
            value = match["value"]
            out[match["key"]] = value == "Yes" if value in ("Yes", "No") else int(value)
        return out

    @staticmethod
    def parse_condition(text: str) -> str | None:
        found = re.search(r"Condition:\s*(.+)", text)
        return found.group(1).strip() if found else None

    @staticmethod
    def capacity_ratio(values: Mapping[str, Any]) -> tuple[float, str] | None:
        design = values.get("DesignCapacity")
        if not design:
            return None
        for key in ("AppleRawMaxCapacity", "NominalChargeCapacity"):
            if values.get(key):
                return round(values[key] / design, 4), key
        return None

    def run(self) -> list[Figure]:
        return self._mac() if self._ctx.mac else self._linux()

    def _all_skipped(self, method: str, reason: str) -> list[Figure]:
        f = self._ctx.figures
        return [
            f.skipped(fid, label, unit, method, reason)
            for fid, label, unit in (
                ("battery.capacity_ratio", "Battery full-charge capacity / design", "ratio"),
                ("battery.cycle_count", "Battery cycle count", "count"),
                ("battery.design_cycle_count", "Battery design cycle count", "count"),
                ("battery.condition", "Battery condition", "verdict"),
            )
        ]

    def _mac(self) -> list[Figure]:
        f = self._ctx.figures
        argv = ["ioreg", "-rn", str(self._cfg["ioreg_class"])]
        method = " ".join(argv)
        values = self.parse_ioreg(str(self._ctx.run(argv).stdout))
        if "DesignCapacity" not in values:
            return self._all_skipped(method, "no battery: the gauge's registry entry is absent")
        figures: list[Figure] = []
        ratio = self.capacity_ratio(values)
        if ratio is None:
            figures.append(
                f.skipped(
                    "battery.capacity_ratio",
                    "Battery full-charge capacity / design",
                    "ratio",
                    method,
                    "the gauge reports no full-charge capacity",
                )
            )
        else:
            figures.append(
                f.measured(
                    "battery.capacity_ratio",
                    "Battery full-charge capacity / design",
                    ratio[0],
                    "ratio",
                    f"{method}: {ratio[1]} / DesignCapacity",
                    conditions={"on_ac": values.get("ExternalConnected")},
                )
            )
        for fid, key, label in (
            ("battery.cycle_count", "CycleCount", "Battery cycle count"),
            ("battery.design_cycle_count", "DesignCycleCount9C", "Battery design cycle count"),
        ):
            if key in values:
                figures.append(f.measured(fid, label, values[key], "count", f"{method}: {key}"))
            else:
                figures.append(
                    f.skipped(fid, label, "count", method, f"the gauge reports no {key}")
                )
        profile = ["system_profiler", "SPPowerDataType"]
        condition = self.parse_condition(str(self._ctx.run(profile).stdout))
        if condition:
            figures.append(
                f.measured(
                    "battery.condition",
                    "Battery condition",
                    condition,
                    "verdict",
                    " ".join(profile),
                )
            )
        else:
            figures.append(
                f.skipped(
                    "battery.condition",
                    "Battery condition",
                    "verdict",
                    " ".join(profile),
                    "system_profiler printed no Condition",
                )
            )
        return figures

    def _linux(self) -> list[Figure]:
        base = str(self._cfg["power_supply_dir"])
        method = f"read {base}/BAT*/"
        for supply in self._ctx.glob(f"{base}/*"):
            kind = (self._read(supply / "type") or "").strip()
            if kind != "Battery":
                continue
            return self._linux_battery(supply, method)
        return self._all_skipped(method, "no battery: no power supply of type Battery")

    @staticmethod
    def _read(path: Path) -> str | None:
        with contextlib.suppress(OSError):
            return path.read_text(encoding="utf-8").strip()
        return None

    def _number(self, supply: Path, name: str) -> float | None:
        text = self._read(supply / name)
        return float(text) if text and re.fullmatch(r"-?\d+(\.\d+)?", text) else None

    def _linux_battery(self, supply: Path, method: str) -> list[Figure]:
        f = self._ctx.figures
        figures: list[Figure] = []
        full = self._number(supply, "energy_full") or self._number(supply, "charge_full")
        design = self._number(supply, "energy_full_design") or self._number(
            supply, "charge_full_design"
        )
        label = "Battery full-charge capacity / design"
        if full and design:
            figures.append(
                f.measured(
                    "battery.capacity_ratio",
                    label,
                    round(full / design, 4),
                    "ratio",
                    f"{method}: (energy|charge)_full / _full_design",
                )
            )
        else:
            figures.append(
                f.skipped(
                    "battery.capacity_ratio",
                    label,
                    "ratio",
                    method,
                    "no full/design capacity files",
                )
            )
        cycles = self._number(supply, "cycle_count")
        if cycles is not None and cycles > 0:
            figures.append(
                f.measured(
                    "battery.cycle_count",
                    "Battery cycle count",
                    int(cycles),
                    "count",
                    f"{method}: cycle_count",
                )
            )
        else:
            figures.append(
                f.skipped(
                    "battery.cycle_count",
                    "Battery cycle count",
                    "count",
                    method,
                    "cycle_count is absent or 0 (the driver does not report it)",
                )
            )
        figures.append(
            f.skipped(
                "battery.design_cycle_count",
                "Battery design cycle count",
                "count",
                method,
                "the Linux power-supply class exposes no design cycle count",
            )
        )
        health = self._read(supply / "health")
        if health:
            figures.append(
                f.measured(
                    "battery.condition", "Battery condition", health, "verdict", f"{method}: health"
                )
            )
        else:
            figures.append(
                f.skipped(
                    "battery.condition",
                    "Battery condition",
                    "verdict",
                    method,
                    "the driver exposes no health file",
                )
            )
        return figures


class ThermalProbe(ProbeInterface):
    """Whether the OS is capping the CPU for heat: `pmset -g therm` on macOS; on Linux the
    thermal zones, the frequency caps against the hardware maximum, and the throttle counts."""

    name = "thermal"

    def __init__(self, ctx: ProbeContext) -> None:
        self._ctx = ctx
        self._cfg = ctx.settings["thermal"]

    @staticmethod
    def parse_pmset(text: str) -> dict[str, Any]:
        out: dict[str, Any] = {}
        limit = re.search(r"CPU_Speed_Limit\s*=\s*(\d+)", text)
        if limit:
            out["cpu_speed_limit_pct"] = int(limit.group(1))
        elif "No CPU power status has been recorded" in text:
            out["cpu_speed_limit_pct"] = 100
        level = re.search(r"(?i)thermal[_ ]warning[_ ]level\s*=\s*(\d+)", text)
        if level:
            out["warning_level"] = int(level.group(1))
        elif "No thermal warning level has been recorded" in text:
            out["warning_level"] = 0
        return out

    def run(self) -> list[Figure]:
        return self._mac() if self._ctx.mac else self._linux()

    def _mac(self) -> list[Figure]:
        f = self._ctx.figures
        argv = ["pmset", "-g", "therm"]
        method = " ".join(argv)
        values = self.parse_pmset(str(self._ctx.run(argv).stdout))
        figures: list[Figure] = []
        for key, fid, label, unit, note in (
            (
                "cpu_speed_limit_pct",
                "thermal.cpu_speed_limit_pct",
                "CPU speed limit",
                "%",
                "100 when pmset records no CPU power status (no limit since boot)",
            ),
            (
                "warning_level",
                "thermal.warning_level",
                "Thermal warning level",
                "level",
                "0 when pmset records no thermal warning level",
            ),
        ):
            if key in values:
                figures.append(f.measured(fid, label, values[key], unit, method, note=note))
            else:
                figures.append(f.skipped(fid, label, unit, method, "pmset printed neither form"))
        return figures

    def _linux(self) -> list[Figure]:
        f = self._ctx.figures
        figures: list[Figure] = []
        temps = [
            int(text) / 1000
            for path in self._ctx.glob(str(self._cfg["thermal_zone_glob"]))
            if (text := (self._read(path) or "")).lstrip("-").isdigit()
        ]
        zone_method = f"read {self._cfg['thermal_zone_glob']}"
        if temps:
            figures.append(
                f.measured(
                    "thermal.max_zone_c", "Hottest thermal zone", max(temps), "°C", zone_method
                )
            )
        else:
            figures.append(
                f.skipped(
                    "thermal.max_zone_c", "Hottest thermal zone", "°C", zone_method, "no zones"
                )
            )
        ratios = []
        for cpu in self._ctx.glob(str(self._cfg["cpufreq_glob"])):
            cap, hw = self._read(cpu / "scaling_max_freq"), self._read(cpu / "cpuinfo_max_freq")
            if cap and hw and cap.isdigit() and hw.isdigit() and int(hw):
                ratios.append(int(cap) / int(hw))
        freq_method = f"read {self._cfg['cpufreq_glob']}/scaling_max_freq / cpuinfo_max_freq"
        if ratios:
            figures.append(
                f.measured(
                    "thermal.cpu_speed_limit_pct",
                    "CPU speed limit",
                    round(min(ratios) * 100),
                    "%",
                    freq_method,
                )
            )
        else:
            figures.append(
                f.skipped(
                    "thermal.cpu_speed_limit_pct",
                    "CPU speed limit",
                    "%",
                    freq_method,
                    "no cpufreq directory (a VM, or a kernel without cpufreq)",
                )
            )
        counts = [
            int(text)
            for path in self._ctx.glob(str(self._cfg["throttle_glob"]))
            if (text := (self._read(path) or "")).isdigit()
        ]
        throttle_method = f"read {self._cfg['throttle_glob']}"
        if counts:
            figures.append(
                f.measured(
                    "thermal.throttle_events",
                    "Thermal throttle events since boot",
                    sum(counts),
                    "count",
                    throttle_method,
                )
            )
        else:
            figures.append(
                f.skipped(
                    "thermal.throttle_events",
                    "Thermal throttle events since boot",
                    "count",
                    throttle_method,
                    "no thermal_throttle counters (not an x86 CPU, or not exposed)",
                )
            )
        return figures

    @staticmethod
    def _read(path: Path) -> str | None:
        with contextlib.suppress(OSError):
            return path.read_text(encoding="utf-8").strip()
        return None


class MemoryProbe(ProbeInterface):
    """Memory, swap and pressure: what the workload costs the machine week after week."""

    name = "memory"

    def __init__(self, ctx: ProbeContext) -> None:
        self._ctx = ctx

    @staticmethod
    def parse_swapusage(text: str) -> tuple[float, float] | None:
        """(total, used) in MiB from `sysctl vm.swapusage`."""
        total = re.search(r"total = ([\d.]+)([MG])", text)
        used = re.search(r"used = ([\d.]+)([MG])", text)
        if not total or not used:
            return None

        def mib(match: re.Match[str]) -> float:
            return float(match.group(1)) * (1024 if match.group(2) == "G" else 1)

        return mib(total), mib(used)

    @staticmethod
    def parse_vm_stat(text: str) -> dict[str, int]:
        out: dict[str, int] = {}
        for match in re.finditer(r'^"?([A-Za-z -]+?)"?:\s+(\d+)\.?$', text, re.M):
            out[match.group(1).strip().lower()] = int(match.group(2))
        return out

    @staticmethod
    def parse_meminfo(text: str) -> dict[str, int]:
        """/proc/meminfo, in bytes."""
        return {
            m.group(1): int(m.group(2)) * 1024
            for m in re.finditer(r"^(\w+):\s+(\d+) kB$", text, re.M)
        }

    @staticmethod
    def parse_psi(text: str) -> dict[str, float]:
        out: dict[str, float] = {}
        for line in text.splitlines():
            parts = line.split()
            if parts and parts[0] in ("some", "full"):
                for part in parts[1:]:
                    key, _, value = part.partition("=")
                    if key == "avg300":
                        out[parts[0]] = float(value)
        return out

    @staticmethod
    def parse_boottime(text: str) -> float | None:
        found = re.search(r"sec = (\d+)", text)
        return float(found.group(1)) if found else None

    def run(self) -> list[Figure]:
        return self._mac() if self._ctx.mac else self._linux()

    def _ram(self, ram_bytes: int, method: str) -> list[Figure]:
        f = self._ctx.figures
        gib = ram_bytes / GIB
        return [
            f.measured("memory.ram_gib", "Installed memory", round(gib, 2), "GiB", method),
            f.measured(
                "memory.ram_gb_as_sold",
                "Installed memory, GB as sold",
                float(round(gib)),
                "GB",
                method,
                note="unified memory is sold in GiB labelled GB: 24 GiB is sold as '24 GB'",
            ),
        ]

    def _swap(self, ram_bytes: int, total_mib: float, used_mib: float, method: str) -> list[Figure]:
        f = self._ctx.figures
        used_bytes = used_mib * MIB
        return [
            f.measured(
                "memory.swap_total_gib", "Swap size", round(total_mib / 1024, 2), "GiB", method
            ),
            f.measured(
                "memory.swap_used_gib", "Swap in use", round(used_mib / 1024, 2), "GiB", method
            ),
            f.measured(
                "memory.swap_used_ratio",
                "Swap in use / installed memory",
                round(used_bytes / ram_bytes, 3) if ram_bytes else 0.0,
                "ratio",
                method,
            ),
        ]

    def _mac(self) -> list[Figure]:
        f = self._ctx.figures
        figures: list[Figure] = []
        ram_text = str(self._ctx.run(["sysctl", "-n", "hw.memsize"]).stdout).strip()
        ram_bytes = int(ram_text) if ram_text.isdigit() else 0
        if ram_bytes:
            figures.extend(self._ram(ram_bytes, "sysctl -n hw.memsize"))
        else:
            for fid, label, unit in (
                ("memory.ram_gib", "Installed memory", "GiB"),
                ("memory.ram_gb_as_sold", "Installed memory, GB as sold", "GB"),
            ):
                figures.append(f.skipped(fid, label, unit, "sysctl -n hw.memsize", "unreadable"))
        swap = self.parse_swapusage(str(self._ctx.run(["sysctl", "vm.swapusage"]).stdout))
        if swap and ram_bytes:
            figures.extend(self._swap(ram_bytes, swap[0], swap[1], "sysctl vm.swapusage"))
        else:
            figures.append(
                f.skipped(
                    "memory.swap_used_ratio",
                    "Swap in use / installed memory",
                    "ratio",
                    "sysctl vm.swapusage",
                    "swap usage or memory size unreadable",
                )
            )
        pressure = str(self._ctx.run(["memory_pressure", "-Q"]).stdout)
        free = re.search(r"free percentage:\s*(\d+)%", pressure)
        if free:
            figures.append(
                f.measured(
                    "memory.free_pct",
                    "System-wide memory free",
                    int(free.group(1)),
                    "%",
                    "memory_pressure -Q",
                )
            )
        else:
            figures.append(
                f.skipped(
                    "memory.free_pct",
                    "System-wide memory free",
                    "%",
                    "memory_pressure -Q",
                    "memory_pressure printed no free percentage",
                )
            )
        boot = self.parse_boottime(str(self._ctx.run(["sysctl", "-n", "kern.boottime"]).stdout))
        vm_stat = str(self._ctx.run(["vm_stat"]).stdout)
        stats = self.parse_vm_stat(vm_stat)
        hours = (self._ctx.wall() - boot) / 3600 if boot else 0
        page = re.search(r"page size of (\d+) bytes", vm_stat)
        if "swapouts" in stats and hours > 0 and page:
            figures.append(
                f.measured(
                    "memory.swapout_gb_per_hour",
                    "Swap-out volume per hour",
                    round(stats["swapouts"] * int(page.group(1)) / 1e9 / hours, 1),
                    "GB/h",
                    "vm_stat Swapouts x page size / hours since kern.boottime",
                    conditions={"hours_since_boot": round(hours, 1)},
                    note="pages swapped out times the page size; an upper bound on bytes written to swap if the swap files hold compressed pages (not verified)",
                )
            )
        else:
            figures.append(
                f.skipped(
                    "memory.swapout_gb_per_hour",
                    "Swap-out volume per hour",
                    "GB/h",
                    "vm_stat",
                    "no swapouts counter, page size or boot time",
                )
            )
        for key, fid, label in (
            ("compressions", "memory.compressions_per_hour", "Memory compressions per hour"),
            ("swapouts", "memory.swapouts_per_hour", "Swap-outs per hour"),
        ):
            if key in stats and hours > 0:
                figures.append(
                    f.measured(
                        fid,
                        label,
                        round(stats[key] / hours),
                        "pages/h",
                        "vm_stat counter / hours since kern.boottime",
                        conditions={"hours_since_boot": round(hours, 1)},
                    )
                )
            else:
                figures.append(
                    f.skipped(fid, label, "pages/h", "vm_stat", f"no {key} counter or boot time")
                )
        return figures

    def _linux(self) -> list[Figure]:
        f = self._ctx.figures
        figures: list[Figure] = []
        info = self.parse_meminfo(self._ctx.read("/proc/meminfo") or "")
        ram = info.get("MemTotal", 0)
        if ram:
            figures.extend(self._ram(ram, "read /proc/meminfo: MemTotal"))
            total = info.get("SwapTotal", 0) / MIB
            used = (info.get("SwapTotal", 0) - info.get("SwapFree", 0)) / MIB
            figures.extend(self._swap(ram, total, used, "read /proc/meminfo: SwapTotal - SwapFree"))
            if "MemAvailable" in info:
                figures.append(
                    f.measured(
                        "memory.free_pct",
                        "System-wide memory free",
                        round(info["MemAvailable"] / ram * 100),
                        "%",
                        "read /proc/meminfo: MemAvailable / MemTotal",
                    )
                )
        else:
            figures.append(
                f.skipped(
                    "memory.swap_used_ratio",
                    "Swap in use / installed memory",
                    "ratio",
                    "read /proc/meminfo",
                    "/proc/meminfo unreadable",
                )
            )
        psi_path = str(self._ctx.settings["memory"]["psi_path"])
        psi = self.parse_psi(self._ctx.read(psi_path) or "")
        for key, fid, label in (
            ("some", "memory.psi_some_avg300", "Memory pressure stall, some (avg300)"),
            ("full", "memory.psi_full_avg300", "Memory pressure stall, full (avg300)"),
        ):
            if key in psi:
                figures.append(f.measured(fid, label, psi[key], "%", f"read {psi_path}"))
            else:
                figures.append(
                    f.skipped(fid, label, "%", f"read {psi_path}", "no PSI (kernel without it)")
                )
        vmstat = dict(
            (k, int(v))
            for k, v in re.findall(r"^(\w+) (\d+)$", self._ctx.read("/proc/vmstat") or "", re.M)
        )
        if "oom_kill" in vmstat:
            figures.append(
                f.measured(
                    "memory.oom_kills",
                    "Out-of-memory kills since boot",
                    vmstat["oom_kill"],
                    "count",
                    "read /proc/vmstat: oom_kill",
                )
            )
        else:
            figures.append(
                f.skipped(
                    "memory.oom_kills",
                    "Out-of-memory kills since boot",
                    "count",
                    "read /proc/vmstat",
                    "no oom_kill counter",
                )
            )
        return figures


class ReliabilityProbe(ProbeInterface):
    """Panics, resets, shutdown stalls and memory kills, by report FILE NAME and date only,
    and the time since boot. Every event found is recorded with its date, so the history
    across weeks outlives the reports the OS prunes."""

    name = "reliability"
    _DATE = re.compile(r"(\d{4}-\d{2}-\d{2})-(\d{2})(\d{2})(\d{2})")

    def __init__(self, ctx: ProbeContext) -> None:
        self._ctx = ctx
        self._cfg = ctx.settings["reliability"]

    @classmethod
    def classify(cls, names: Iterable[str], kinds: Mapping[str, str]) -> list[dict[str, str]]:
        """Each report name that matches a kind, as {kind, at}; the host name and anything
        else in the name are dropped. De-duplicated (a report moved to Retired is one event)."""
        found: dict[tuple[str, str], dict[str, str]] = {}
        for name in names:
            for kind, pattern in kinds.items():
                if re.search(pattern, name):
                    stamp = cls._DATE.search(name)
                    if stamp is None:
                        continue
                    at = f"{stamp.group(1)}T{stamp.group(2)}:{stamp.group(3)}:{stamp.group(4)}"
                    found[(kind, at)] = {"kind": kind, "at": at}
                    break
        return sorted(found.values(), key=lambda e: (e["at"], e["kind"]))

    @staticmethod
    def fid(kind: str) -> str:
        """The figure id for a kind's count in the window (the panic driver's is plural)."""
        return (
            "reliability.kernel_panics_window"
            if kind == "kernel_panic"
            else f"reliability.{kind}_window"
        )

    @staticmethod
    def window(events: Sequence[Mapping[str, str]], kind: str, since: str) -> int:
        return sum(1 for e in events if e["kind"] == kind and e["at"] >= since)

    def run(self) -> list[Figure]:
        f = self._ctx.figures
        figures = [self._uptime()]
        days = int(self._cfg["window_days"])
        since = (datetime.fromtimestamp(self._ctx.wall(), UTC) - timedelta(days=days)).strftime(
            "%Y-%m-%dT%H:%M:%S"
        )
        kinds: Mapping[str, str] = self._cfg["kinds"]
        if self._ctx.mac:
            dirs = [str(d) for d in self._cfg["report_dirs"]]
            names, unreadable = self._names(dirs)
            method = "list report names in " + ", ".join(dirs)
            if unreadable == len(dirs):
                reason = "no report directory was readable"
                return figures + [
                    f.skipped(self.fid(k), k.replace("_", " "), "count", method, reason)
                    for k in kinds
                ]
            events = self.classify(names, kinds)
        else:
            pstore = str(self._cfg["pstore_dir"])
            method = f"list {pstore} (kernel crash records kept across reboots)"
            entries = self._ctx.glob(f"{pstore}/*")
            events = [
                {
                    "kind": "kernel_panic",
                    "at": datetime.fromtimestamp(p.stat().st_mtime, UTC).strftime(
                        "%Y-%m-%dT%H:%M:%S"
                    ),
                }
                for p in entries
                if p.name.startswith("dmesg-")
            ]
        figures.append(
            f.measured(
                "reliability.events",
                "Crash, panic and shutdown events found",
                events,
                "events",
                method,
                note="by report name and date only, the host's local time; reports are never opened",
            )
        )
        for kind in kinds:
            label = f"{kind.replace('_', ' ')} events in the last {days} days"
            fid = self.fid(kind)
            if self._ctx.mac or kind == "kernel_panic":
                figures.append(
                    f.measured(fid, label, self.window(events, kind, since), "count", method)
                )
            else:
                figures.append(
                    f.skipped(
                        fid,
                        label,
                        "count",
                        method,
                        "needs the system journal, which is not read without privileges",
                    )
                )
        return figures

    def _names(self, dirs: Sequence[str]) -> tuple[list[str], int]:
        names: list[str] = []
        unreadable = 0
        for directory in dirs:
            try:
                names.extend(os.listdir(self._ctx.path(directory)))
            except OSError:
                unreadable += 1
        return names, unreadable

    def _uptime(self) -> Figure:
        f = self._ctx.figures
        if self._ctx.mac:
            argv = ["sysctl", "-n", "kern.boottime"]
            boot = MemoryProbe.parse_boottime(str(self._ctx.run(argv).stdout))
            method = " ".join(argv)
        else:
            text = (self._ctx.read("/proc/uptime") or "").split()
            boot = self._ctx.wall() - float(text[0]) if text else None
            method = "read /proc/uptime"
        if boot is None:
            return f.skipped(
                "reliability.uptime_days", "Days since boot", "d", method, "unreadable"
            )
        return f.measured(
            "reliability.uptime_days",
            "Days since boot",
            round((self._ctx.wall() - boot) / 86400, 2),
            "d",
            method,
        )


@dataclass(frozen=True)
class ThroughputSample:
    at: str
    model: str
    prompt_tokens: int
    generated_tokens: int
    tok_s: float


class OllamaThroughputLog:
    """Every completed generation in the Ollama server log, with the model last loaded and
    the last time the log printed before it. Passive: it reads what was already served."""

    _TIME = re.compile(r"^time=(\S+)")
    _GIN = re.compile(r"^\[GIN\] (\d{4}/\d{2}/\d{2} - \d{2}:\d{2}:\d{2})")
    _MODEL = re.compile(r'\bmodel=(?:"?)([^\s"]+)')
    _PROMPT = re.compile(r"\|\s+prompt eval time =\s*[\d.]+ ms /\s*(\d+) tokens")
    _EVAL = re.compile(
        r"\|\s+eval time =\s*[\d.]+ ms /\s*(\d+) tokens \(.*?,\s*([\d.]+) tokens per second\)"
    )

    @classmethod
    def samples(
        cls, lines: Iterable[str], local_offset: Callable[[float], float] | None = None
    ) -> list[ThroughputSample]:
        out: list[ThroughputSample] = []
        at: str | None = None
        model = ""
        prompt = 0
        for line in lines:
            stamp = cls._TIME.match(line)
            if stamp:
                with contextlib.suppress(ValueError):
                    at = Stamp.iso(datetime.fromisoformat(stamp.group(1)))
                found = cls._MODEL.search(line)
                if found:
                    model = found.group(1).rsplit("/", 1)[-1]
                continue
            gin = cls._GIN.match(line)
            if gin:
                local = time.mktime(time.strptime(gin.group(1), "%Y/%m/%d - %H:%M:%S"))
                at = Stamp.iso(datetime.fromtimestamp(local, UTC))
                continue
            p = cls._PROMPT.search(line)
            if p:
                prompt = int(p.group(1))
                continue
            e = cls._EVAL.search(line)
            if e and at is not None:
                out.append(ThroughputSample(at, model, prompt, int(e.group(1)), float(e.group(2))))
        return out

    @staticmethod
    def weekly(
        samples: Sequence[ThroughputSample],
        model: str,
        band: tuple[int, int],
        min_generated: int,
        min_per_week: int,
    ) -> list[dict[str, Any]]:
        weeks: dict[str, list[float]] = {}
        for s in samples:
            if s.model != model or s.generated_tokens < min_generated:
                continue
            if not band[0] <= s.prompt_tokens < band[1]:
                continue
            weeks.setdefault(Stamp.week_of(Stamp.parse(s.at)), []).append(s.tok_s)
        return [
            {"week": week, "median_tok_s": round(median(rates), 2), "n": len(rates)}
            for week, rates in sorted(weeks.items())
            if len(rates) >= min_per_week
        ]


class ThroughputProbe(ProbeInterface):
    """The sovereign model's generation rate per week, from the server log's history."""

    name = "throughput"

    def __init__(self, ctx: ProbeContext, model: str) -> None:
        self._ctx = ctx
        self._cfg = ctx.settings["throughput"]
        self._model = model

    def run(self) -> list[Figure]:
        f = self._ctx.figures
        pattern = str(self._cfg["log_glob"])
        method = f"mine {pattern} (passive; no request is made)"
        files = sorted(self._ctx.glob(pattern), key=lambda p: p.stat().st_mtime)
        if not files:
            reason = f"no Ollama server log matches {pattern}"
            return [
                f.skipped(
                    "throughput.weekly", "Generation rate by week", "tokens/s", method, reason
                ),
                f.skipped(
                    "throughput.gen_tok_s_week_median",
                    "Generation rate, newest week's median",
                    "tokens/s",
                    method,
                    reason,
                ),
            ]
        samples: list[ThroughputSample] = []
        for path in files:
            with path.open(encoding="utf-8", errors="replace") as handle:
                samples.extend(OllamaThroughputLog.samples(handle))
        band = (int(self._cfg["band_min_tokens"]), int(self._cfg["band_max_tokens"]))
        weekly = OllamaThroughputLog.weekly(
            samples,
            self._model,
            band,
            int(self._cfg["min_generated_tokens"]),
            int(self._cfg["min_samples_per_week"]),
        )
        conditions = {
            "model": self._model,
            "prompt_band_tokens": list(band),
            "files": len(files),
            "samples_all_models": len(samples),
            "first_sample": samples[0].at if samples else None,
            "last_sample": samples[-1].at if samples else None,
        }
        figures = [
            f.measured(
                "throughput.weekly",
                "Generation rate by week",
                weekly,
                "tokens/s",
                method,
                conditions=conditions,
            )
        ]
        if weekly:
            newest = weekly[-1]
            figures.append(
                f.measured(
                    "throughput.gen_tok_s_week_median",
                    "Generation rate, newest week's median",
                    newest["median_tok_s"],
                    "tokens/s",
                    method,
                    conditions={**conditions, "week": newest["week"], "n": newest["n"]},
                )
            )
        else:
            figures.append(
                f.skipped(
                    "throughput.gen_tok_s_week_median",
                    "Generation rate, newest week's median",
                    "tokens/s",
                    method,
                    f"no week had {self._cfg['min_samples_per_week']} comparable {self._model}"
                    f" requests (prompts {band[0]}-{band[1]} tokens)",
                )
            )
        return figures


class MicroBenchmark(ProbeInterface):
    """A small CPU and disk benchmark, only on a quiet host (minimum_specs' IdleGate)."""

    name = "microbench"

    def __init__(
        self,
        ctx: ProbeContext,
        gate: Any,
        hasher: Callable[[int, int], float] | None = None,
        writer: Callable[[int, int], float] | None = None,
    ) -> None:
        self._ctx = ctx
        self._cfg = ctx.settings["microbench"]
        self._gate = gate
        self._hasher = hasher or self.sha256_mib_s
        self._writer = writer or self.fsync_write_mib_s

    @staticmethod
    def sha256_mib_s(mib: int, repeats: int) -> float:
        block = b"\xa5" * MIB
        best = 0.0
        for _ in range(repeats):
            digest = hashlib.sha256()
            started = time.perf_counter()
            for _ in range(mib):
                digest.update(block)
            best = max(best, mib / max(time.perf_counter() - started, 1e-9))
        return round(best, 1)

    @staticmethod
    def fsync_write_mib_s(mib: int, repeats: int) -> float:
        block = os.urandom(MIB)
        best = 0.0
        for _ in range(repeats):
            handle, name = tempfile.mkstemp(prefix="vibey-host-health-")
            try:
                started = time.perf_counter()
                for _ in range(mib):
                    os.write(handle, block)
                # On macOS fsync() leaves the data in the drive's cache; F_FULLFSYNC flushes it.
                full = getattr(fcntl, "F_FULLFSYNC", None)
                if full is None:
                    os.fsync(handle)
                else:
                    fcntl.fcntl(handle, full)
                best = max(best, mib / max(time.perf_counter() - started, 1e-9))
            finally:
                os.close(handle)
                os.unlink(name)
        return round(best, 1)

    def run(self) -> list[Figure]:
        f = self._ctx.figures
        cpu_mib, disk_mib, repeats = (
            int(self._cfg["cpu_mib"]),
            int(self._cfg["disk_mib"]),
            int(self._cfg["repeats"]),
        )
        ids = (
            ("micro.cpu_sha256_mib_s", "CPU: SHA-256 throughput, one core", "MiB/s"),
            ("micro.disk_fsync_write_mib_s", "Disk: fsynced sequential write", "MiB/s"),
        )
        idle, reason, conditions = self._gate.wait()
        if not idle:
            return [f.skipped(fid, label, unit, "idle-gated", reason) for fid, label, unit in ids]
        return [
            f.measured(
                ids[0][0],
                ids[0][1],
                self._hasher(cpu_mib, repeats),
                "MiB/s",
                f"best of {repeats}: SHA-256 over {cpu_mib} MiB in memory",
                conditions=conditions,
            ),
            f.measured(
                ids[1][0],
                ids[1][1],
                self._writer(disk_mib, repeats),
                "MiB/s",
                f"best of {repeats}: {disk_mib} MiB written and flushed to the drive (F_FULLFSYNC on macOS, fsync elsewhere), scratch file removed",
                conditions=conditions,
            ),
        ]


class PlatformProbe(ProbeInterface):
    """The OS and its vendor support horizon, and the hardware's support status, from the
    declared table -- with its source and the date it was last verified."""

    name = "platform"

    def __init__(self, ctx: ProbeContext, host: Mapping[str, Any]) -> None:
        self._ctx = ctx
        self._cfg = ctx.settings["platform"]
        self._host = host

    @staticmethod
    def os_key(system: str, os_release: str) -> tuple[str, str]:
        """(table key, display name)."""
        if system == "Darwin":
            return "macos", "macOS"
        found = dict(re.findall(r'^(\w+)="?([^"\n]*)"?$', os_release, re.M))
        distro, version = found.get("ID", ""), found.get("VERSION_ID", "")
        key = f"{distro}-{version}" if distro == "ubuntu" else distro
        return key, found.get("PRETTY_NAME", key)

    def run(self) -> list[Figure]:
        f = self._ctx.figures
        release = "" if self._ctx.mac else (self._ctx.read("/etc/os-release") or "")
        key, name = self.os_key(self._ctx.system, release)
        os_label = str(self._host.get("os") or name)
        figures = [
            f.measured(
                "platform.os",
                "Operating system",
                os_label,
                "text",
                "sw_vers" if self._ctx.mac else "read /etc/os-release",
                conditions={"os_key": key},
            )
        ]
        entry = self._cfg["os"].get(key)
        method = "[host_health.platform.os] in scripts/host_health.toml"
        if entry is None:
            figures.append(
                f.skipped(
                    "platform.os_support_end",
                    "OS vendor support ends",
                    "date",
                    method,
                    f"no support entry is declared for {key!r}",
                )
            )
        elif entry["support_end"]:
            figures.append(
                self._declared(
                    "platform.os_support_end",
                    "OS vendor support ends",
                    entry["support_end"],
                    entry,
                    method,
                )
            )
        else:
            figures.append(
                f.skipped(
                    "platform.os_support_end",
                    "OS vendor support ends",
                    "date",
                    method,
                    f"{entry['reason']} (source {entry['source']}, verified {entry['last_verified']})",
                )
            )
        figures.append(self._hardware())
        return figures

    def _declared(
        self, fid: str, label: str, value: str, entry: Mapping[str, Any], method: str
    ) -> Figure:
        figure = self._ctx.figures.declared(fid, label, value, "date", method, str(entry["source"]))
        return replace(figure, note=f"{entry['reason']}; last verified {entry['last_verified']}")

    def _hardware(self) -> Figure:
        f = self._ctx.figures
        model = str(self._host.get("model") or "")
        label = "Hardware obsolete under the vendor's policy"
        method = "[host_health.platform.hardware] in scripts/host_health.toml"
        entry = self._cfg["hardware"].get(model)
        if entry is None:
            return f.skipped(
                "platform.hardware_obsolete_on",
                label,
                "date",
                method,
                f"no hardware support entry is declared for model {model or 'unknown'!r}",
            )
        if not entry["last_sold"]:
            return f.skipped(
                "platform.hardware_obsolete_on",
                label,
                "date",
                method,
                f"{entry['reason']} (policy: obsolete {entry['obsolete_after_years']} years after"
                f" the last sale; source {entry['source']}, verified {entry['last_verified']})",
            )
        sold = date.fromisoformat(str(entry["last_sold"]))
        years = int(entry["obsolete_after_years"])
        try:
            obsolete = sold.replace(year=sold.year + years)
        except ValueError:  # 29 February
            obsolete = sold.replace(year=sold.year + years, day=28)
        return self._declared(
            "platform.hardware_obsolete_on", label, obsolete.isoformat(), entry, method
        )


class CapacityProbe(ProbeInterface):
    """This machine against vibey's own requirements, read from the minimum-specs record and
    copied in with their dates, so a record names the requirement it was held against."""

    name = "capacity"
    REQUIREMENTS = (
        ("ram.minimum_gb", "capacity.ram_minimum_gb", "vibey's minimum memory"),
        ("ram.recommended_gb", "capacity.ram_recommended_gb", "vibey's recommended memory"),
        ("disk.minimum_gb", "capacity.disk_minimum_gb", "vibey's minimum free disk"),
        ("disk.recommended_gb", "capacity.disk_recommended_gb", "vibey's recommended free disk"),
    )

    def __init__(self, ctx: ProbeContext, specs: SpecsRecord | None, specs_path: str) -> None:
        self._ctx = ctx
        self._specs = specs
        self._path = specs_path

    def run(self) -> list[Figure]:
        f = self._ctx.figures
        out: list[Figure] = []
        by_id = self._specs.by_id() if self._specs else {}
        for source_id, fid, label in self.REQUIREMENTS:
            figure = by_id.get(source_id)
            method = f"read {self._path}: {source_id}"
            if figure is None or not figure.has_value:
                reason = (
                    f"{self._path} is unreadable"
                    if self._specs is None
                    else f"{source_id} has no value there"
                )
                out.append(f.skipped(fid, label, "GB", method, reason))
                continue
            declared = f.declared(fid, label, figure.value, figure.unit, method, self._path)
            out.append(
                replace(
                    declared,
                    measured_at=figure.measured_at or declared.measured_at,
                    note=f"{figure.status} in the minimum-specs record",
                )
            )
        return out


# ------------------------------------------------------------------------ the record


@dataclass(frozen=True)
class HealthRecord:
    """One weekly run on one host: its figures and the forecast as of that run."""

    run_id: str
    measured_at: str
    host: Mapping[str, Any]
    figures: tuple[Figure, ...]
    forecast: Mapping[str, Any] = field(default_factory=dict)
    schema: str = SCHEMA

    @property
    def fingerprint(self) -> str:
        return str(self.host["fingerprint"])

    def by_id(self) -> dict[str, Figure]:
        return {f.id: f for f in self.figures}

    def to_line(self) -> str:
        body = {
            "schema": self.schema,
            "run_id": self.run_id,
            "measured_at": self.measured_at,
            "generated_by": SCRIPT,
            "host": dict(sorted(self.host.items())),
            "figures": [f.to_dict() for f in sorted(self.figures, key=lambda f: f.id)],
            "forecast": dict(self.forecast),
        }
        return json.dumps(body, ensure_ascii=False, separators=(",", ":"), default=str)

    @classmethod
    def from_line(cls, text: str) -> HealthRecord:
        raw = json.loads(text)
        if raw.get("schema") != SCHEMA:
            raise ValueError(f"record schema {raw.get('schema')!r} is not {SCHEMA}")
        if "fingerprint" not in raw.get("host", {}):
            raise ValueError("a record names its host's fingerprint")
        return cls(
            run_id=raw["run_id"],
            measured_at=raw["measured_at"],
            host=raw["host"],
            figures=tuple(Figure.from_dict(f) for f in raw["figures"]),
            forecast=raw.get("forecast", {}),
        )


class HealthLedger(HealthLedgerInterface):
    """The JSON-lines record. Appending is the only write; merging adds the lines another
    copy has that this one lacks, by run id, and never changes a line already there."""

    def __init__(self, path: Path) -> None:
        self.path = path

    @staticmethod
    def parse(text: str, where: str = "record") -> list[HealthRecord]:
        records: list[HealthRecord] = []
        seen: set[str] = set()
        for number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                record = HealthRecord.from_line(line)
            except (ValueError, KeyError, TypeError) as exc:
                raise ValueError(f"{where}:{number}: {exc}") from exc
            if record.run_id in seen:
                raise ValueError(f"{where}:{number}: run id {record.run_id} appears twice")
            seen.add(record.run_id)
            records.append(record)
        return records

    def text(self) -> str:
        return self.path.read_text(encoding="utf-8") if self.path.exists() else ""

    def read(self) -> list[HealthRecord]:
        return self.parse(self.text(), str(self.path))

    def append(self, record: HealthRecord) -> bool:
        if any(r.run_id == record.run_id for r in self.read()):
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        existing = self.text()
        with self.path.open("a", encoding="utf-8") as handle:
            if existing and not existing.endswith("\n"):
                handle.write("\n")
            handle.write(record.to_line() + "\n")
        return True

    def merge(self, records: Sequence[HealthRecord]) -> int:
        """Append every record not already here, oldest first. Returns how many."""
        known = {r.run_id for r in self.read()}
        added = 0
        for record in sorted(records, key=lambda r: r.measured_at):
            if record.run_id not in known:
                self.append(record)
                known.add(record.run_id)
                added += 1
        return added

    @staticmethod
    def append_only(before: str, after: str) -> str | None:
        """None when `after` keeps every line of `before`, in place; else what changed."""
        old = [line for line in before.splitlines() if line.strip()]
        new = [line for line in after.splitlines() if line.strip()]
        for index, line in enumerate(old):
            if index >= len(new):
                return f"line {index + 1} was removed"
            if new[index] != line:
                return f"line {index + 1} was rewritten"
        return None

    @staticmethod
    def by_host(records: Sequence[HealthRecord]) -> dict[str, list[HealthRecord]]:
        hosts: dict[str, list[HealthRecord]] = {}
        for record in sorted(records, key=lambda r: r.measured_at):
            hosts.setdefault(record.fingerprint, []).append(record)
        return hosts


# ------------------------------------------------------------------------ the forecast


class Thresholds:
    """Where a driver's threshold comes from: a literal, a figure in the minimum-specs record,
    a key in its configuration, or a figure in the host's own newest record."""

    def __init__(self, specs: SpecsRecord | None, specs_config: Mapping[str, Any]) -> None:
        self._specs = specs.by_id() if specs else {}
        self._config = specs_config

    def resolve(self, driver: Mapping[str, Any], newest: HealthRecord) -> tuple[float | None, str]:
        """(threshold, where it came from) -- or (None, why there is none)."""
        if "threshold" in driver:
            return float(driver["threshold"]), "declared in scripts/host_health.toml"
        if "threshold_figure" in driver:
            figure = self._specs.get(str(driver["threshold_figure"]))
            if figure is None or not figure.has_value:
                return (
                    None,
                    f"{driver['threshold_figure']} has no value in the minimum-specs record",
                )
            stamp = (figure.measured_at or "")[:10]
            return float(figure.value), (
                f"minimum-specs record {driver['threshold_figure']} ({figure.status}, {stamp})"
            )
        if "threshold_config" in driver:
            node: Any = self._config
            path = str(driver["threshold_config"])
            for part in path.split("."):
                if not isinstance(node, Mapping) or part not in node:
                    return None, f"{path} is not in the minimum-specs configuration"
                node = node[part]
            return float(node), f"scripts/minimum_specs.toml {path}"
        local = str(driver.get("threshold_figure_local", ""))
        figure = newest.by_id().get(local)
        if figure is not None and not figure.has_value and figure.reason:
            return None, f"{local}: {figure.reason}"
        if figure is None or not figure.has_value:
            return None, f"{local or 'no threshold'} is not measured on this host"
        return float(figure.value), f"this host's {local} ({(figure.measured_at or '')[:10]})"


class Forecaster(ForecasterInterface):
    """Each driver's state and dates from one host's history; the machine's replacement is
    the earliest driver's, and its interval the earliest bounds across the drivers."""

    def __init__(self, settings: HealthSettings, thresholds: Thresholds) -> None:
        self._settings = settings
        self._cfg = settings["forecast"]
        self._thresholds = thresholds
        self._estimator = TheilSenEstimator(float(self._cfg["confidence"]))
        self._projector = ThresholdProjector()

    def series(
        self, history: Sequence[HealthRecord], driver: Mapping[str, Any]
    ) -> list[tuple[float, float, str]]:
        """(days, value, when) points inside the lookback, oldest first."""
        newest = Stamp.days(history[-1].measured_at)
        lookback = float(self._cfg["lookback_days"])
        points: dict[str, tuple[float, float, str]] = {}
        series_id = driver.get("series_figure")
        for record in history:
            figure = record.by_id().get(str(series_id or driver["figure"]))
            if figure is None or not figure.has_value:
                continue
            if series_id:
                for week in figure.value:
                    at = f"{week['week']}T12:00:00Z"
                    points[week["week"]] = (
                        Stamp.days(at) + 3,
                        float(week["median_tok_s"]),
                        at,
                    )
            elif isinstance(figure.value, (int, float)) and not isinstance(figure.value, bool):
                points[record.run_id] = (
                    Stamp.days(record.measured_at),
                    float(figure.value),
                    record.measured_at,
                )
        return sorted(p for p in points.values() if newest - p[0] <= lookback)

    def driver(self, key: str, history: Sequence[HealthRecord]) -> dict[str, Any]:
        result = self._driver(key, history)
        fallback = self._settings.drivers[key].get("fallback")
        if result["state"] == "unknown" and fallback:
            label = self._settings.drivers[str(fallback)]["label"]
            result["reason"] = f"{result['reason']}; the forecast rests on {label} instead"
            result["fallback"] = fallback
        return result

    def _driver(self, key: str, history: Sequence[HealthRecord]) -> dict[str, Any]:
        spec = self._settings.drivers[key]
        newest = history[-1]
        out: dict[str, Any] = {
            "id": key,
            "label": spec["label"],
            "kind": spec["kind"],
            "figure": spec["figure"],
            "expected": list(spec.get("expected", [])),
        }
        latest = newest.by_id().get(str(spec["figure"]))
        if spec["kind"] == "dated":
            return {**out, **self._dated(latest, newest)}
        points = self.series(history, spec)
        if not points:
            reason = latest.reason if latest is not None and latest.reason else "not measured"
            return {**out, "state": "unknown", "reason": reason, "points": 0}
        threshold, source = self._thresholds.resolve(spec, newest)
        value = points[-1][1]
        out.update(value=value, unit=latest.unit if latest else "", points=len(points))
        if threshold is None:
            return {**out, "state": "unknown", "reason": f"threshold unavailable: {source}"}
        direction = str(spec["direction"])
        out.update(threshold=threshold, threshold_source=source, direction=direction)
        if spec.get("recommended_figure"):
            rec, rec_source = self._thresholds.resolve(
                {"threshold_figure": spec["recommended_figure"]}, newest
            )
            if rec is not None:
                out.update(recommended=rec, recommended_source=rec_source)

        strict = bool(spec.get("strict", False))

        def past(v: float) -> bool:
            if direction == "rising":
                return v > threshold if strict else v >= threshold
            return v < threshold if strict else v <= threshold

        if spec["kind"] == "level":
            confirm = int(spec.get("confirm", 1))
            run = 0
            for _, v, _ in reversed(points):
                if not past(v):
                    break
                run += 1
            if run >= confirm:
                return {**out, "state": "exceeded", "date": points[-1][2][:10]}
            if run:
                return {
                    **out,
                    "state": "unconfirmed",
                    "reason": f"past the threshold in {run} of the {confirm} records that confirm it",
                }
            return {**out, "state": "within"}
        if past(value):
            return {**out, "state": "exceeded", "date": points[-1][2][:10]}
        if len(points) < int(self._cfg["min_points"]):
            return {
                **out,
                "state": "insufficient-history",
                "reason": f"{len(points)} of the {self._cfg['min_points']} weekly points a trend needs",
            }
        fit = self._estimator.fit([p[0] for p in points], [p[1] for p in points])
        crossing = self._projector.crossing(fit, threshold, direction)
        out.update(
            method=f"Theil-Sen, {fit.confidence:.0%} interval on the slope",
            slope_per_week=round(fit.slope * 7, 6),
        )
        if not crossing.approaching or crossing.central is None:
            return {**out, "state": "not-approaching"}
        last = points[-1][0]
        earliest = max(crossing.earliest if crossing.earliest is not None else last, last)
        return {
            **out,
            "state": "projected",
            "date": Stamp.day_of(max(crossing.central, last)),
            "earliest": Stamp.day_of(earliest),
            "latest": Stamp.day_of(crossing.latest) if crossing.latest is not None else None,
        }

    @staticmethod
    def _dated(latest: Figure | None, newest: HealthRecord) -> dict[str, Any]:
        if latest is None or not latest.has_value:
            reason = latest.reason if latest is not None and latest.reason else "not declared"
            return {"state": "unknown", "reason": reason, "points": 0}
        when = str(latest.value)
        state = "exceeded" if when <= newest.measured_at[:10] else "dated"
        return {
            "state": state,
            "date": when,
            "value": when,
            "unit": "date",
            "threshold_source": latest.source or "",
            "points": 1,
        }

    def hypotheses(self, drivers: Sequence[Mapping[str, Any]], newest: HealthRecord) -> list[str]:
        """The declared hypotheses whose drivers are past or nearing their threshold and
        whose figures were all measured, with the values filled in. Offered, never concluded."""
        states = {d["id"]: d["state"] for d in drivers}
        figures = newest.by_id()
        out: list[str] = []
        for spec in self._settings.table.get("hypotheses", {}).values():
            if not any(states.get(d) in ("exceeded", "unconfirmed") for d in spec["drivers"]):
                continue
            values = {fid: figures.get(fid) for fid in spec["figures"]}
            if any(v is None or not v.has_value for v in values.values()):
                continue
            text = str(spec["text"])
            for fid, figure in values.items():
                text = text.replace("{" + fid + "}", f"{figure.value:g}")  # type: ignore[union-attr]
            out.append(text)
        return out

    def forecast(self, history: Sequence[HealthRecord]) -> dict[str, Any]:
        newest = history[-1]
        drivers = [self.driver(key, history) for key in self._settings.drivers]
        dated = [d for d in drivers if d["state"] in ("exceeded", "projected", "dated")]
        result: dict[str, Any] = {
            "as_of": newest.measured_at,
            "host": newest.fingerprint,
            "records": len(history),
            "drivers": drivers,
            "hypotheses": self.hypotheses(drivers, newest),
        }
        if not dated:
            result.update(binding=None, replace_by=None, earliest=None, latest=None, warning=False)
            return result
        binding = min(dated, key=lambda d: d["date"])
        earliest = min(d.get("earliest") or d["date"] for d in dated)
        # The machine goes at its first driver, so its latest bound is the smallest finite
        # latest across the drivers; a projected driver whose interval cannot rule out
        # "never" contributes no bound, and none at all leaves the interval open.
        bounds = [d["latest"] if d["state"] == "projected" else d["date"] for d in dated]
        finite = [b for b in bounds if b is not None]
        latest = min(finite) if finite else None
        horizon = (
            Stamp.parse(newest.measured_at).date()
            + timedelta(days=int(self._cfg["warn_within_days"]))
        ).isoformat()
        result.update(
            binding=binding["id"],
            replace_by=binding["date"],
            earliest=earliest,
            latest=latest,
            warning=binding["date"] <= horizon,
        )
        return result


# ------------------------------------------------------------------------ rendering


class HealthBlocks:
    """`<!-- BEGIN GENERATED health:NAME — regenerated by scripts/host_health.py -->`.

    minimum_specs' GeneratedBlocks is fixed to its own script's name in the marker, so it
    cannot read or write these; the convention is the same.
    """

    PATTERN = re.compile(
        r"<!-- BEGIN GENERATED health:(?P<name>[a-z0-9-]+) — regenerated by "
        + re.escape(SCRIPT)
        + r" -->\n(?P<body>.*?)<!-- END GENERATED health:(?P=name) -->",
        re.DOTALL,
    )

    @classmethod
    def wrap(cls, name: str, body: str) -> str:
        return (
            f"<!-- BEGIN GENERATED health:{name} — regenerated by {SCRIPT} -->\n"
            f"{body.rstrip()}\n<!-- END GENERATED health:{name} -->"
        )

    @classmethod
    def replace_all(cls, document: str, blocks: Mapping[str, str]) -> str:
        return cls.PATTERN.sub(
            lambda m: cls.wrap(m["name"], blocks[m["name"]]) if m["name"] in blocks else m.group(0),
            document,
        )

    @classmethod
    def drift(cls, document: str, blocks: Mapping[str, str]) -> list[str]:
        present = {m["name"]: m["body"] for m in cls.PATTERN.finditer(document)}
        return sorted(
            name
            for name, body in blocks.items()
            if name not in present or present[name].rstrip() != body.rstrip()
        )


class HealthRenderer(HealthRendererInterface):
    """The page's tables: the newest record of each host, and its forecast computed from the
    whole committed history with the current configuration."""

    def __init__(self, forecaster: Forecaster) -> None:
        self._forecaster = forecaster

    @staticmethod
    def _cell(text: Any) -> str:
        return str(text).replace("|", "\\|").replace("\n", " ")

    @staticmethod
    def value(figure: Figure) -> str:
        v = figure.value
        if figure.id == "reliability.events":
            return f"{len(v)} event(s)" if v else "none"
        if figure.id == "throughput.weekly":
            return f"{len(v)} week(s) of medians" if v else "no qualifying week"
        if isinstance(v, bool):
            return "yes" if v else "no"
        if figure.unit in ("text", "verdict", "date"):
            return str(v)
        if isinstance(v, (int, float)):
            number = f"{v:,.0f}" if abs(v) >= 100_000 else f"{v:g}"
            return f"{number} {figure.unit}"
        return str(v)

    def _host(self, history: Sequence[HealthRecord]) -> str:
        host = history[-1].host
        ram = host.get("ram_bytes")
        parts = [
            str(host.get("model") or host.get("arch") or "unknown"),
            str(host.get("chip") or "unknown chip"),
            f"{round(ram / GIB)} GiB" if ram else "unknown memory",
            str(host.get("os") or host.get("system") or "unknown OS"),
        ]
        return (
            f"**Host `{history[-1].fingerprint}`** ({' · '.join(parts)}): "
            f"{len(history)} weekly record(s), {history[0].measured_at[:10]} to "
            f"{history[-1].measured_at[:10]}."
        )

    def _latest(self, history: Sequence[HealthRecord]) -> str:
        rows = ["| Figure | Value | Status | How |", "|---|---|---|---|"]
        for figure in sorted(history[-1].figures, key=lambda f: f.id):
            if figure.status == "skipped":
                value, how = "—", f"skipped: {figure.reason}"
            else:
                value, how = self.value(figure), figure.method
                if figure.source:
                    how = f"{how} (source: {figure.source})"
            rows.append(
                f"| {self._cell(figure.label)} | {self._cell(value)} | {figure.status} "
                f"| {self._cell(how)} |"
            )
        return "\n".join(rows)

    def _forecast(self, history: Sequence[HealthRecord]) -> str:
        fc = self._forecaster.forecast(history)
        rows = [
            "| Driver | Latest | Threshold | State | Date (interval) | Points |",
            "|---|---|---|---|---|---|",
        ]
        for d in fc["drivers"]:
            latest = (
                f"{d['value']:g} {d.get('unit', '')}".strip()
                if isinstance(d.get("value"), (int, float))
                else str(d.get("value", "—"))
            )
            threshold = (
                f"{d['threshold']:g} ({d['threshold_source']})"
                if "threshold" in d
                else d.get("threshold_source", "—") or "—"
            )
            if d["state"] == "projected":
                when = f"{d['date']} ({d['earliest']} to {d['latest'] or 'not bounded'})"
            elif "date" in d:
                when = d["date"]
            else:
                when = d.get("reason", "—")
            rows.append(
                f"| {self._cell(d['label'])} | {self._cell(latest)} | {self._cell(threshold)} "
                f"| {d['state']} | {self._cell(when)} | {d.get('points', 0)} |"
            )
        if fc["binding"]:
            label = next(d["label"] for d in fc["drivers"] if d["id"] == fc["binding"])
            verdict = (
                f"**Replacement by {fc['replace_by']}** (interval {fc['earliest']} to "
                f"{fc['latest'] or 'not bounded'}), bound by *{label}*"
                + (" — within the warning horizon." if fc["warning"] else ".")
            )
        else:
            verdict = (
                "**No driver projects a replacement date yet.** Trend drivers need "
                f"{self._forecaster._cfg['min_points']} weekly points; dated drivers need a "
                "vendor date. Each driver's reason is in the table below."
            )
        notes = "".join(f"\n\n> {h}" for h in fc["hypotheses"])
        return f"{verdict} As of {fc['as_of'][:10]}.{notes}\n\n" + "\n".join(rows)

    def blocks(self, records: Sequence[HealthRecord]) -> dict[str, str]:
        hosts = HealthLedger.by_host(records)
        if not hosts:
            empty = "No host has recorded its health yet."
            return {"hosts": empty, "latest": empty, "forecast": empty}
        return {
            "hosts": "\n\n".join(self._host(h) for h in hosts.values()),
            "latest": "\n\n".join(f"{self._host(h)}\n\n{self._latest(h)}" for h in hosts.values()),
            "forecast": "\n\n".join(
                f"{self._host(h)}\n\n{self._forecast(h)}" for h in hosts.values()
            ),
        }

    def apply(self, document: str, records: Sequence[HealthRecord]) -> str:
        return HealthBlocks.replace_all(document, self.blocks(records))

    def drift(self, document: str, records: Sequence[HealthRecord]) -> list[str]:
        return HealthBlocks.drift(document, self.blocks(records))


# ------------------------------------------------------------------------ conditions


class ConditionEvaluator(ConditionEvaluatorInterface):
    """The one tracking issue's conditions: a host gone quiet, an expected probe missing
    from its last records, or a driver past or near its threshold."""

    def __init__(self, settings: HealthSettings, forecaster: Forecaster) -> None:
        self._settings = settings
        self._cfg = settings["conditions"]
        self._forecaster = forecaster

    def evaluate(self, records: Sequence[HealthRecord], now: str) -> dict[str, Any]:
        conditions: list[str] = []
        stale_after = int(self._cfg["stale_after_days"])
        needed = int(self._cfg["missing_records"])
        for fingerprint, history in HealthLedger.by_host(records).items():
            newest = history[-1]
            age = Stamp.days(now) - Stamp.days(newest.measured_at)
            if age > stale_after:
                conditions.append(
                    f"Host `{fingerprint}` has not recorded its health for {age:.0f} days"
                    f" (newest record {newest.measured_at[:10]}; the weekly unit should run"
                    f" every 7) -- is `{self._settings['schedule']['label']}` loaded?"
                )
            system = str(newest.host.get("system", ""))
            recent = history[-needed:]
            if len(recent) >= needed:
                for spec in self._settings.drivers.values():
                    if system not in spec.get("expected", []):
                        continue
                    figures = [r.by_id().get(str(spec["figure"])) for r in recent]
                    if all(f is None or not f.has_value for f in figures):
                        last = figures[-1]
                        if spec["kind"] == "dated" and last is not None:
                            continue  # a vendor that publishes no date is not a missing probe
                        why = last.reason if last is not None and last.reason else "not recorded"
                        conditions.append(
                            f"{spec['label']} (`{spec['figure']}`) was not measured on host"
                            f" `{fingerprint}` in its last {needed} records: {why}"
                        )
            fc = self._forecaster.forecast(history)
            for d in fc["drivers"]:
                if d["state"] == "exceeded":
                    conditions.append(
                        f"{d['label']} on host `{fingerprint}` is past its threshold"
                        f" ({d.get('value')} against {d.get('threshold', d.get('date'))};"
                        f" {d.get('threshold_source', '')})"
                    )
            if fc["warning"] and fc["binding"]:
                conditions.append(
                    f"Host `{fingerprint}` is predicted to need replacing by {fc['replace_by']}"
                    f" (interval {fc['earliest']} to {fc['latest'] or 'not bounded'}), bound by"
                    f" `{fc['binding']}`"
                )
        body = "\n".join(f"- {c}" for c in conditions)
        if conditions:
            body = (
                "The weekly host-health record (`docs/architecture/evidence/host-health.jsonl`,"
                " `scripts/host_health.py`) shows:\n\n"
                + body
                + "\n\nThis issue updates itself every week and closes when no condition holds."
                " The page: docs/reference/host-health.md."
            )
        return {
            "raise": bool(conditions),
            "key": self._cfg["key"],
            "title": self._cfg["title"],
            "body": body,
            "conditions": conditions,
        }


# ------------------------------------------------------------------------ the host's unit


class SchedulerRenderer(SchedulerRendererInterface):
    """A weekly calendar unit for the host's own service manager. vibey's TimerUnitRenderer
    (src/vibey/infrastructure/driver/timer_units.py) renders interval timers and supervised
    services, not calendar ones, and this script stays stdlib-only so the unit can run it
    under `uv run --no-project`; the gap is a calendar trigger, written here."""

    _DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")

    def __init__(self, schedule: Mapping[str, Any]) -> None:
        self._s = schedule
        weekday = int(schedule["weekday"])
        if not 1 <= weekday <= 7:
            raise ValueError(f"[host_health.schedule] weekday is ISO 1-7, not {weekday}")

    def launchd(self, argv: Sequence[str], workdir: str, log: str, path_env: str) -> str:
        args = "\n".join(f"    <string>{escape(part)}</string>" for part in argv)
        weekday = int(self._s["weekday"]) % 7  # launchd: 0 and 7 are Sunday, 1 is Monday
        return (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
            '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            f"<!-- Rendered by `{SCRIPT} install` from [host_health.schedule] in"
            " scripts/host_health.toml. Edit the table and render again. -->\n"
            '<plist version="1.0">\n<dict>\n'
            f"  <key>Label</key>\n  <string>{escape(str(self._s['label']))}</string>\n"
            f"  <key>ProgramArguments</key>\n  <array>\n{args}\n  </array>\n"
            f"  <key>WorkingDirectory</key>\n  <string>{escape(workdir)}</string>\n"
            "  <key>EnvironmentVariables</key>\n  <dict>\n"
            f"    <key>PATH</key>\n    <string>{escape(path_env)}</string>\n  </dict>\n"
            "  <key>StartCalendarInterval</key>\n  <dict>\n"
            f"    <key>Weekday</key>\n    <integer>{weekday}</integer>\n"
            f"    <key>Hour</key>\n    <integer>{int(self._s['hour'])}</integer>\n"
            f"    <key>Minute</key>\n    <integer>{int(self._s['minute'])}</integer>\n"
            "  </dict>\n"
            "  <key>LowPriorityIO</key>\n  <true/>\n"
            "  <key>Nice</key>\n  <integer>10</integer>\n"
            f"  <key>StandardOutPath</key>\n  <string>{escape(log)}</string>\n"
            f"  <key>StandardErrorPath</key>\n  <string>{escape(log)}</string>\n"
            "</dict>\n</plist>\n"
        )

    def systemd(
        self, argv: Sequence[str], workdir: str, log: str, path_env: str
    ) -> tuple[str, str]:
        exec_start = " ".join(self._quote(part) for part in argv)
        day = self._DAYS[int(self._s["weekday"]) - 1]
        service = (
            f"# Rendered by `{SCRIPT} install` from [host_health.schedule].\n"
            "[Unit]\nDescription=vibey weekly host health (scripts/host_health.py)\n"
            "After=network-online.target\nWants=network-online.target\n\n"
            "[Service]\nType=oneshot\nNice=10\nIOSchedulingClass=idle\n"
            f"WorkingDirectory={workdir.replace('%', '%%')}\n"
            f"Environment={self._quote('PATH=' + path_env)}\n"
            f"ExecStart={exec_start}\n"
            f"StandardOutput=append:{log.replace('%', '%%')}\n"
            f"StandardError=append:{log.replace('%', '%%')}\n"
        )
        timer = (
            f"# Rendered by `{SCRIPT} install` from [host_health.schedule].\n"
            "[Unit]\nDescription=vibey weekly host health timer\n\n"
            "[Timer]\n"
            f"OnCalendar={day} *-*-* {int(self._s['hour']):02d}:{int(self._s['minute']):02d}:00\n"
            "Persistent=true\n"
            f"Unit={self._s['label']}.service\n\n"
            "[Install]\nWantedBy=timers.target\n"
        )
        return service, timer

    @staticmethod
    def _quote(part: str) -> str:
        return '"' + part.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%") + '"'


class UnitPlacement:
    """Refuses a unit that would run something from where it disappears (sub-doctrine
    10.h): a temporary directory, which a reboot empties, or a linked worktree, which is
    deleted when its lane ends."""

    @staticmethod
    def volatile_roots() -> list[str]:
        # Assembled from parts, as tests/meta/test_no_volatile_work_paths.py assembles its own,
        # so these roots -- which are refused here -- are not mistaken for a use of them.
        tmp = "/" + "tmp"
        roots = {
            tempfile.gettempdir(),
            tmp,
            "/private" + tmp,
            "/var" + tmp,
            "/private/var/" + "folders",
        }
        return sorted(os.path.realpath(r) for r in roots)

    @classmethod
    def refusal(cls, path: str) -> str | None:
        real = os.path.realpath(path)
        for root in cls.volatile_roots():
            if real == root or real.startswith(root.rstrip("/") + "/"):
                return f"{path} is under {root}, which a reboot empties (sub-doctrine 10.h)"
        for parent in (Path(path), *Path(path).parents):
            if (parent / ".git").is_file():
                return (
                    f"{path} is inside the linked worktree {parent}, which is deleted when its"
                    " lane ends (sub-doctrine 10.h)"
                )
        return None


# ------------------------------------------------------------------------ publishing


class Publisher(PublisherInterface):
    """Lands the host's records on the base branch through one pull request, from a clone of
    its own: the operator's checkout is never touched and develop is never pushed to."""

    def __init__(
        self,
        settings: HealthSettings,
        runner: CommandRunnerInterface,
        home: Path,
        render_check: Callable[[Path, Sequence[HealthRecord]], list[str]],
    ) -> None:
        self._cfg = settings["publish"]
        self._runner = runner
        self._home = home
        self._render_check = render_check
        self.clone = self._expand(str(self._cfg["clone_dir"]))
        self._record = str(settings["record"])
        self._docs = str(settings["docs_page"])

    def _expand(self, text: str) -> Path:
        return self._home / text[1:].lstrip("/") if text.startswith("~") else Path(text)

    def _git(self, *args: str, env: Mapping[str, str] | None = None) -> Any:
        ident: list[str] = []
        if self._cfg["git_user_name"]:
            ident += ["-c", f"user.name={self._cfg['git_user_name']}"]
        if self._cfg["git_user_email"]:
            ident += ["-c", f"user.email={self._cfg['git_user_email']}"]
        argv = ["git", "-C", str(self.clone), *ident, *args]
        result = self._runner.run(argv, timeout=float(self._cfg["git_timeout_s"]), env=env)
        if result.returncode:
            raise RuntimeError(f"{' '.join(argv[3:6])}: {result.tail()}")
        return result

    def ensure_clone(self) -> None:
        if (self.clone / ".git").exists():
            return
        self.clone.parent.mkdir(parents=True, exist_ok=True)
        url = f"https://github.com/{self._cfg['repository']}.git"
        argv = ["git", "clone", "--branch", str(self._cfg["base"]), url, str(self.clone)]
        result = self._runner.run(argv, timeout=float(self._cfg["git_timeout_s"]))
        if result.returncode:
            raise RuntimeError(f"git clone {url}: {result.tail()}")

    def refresh(self) -> Path:
        self.ensure_clone()
        base = str(self._cfg["base"])
        self._git("fetch", "--quiet", "origin", base)
        self._git("switch", "--quiet", "--force-create", str(self._cfg["branch"]), f"origin/{base}")
        return self.clone

    def gh_env(self) -> dict[str, str]:
        return {"GH_CONFIG_DIR": str(self._expand(str(self._cfg["gh_config_dir"])))}

    def publish(self, records: Sequence[HealthRecord], env: Mapping[str, str]) -> str:
        ledger = HealthLedger(self.clone / self._record)
        added = ledger.merge(records)
        problems = self._render_check(self.clone, ledger.read())
        if problems:
            raise RuntimeError("; ".join(problems))
        self._git("add", self._record, self._docs)
        if not self._runner.run(
            ["git", "-C", str(self.clone), "diff", "--cached", "--quiet"], timeout=60
        ).returncode:
            return "the committed record already holds every local record: nothing to publish"
        self._git(
            "commit",
            "--quiet",
            "-m",
            str(self._cfg["commit_title"]),
            "-m",
            f"Made-With: {self._cfg['made_with']}",
        )
        branch = str(self._cfg["branch"])
        merged = {**env, **self.gh_env()}
        self._git(
            "-c",
            "credential.helper=",
            "-c",
            "credential.helper=!gh auth git-credential",
            "push",
            "--quiet",
            f"--force-with-lease=refs/heads/{branch}",
            "origin",
            f"HEAD:{branch}",
            env=merged,
        )
        repo, base = str(self._cfg["repository"]), str(self._cfg["base"])
        timeout = float(self._cfg["git_timeout_s"])
        found = self._runner.run(
            [
                "gh",
                "pr",
                "list",
                "--repo",
                repo,
                "--head",
                branch,
                "--base",
                base,
                "--state",
                "open",
                "--json",
                "number",
                "--jq",
                ".[0].number",
            ],
            timeout=timeout,
            env=merged,
        )
        number = str(found.stdout).strip()
        if found.returncode == 0 and number:
            return f"added {added} record(s); updated pull request #{number}"
        created = self._runner.run(
            [
                "gh",
                "pr",
                "create",
                "--repo",
                repo,
                "--base",
                base,
                "--head",
                branch,
                "--title",
                str(self._cfg["commit_title"]),
                "--body",
                "The host's weekly health record (`scripts/host_health.py weekly`, run by the"
                " host's own launchd/systemd unit), with the page re-rendered. Every week the host"
                " has not yet landed is carried here, de-duplicated by run id. Merge through the"
                " normal train after the checks pass.",
            ],
            timeout=timeout,
            env=merged,
        )
        if created.returncode:
            raise RuntimeError(f"gh pr create: {created.tail()}")
        return f"added {added} record(s); opened {str(created.stdout).strip()}"


# ------------------------------------------------------------------------ the session


class MeasurementSession:
    """Runs every probe on this host and assembles one record with its forecast."""

    def __init__(
        self,
        repo: Path,
        settings: HealthSettings,
        clock: ClockInterface,
        runner: CommandRunnerInterface | None = None,
        system: str | None = None,
        home: Path | None = None,
    ) -> None:
        self._repo = repo
        self._settings = settings
        self._clock = clock
        self._runner = runner or SubprocessRunner()
        self._system = system or platform.system()
        self._home = home or Path.home()

    def specs(self) -> tuple[SpecsRecord | None, SpecsSettings, Mapping[str, Any]]:
        config_path = self._repo / str(self._settings["minimum_specs_config"])
        specs_settings = SpecsSettings.load(config_path)
        raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
        record_path = self._repo / specs_settings.record
        specs = SpecsRecord.load(record_path) if record_path.exists() else None
        return specs, specs_settings, raw

    def probes(
        self,
        ctx: ProbeContext,
        host: Mapping[str, Any],
        specs: SpecsRecord | None,
        specs_settings: SpecsSettings,
    ) -> list[ProbeInterface]:
        log = LlamaServerLog(ctx.path(str(specs_settings.ollama["server_log"])))
        gate = IdleGate(self._settings["idle"], log, ctx.runner)
        return [
            StorageProbe(ctx),
            BatteryProbe(ctx),
            ThermalProbe(ctx),
            MemoryProbe(ctx),
            ReliabilityProbe(ctx),
            ThroughputProbe(ctx, specs_settings.sovereign_model),
            MicroBenchmark(ctx, gate),
            PlatformProbe(ctx, host),
            CapacityProbe(ctx, specs, specs_settings.record),
        ]

    @staticmethod
    def weekly_writes(
        history: Sequence[HealthRecord],
        host: Mapping[str, Any],
        figures: Sequence[Figure],
        factory: FigureFactory,
        stamp: str,
    ) -> Figure:
        """Bytes written per week since this host's previous record: the counter's difference
        over the days between the two, times seven."""
        fid, label = "storage.bytes_written_per_week", "SSD data written per week"
        now = next((f for f in figures if f.id == "storage.bytes_written" and f.has_value), None)
        before = next(
            (
                (r, r.by_id()["storage.bytes_written"])
                for r in reversed(history)
                if r.fingerprint == host["fingerprint"]
                and "storage.bytes_written" in r.by_id()
                and r.by_id()["storage.bytes_written"].has_value
            ),
            None,
        )
        method = "difference of storage.bytes_written between two records"
        if now is None or before is None:
            reason = (
                "storage.bytes_written was not measured this time"
                if now is None
                else "needs an earlier record of this host with storage.bytes_written"
            )
            return factory.skipped(fid, label, "bytes/week", method, reason)
        days = Stamp.days(stamp) - Stamp.days(before[0].measured_at)
        if days <= 0:
            return factory.skipped(fid, label, "bytes/week", method, "no time between records")
        rate = round((float(now.value) - float(before[1].value)) / days * 7)
        return Figure(
            id=fid,
            label=label,
            value=rate,
            unit="bytes/week",
            status="derived",
            method=method,
            measured_at=stamp,
            host=str(host["fingerprint"]),
            formula="(bytes_now - bytes_before) / days_between * 7",
            inputs={
                "bytes_now": now.value,
                "bytes_before": before[1].value,
                "before_at": before[0].measured_at,
                "days_between": round(days, 4),
            },
        )

    def run(self, history: Sequence[HealthRecord]) -> HealthRecord:
        stamp = self._clock.now()
        bare = ProbeContext(
            self._settings,
            self._runner,
            FigureFactory(self._clock, ""),
            self._system,
            home=self._home,
        )
        host = HostIdentity(bare).describe()
        ctx = ProbeContext(
            self._settings,
            self._runner,
            FigureFactory(self._clock, str(host["fingerprint"])),
            self._system,
            home=self._home,
        )
        specs, specs_settings, raw = self.specs()
        figures: list[Figure] = []
        for probe in self.probes(ctx, host, specs, specs_settings):
            try:
                figures.extend(probe.run())
            except Exception as exc:  # noqa: BLE001 -- one probe's crash is recorded, not fatal
                figures.append(
                    ctx.figures.skipped(
                        f"{probe.name}.probe",
                        f"{probe.name} probe",
                        "verdict",
                        probe.name,
                        f"the probe crashed: {type(exc).__name__}: {exc}",
                    )
                )
        figures.append(self.weekly_writes(history, host, figures, ctx.figures, stamp))
        record = HealthRecord(
            run_id=f"{host['fingerprint']}@{stamp}",
            measured_at=stamp,
            host=host,
            figures=tuple(figures),
        )
        mine = [r for r in history if r.fingerprint == record.fingerprint] + [record]
        forecaster = Forecaster(self._settings, Thresholds(specs, raw))
        return HealthRecord(record.run_id, stamp, host, record.figures, forecaster.forecast(mine))


# ------------------------------------------------------------------------ the command


class HostHealthCli:
    """measure, forecast, render, check, conditions, render-unit, install, weekly."""

    def __init__(
        self,
        repo: Path = Path("."),
        clock: ClockInterface | None = None,
        runner: CommandRunnerInterface | None = None,
        home: Path | None = None,
        which: Callable[[str], str | None] = shutil.which,
    ) -> None:
        self._repo = repo
        self._clock = clock or SystemClock()
        self._runner = runner or SubprocessRunner()
        self._home = home or Path.home()
        self._which = which

    def parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
        parser.add_argument("--repo", type=Path, default=None)
        parser.add_argument("--config", default=DEFAULT_CONFIG, help="relative to --repo")
        sub = parser.add_subparsers(dest="command", required=True)
        measure = sub.add_parser("measure", help="probe this host; append to its own record")
        measure.add_argument(
            "--out", type=Path, default=None, help="default: [host_health] local_record"
        )
        forecast = sub.add_parser("forecast", help="this host's forecast, from a record")
        forecast.add_argument("--record", type=Path, default=None, help="default: the local record")
        sub.add_parser("render", help="rewrite the page's GENERATED blocks from the record")
        check = sub.add_parser("check", help="exit 1 if the record or the page is out of step")
        check.add_argument(
            "--against", default="", help="a git ref whose record must be a prefix of this one"
        )
        conditions = sub.add_parser("conditions", help="the tracking issue's conditions, as JSON")
        conditions.add_argument("--now", default="", help="default: the clock")
        unit = sub.add_parser("render-unit", help="write the weekly unit to --out, load nothing")
        unit.add_argument("--out", type=Path, required=True)
        unit.add_argument(
            "--platform", choices=("launchd", "systemd"), default=self._default_platform()
        )
        unit.add_argument(
            "--clone", type=Path, default=None, help="default: [host_health.publish] clone_dir"
        )
        install = sub.add_parser("install", help="clone, write the unit, print the load command")
        install.add_argument(
            "--platform", choices=("launchd", "systemd"), default=self._default_platform()
        )
        sub.add_parser("tools", help="which declared tools this platform has and lacks")
        sub.add_parser("weekly", help="measure, then publish (what the unit runs)")
        return parser

    @staticmethod
    def _default_platform() -> str:
        return "launchd" if sys.platform == "darwin" else "systemd"

    def _expand(self, text: str) -> Path:
        return self._home / text[1:].lstrip("/") if text.startswith("~") else Path(text)

    def forecaster(self, repo: Path, settings: HealthSettings) -> Forecaster:
        config_path = repo / str(settings["minimum_specs_config"])
        raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
        specs_path = repo / str(raw["minimum_specs"]["record"])
        specs = SpecsRecord.load(specs_path) if specs_path.exists() else None
        return Forecaster(settings, Thresholds(specs, raw))

    def render_check(
        self, repo: Path, settings: HealthSettings
    ) -> Callable[[Path, Sequence[HealthRecord]], list[str]]:
        def run(root: Path, records: Sequence[HealthRecord]) -> list[str]:
            renderer = HealthRenderer(self.forecaster(root, settings))
            page = root / str(settings["docs_page"])
            page.write_text(
                renderer.apply(page.read_text(encoding="utf-8"), records), encoding="utf-8"
            )
            drift = renderer.drift(page.read_text(encoding="utf-8"), records)
            return [f"{page}: blocks out of date: {', '.join(drift)}"] if drift else []

        return run

    def run(self, argv: Sequence[str]) -> int:
        args = self.parser().parse_args(list(argv))
        repo = (args.repo or self._repo).resolve()
        settings = HealthSettings.load(repo / args.config)
        committed = HealthLedger(repo / str(settings["record"]))
        local = HealthLedger(self._expand(str(settings["local_record"])))
        if args.command == "measure":
            target = HealthLedger(args.out) if args.out else local
            return self._measure(repo, settings, target)
        if args.command == "forecast":
            ledger = HealthLedger(args.record) if args.record else local
            hosts = HealthLedger.by_host(ledger.read())
            for history in hosts.values():
                print(json.dumps(self.forecaster(repo, settings).forecast(history), indent=2))
            if not hosts:
                print(f"{SCRIPT}: {ledger.path} holds no record yet", file=sys.stderr)
                return 1
            return 0
        if args.command == "render":
            problems = self.render_check(repo, settings)(repo, committed.read())
            print(f"{SCRIPT}: rendered {settings['docs_page']}")
            return 1 if problems else 0
        if args.command == "check":
            return self._check(repo, settings, committed, args.against)
        if args.command == "conditions":
            now = args.now or self._clock.now()
            result = ConditionEvaluator(settings, self.forecaster(repo, settings)).evaluate(
                committed.read(), now
            )
            print(json.dumps(result, indent=2))
            return 0
        if args.command == "tools":
            catalog = ToolCatalog(settings, platform.system())
            for name in catalog.tools():
                state = "MISSING; " + catalog.hint(name) if name in catalog.missing() else "present"
                print(f"tool {name}: {state}")
            return 0
        if args.command in ("render-unit", "install"):
            return self._unit(repo, settings, args)
        return self._weekly(repo, settings, local)

    def _measure(self, repo: Path, settings: HealthSettings, ledger: HealthLedger) -> int:
        record = MeasurementSession(repo, settings, self._clock, self._runner, home=self._home).run(
            ledger.read()
        )
        ledger.append(record)
        counts: dict[str, int] = {}
        for figure in record.figures:
            counts[figure.status] = counts.get(figure.status, 0) + 1
        fc = record.forecast
        print(
            f"{SCRIPT}: appended {record.run_id} to {ledger.path}: "
            + ", ".join(f"{n} {s}" for s, n in sorted(counts.items()))
        )
        print(
            f"{SCRIPT}: forecast: "
            + (
                f"replace by {fc['replace_by']} ({fc['earliest']} to {fc['latest'] or 'not bounded'}),"
                f" bound by {fc['binding']}"
                if fc.get("binding")
                else "no driver projects a replacement date yet"
            )
        )
        return 0

    def _check(
        self, repo: Path, settings: HealthSettings, committed: HealthLedger, against: str
    ) -> int:
        problems: list[str] = []
        try:
            records = committed.read()
        except ValueError as exc:
            print(f"{SCRIPT}: {exc}", file=sys.stderr)
            return 1
        page = repo / str(settings["docs_page"])
        drift = HealthRenderer(self.forecaster(repo, settings)).drift(
            page.read_text(encoding="utf-8"), records
        )
        if drift:
            problems.append(
                f"{settings['docs_page']}: generated blocks out of date: {', '.join(drift)}"
            )
        if against:
            before = self._runner.run(
                ["git", "-C", str(repo), "show", f"{against}:{settings['record']}"], timeout=60
            )
            if before.returncode == 0:
                changed = HealthLedger.append_only(str(before.stdout), committed.text())
                if changed:
                    problems.append(f"{settings['record']} is append-only, but {changed}")
        for problem in problems:
            print(f"{SCRIPT}: {problem}", file=sys.stderr)
        if problems:
            print(f"{SCRIPT}: run `python {SCRIPT} render`", file=sys.stderr)
            return 1
        print(f"{SCRIPT}: {len(records)} record(s) valid and the page is in step")
        return 0

    def _unit(self, repo: Path, settings: HealthSettings, args: argparse.Namespace) -> int:
        schedule = settings["schedule"]
        publish = settings["publish"]
        clone = getattr(args, "clone", None) or self._expand(str(publish["clone_dir"]))
        mac = args.platform == "launchd"
        log_dir = self._expand(str(schedule["log_dir_macos" if mac else "log_dir_linux"]))
        launcher = [str(part) for part in schedule["launcher"]]
        resolved = shutil.which(launcher[0]) or launcher[0]
        argv = [resolved, *launcher[1:], str(clone / SCRIPT), "--repo", str(clone), "weekly"]
        for path in (str(clone), str(log_dir), resolved):
            refusal = UnitPlacement.refusal(path)
            if refusal:
                print(f"{SCRIPT}: {refusal}; move it in scripts/host_health.toml", file=sys.stderr)
                return 78
        if args.command == "install":
            system = "Darwin" if mac else "Linux"
            installer = ToolInstaller(
                ToolCatalog(settings, system, self._which),
                self._runner,
                float(settings["tools"]["install_timeout_s"]),
            )
            for line in installer.ensure():
                print(line)
            publisher = Publisher(
                settings, self._runner, self._home, self.render_check(repo, settings)
            )
            publisher.ensure_clone()
            # launchd and systemd do not create a log file's directory; install does.
            log_dir.mkdir(parents=True, exist_ok=True)
        out = (
            args.out
            if args.command == "render-unit"
            else self._expand(str(schedule["unit_dir_macos" if mac else "unit_dir_linux"]))
        )
        out.mkdir(parents=True, exist_ok=True)
        renderer = SchedulerRenderer(schedule)
        label = str(schedule["label"])
        log = str(log_dir / "host-health.log")
        path_env = os.environ.get("PATH", "")
        if mac:
            unit = out / f"{label}.plist"
            unit.write_text(renderer.launchd(argv, str(clone), log, path_env), encoding="utf-8")
            written = [unit]
            load = [f'launchctl bootstrap "gui/$(id -u)" {unit}']
        else:
            service, timer = renderer.systemd(argv, str(clone), log, path_env)
            written = [out / f"{label}.service", out / f"{label}.timer"]
            written[0].write_text(service, encoding="utf-8")
            written[1].write_text(timer, encoding="utf-8")
            load = [
                "systemctl --user daemon-reload",
                f"systemctl --user enable --now {label}.timer",
            ]
        for path in written:
            print(f"wrote {path}")
        exists = "" if log_dir.is_dir() else f" ({log_dir} is created by `install`)"
        print(f"logs: {log}{exists}")
        print("load it with (vibey never loads a unit into your session):")
        for line in load:
            print(f"  {line}")
        return 0

    def _weekly(self, repo: Path, settings: HealthSettings, local: HealthLedger) -> int:
        publisher = Publisher(settings, self._runner, self._home, self.render_check(repo, settings))
        enabled = bool(settings["publish"]["enabled"])
        refused = ""
        if enabled:
            try:
                publisher.refresh()
            except RuntimeError as exc:
                refused = f"could not refresh {publisher.clone}: {exc}"
        # The week is measured and kept locally whatever happens to publishing.
        status = self._measure(repo, settings, local)
        if not enabled:
            print(f"{SCRIPT}: [host_health.publish] enabled = false: recorded locally only")
            return status
        if refused:
            # A clone that could not be brought up to the base is never published from.
            print(f"{SCRIPT}: {refused}; kept in {local.path} for next week", file=sys.stderr)
            return 1
        try:
            print(f"{SCRIPT}: {publisher.publish(local.read(), dict(os.environ))}")
        except (RuntimeError, OSError) as exc:
            # The local record keeps the week; the next run carries it (10.g). Said out loud.
            print(f"{SCRIPT}: publishing failed, kept in {local.path}: {exc}", file=sys.stderr)
            return 1
        return status


if __name__ == "__main__":
    sys.exit(HostHealthCli(Path.cwd()).run(sys.argv[1:]))
