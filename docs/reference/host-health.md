# Host health

How healthy is the machine vibey and krypton run on, and how long until it needs replacing?
The tables on this page are **generated**. `scripts/host_health.py` writes them from the
committed, append-only weekly record,
[`docs/architecture/evidence/host-health.jsonl`](https://github.com/the-vibey-project/vibey/blob/develop/docs/architecture/evidence/host-health.jsonl).
The text between the markers is never edited by hand. The prose around them is.

## Where the weekly run happens, and why there

The probes run **on the host itself**, once a week. A launchd agent (macOS) or a systemd
user timer (Linux) runs them, and `python scripts/host_health.py install` renders that unit
from `[host_health.schedule]` in `scripts/host_health.toml`. They do not run in GitHub
Actions. The project's self-hosted runner is a Linux container on the host (`vibey-gh
runner` starts it with `docker run`), and a container cannot see the host's SSD health,
battery, thermal state or real memory pressure.

`install` clones the repository into a directory of its own (`[host_health.publish]
clone_dir`). It then writes the unit into the service manager's directory and prints the one
command that loads it. vibey never loads a unit into your session itself.

```bash
# macOS, from your vibey checkout
uv run --no-project --python 3.12 python scripts/host_health.py install
launchctl bootstrap "gui/$(id -u)" ~/Library/LaunchAgents/dev.vibey.host-health.plist

# Linux
uv run --no-project --python 3.12 python scripts/host_health.py install
systemctl --user daemon-reload && systemctl --user enable --now dev.vibey.host-health.timer
```

Each week the unit runs `scripts/host_health.py weekly`, which does three things:

1. It fetches the clone and starts a fresh `automation/host-health` branch from `develop`.
2. It probes the host and appends one record to the host's own durable copy
   (`[host_health] local_record`).
3. It merges in every local record that the committed file does not hold yet, matched by run
   id. A week whose pull request never merged is carried by the next one, never dropped.
   Then it re-renders this page, checks it, commits, pushes the branch, and opens or updates
   one pull request.

Nothing reaches `develop` except through that pull request and the merge train. If
publishing fails, the week stays in the local record and the run says so.

A hosted workflow (`.github/workflows/host-health.yml`) reads the committed record every
week. It keeps **one tracking issue** open while any of these conditions holds:

- a host has not recorded for 14 days;
- an expected probe is missing from a host's last two records;
- a driver is past its threshold;
- a replacement is predicted within the warning horizon.

It closes the issue when none of them holds. `vibey doctor` prints the newest record's
summary, its age and the forecast.

## What is measured, and how

Nothing needs `sudo`. Some probes cannot run: one would need privileges, a tool is not
installed, or the machine lacks the hardware (a desktop has no battery). Each of those is
recorded as **skipped**, with the reason, and no number is invented for it.

| Probe | macOS | Linux |
|---|---|---|
| Storage | `smartctl --json -a disk0` when smartmontools is installed (wear, spare, data written, media errors, power-on hours). `diskutil info` for the SMART verdict. `df` for free space. | `smartctl --json -a`, which usually needs root and is skipped without it. `df`. |
| Battery | `ioreg -rn AppleSmartBattery` (cycles, full-charge against design capacity, design cycle count). `system_profiler SPPowerDataType` (condition). | `/sys/class/power_supply/BAT*` |
| Thermal | `pmset -g therm` (CPU speed limit, warning level) | Thermal zones, cpufreq caps against the hardware maximum, throttle counters |
| Memory | `sysctl hw.memsize vm.swapusage`, `memory_pressure -Q`, `vm_stat` rates since boot | `/proc/meminfo`, `/proc/pressure/memory`, `/proc/vmstat` |
| Reliability | Panic, reset, shutdown-stall and jetsam reports, **by file name and date only**. The reports are never opened. Time since boot. | pstore crash records, `/proc/uptime` |
| Throughput | The sovereign model's generation rate per week, mined **passively** from the Ollama server log and its rotations. No request is made. | Same |
| Microbenchmark | SHA-256 and a flushed sequential write. They run only when the minimum-specs idle gate says the host is quiet. | Same |
| Platform | The OS and its vendor support end, and the hardware's support status. Declared in the TOML with a source and a last-verified date. | Same |
| Capacity | vibey's own memory and disk requirements, copied in from the [minimum-specs record](system-requirements.md) with their dates | Same |

Privacy (SD-01 §1): the host is named by a fingerprint, a truncated SHA-256 over its
hardware facts and platform identifier. The identifier, serial numbers and the host name
never reach the record.

## How the forecast is made

Each **driver** is one reason the machine might need replacing. `[host_health.drivers]`
declares each one with its threshold and where that threshold comes from.

- **Trend** drivers are SSD wear, battery capacity and cycles, generation rate, and free
  disk. Each is fitted over the weekly history with the Theil-Sen estimator, which an odd
  week cannot drag, and with Sen's rank-based interval on the slope
  (`scripts/host_health_forecast.py`). The projected date is where the line reaches the
  threshold. The interval comes from the slope's bounds. When the data cannot rule out
  "never", the interval says *not bounded*. With fewer than four weekly points, a trend
  driver says **insufficient history** and projects nothing.
- **Level** drivers are memory against vibey's minimum, sustained swap, kernel panics and
  thermal limits. One is past its threshold when the last *confirm* records all are.
- **Dated** drivers are the OS leaving vendor support and the hardware becoming obsolete.
  They take the date the vendor publishes. Where the vendor publishes none, they say so.

The machine's replacement date is the **earliest** driver's date, and the page names the
driver that binds. The interval runs from the earliest bound across the drivers to the
smallest finite latest bound. vibey's own requirements are read from the minimum-specs
machinery, never restated here. The minimum and recommended memory and free disk come from
its record, and the minimum generation rate from `scripts/minimum_specs.toml`.

## The hosts

<!-- BEGIN GENERATED health:hosts — regenerated by scripts/host_health.py -->
<!-- END GENERATED health:hosts -->

## The forecast

<!-- BEGIN GENERATED health:forecast — regenerated by scripts/host_health.py -->
<!-- END GENERATED health:forecast -->

## The newest record

<!-- BEGIN GENERATED health:latest — regenerated by scripts/host_health.py -->
<!-- END GENERATED health:latest -->
