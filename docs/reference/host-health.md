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
**Host `sha256:ec5e81b92e3a09da`** (Mac17,2 · Apple M5 · 24 GiB · macOS 26.6.2 (25G83)): 2 weekly record(s), 2026-10-01 to 2026-10-02.
<!-- END GENERATED health:hosts -->

## The forecast

<!-- BEGIN GENERATED health:forecast — regenerated by scripts/host_health.py -->
**Host `sha256:ec5e81b92e3a09da`** (Mac17,2 · Apple M5 · 24 GiB · macOS 26.6.2 (25G83)): 2 weekly record(s), 2026-10-01 to 2026-10-02.

**No driver projects a replacement date yet.** Trend drivers need 4 weekly points; dated drivers need a vendor date. Each driver's reason is in the table below. As of 2026-10-02.

> Hypothesis, not a conclusion: 16.38 GiB of swap in use on 24 GiB of memory, with swap-outs of about 62.3 GB/h since boot, may be a large part of the SSD's 108.5 GB per power-on hour of writes. The record cannot attribute writes to swap; per-process disk I/O would test it.

| Driver | Latest | Threshold | State | Date (interval) | Points |
|---|---|---|---|---|---|
| SSD data written vs rated endurance (TBW) | 36.55 TB | — | unknown | threshold unavailable: storage.rated_endurance_tb: Apple publishes no endurance (TBW) rating for its internal SSDs; a search on 2026-10-01 found only third-party estimates and forum figures, which are not a rating (verified 2026-10-01); the forecast rests on SSD wear (NVMe percentage used) instead | 1 |
| SSD wear (NVMe percentage used) | 1 % | 100 (declared in scripts/host_health.toml) | insufficient-history | 1 of the 4 weekly points a trend needs | 1 |
| SSD available spare at its threshold | 1 percentage points | 0 (declared in scripts/host_health.toml) | within | — | 1 |
| Battery full-charge capacity vs design | 1.0162 ratio | 0.8 (declared in scripts/host_health.toml) | insufficient-history | 2 of the 4 weekly points a trend needs | 2 |
| Battery cycles vs the design cycle count | 18 count | 1000 (this host's battery.design_cycle_count (2026-10-02)) | insufficient-history | 2 of the 4 weekly points a trend needs | 2 |
| Sovereign-model generation rate | 25.51 tokens/s | 10 (scripts/minimum_specs.toml minimum_specs.assumptions.minimum_gen_tok_s) | insufficient-history | 2 of the 4 weekly points a trend needs | 2 |
| Free disk vs vibey's minimum | 492.3 GB | 20 (minimum-specs record disk.minimum_gb (derived, 2026-09-30)) | insufficient-history | 2 of the 4 weekly points a trend needs | 2 |
| Memory vs vibey's minimum | 24 GB | 24 (minimum-specs record ram.minimum_gb (derived, 2026-09-30)) | within | — | 2 |
| Swap in use vs memory (sustained) | 0.682 ratio | 0.5 (declared in scripts/host_health.toml) | unconfirmed | past the threshold in 2 of the 3 records that confirm it | 2 |
| Kernel panics in the trailing window | 1 count | 3 (declared in scripts/host_health.toml) | within | — | 2 |
| Thermal CPU speed limit (sustained) | 100 % | 99 (declared in scripts/host_health.toml) | within | — | 2 |
| Operating system out of vendor support | — | — | unknown | Apple publishes no end-of-support date for a macOS release (its security-releases page lists updates, not end dates) (source https://support.apple.com/en-us/100100, verified 2026-10-01) | 0 |
| Hardware obsolete (vendor policy) | — | — | unknown | Apple has not stopped selling it as far as this table records; set last_sold when it does (policy: obsolete 7 years after the last sale; source https://support.apple.com/en-us/102772, verified 2026-10-01) | 0 |
<!-- END GENERATED health:forecast -->

## The newest record

<!-- BEGIN GENERATED health:latest — regenerated by scripts/host_health.py -->
**Host `sha256:ec5e81b92e3a09da`** (Mac17,2 · Apple M5 · 24 GiB · macOS 26.6.2 (25G83)): 2 weekly record(s), 2026-10-01 to 2026-10-02.

| Figure | Value | Status | How |
|---|---|---|---|
| Battery full-charge capacity / design | 1.0162 ratio | measured | ioreg -rn AppleSmartBattery: AppleRawMaxCapacity / DesignCapacity |
| Battery condition | Normal | measured | system_profiler SPPowerDataType |
| Battery cycle count | 18 count | measured | ioreg -rn AppleSmartBattery: CycleCount |
| Battery design cycle count | 1000 count | measured | ioreg -rn AppleSmartBattery: DesignCycleCount9C |
| vibey's minimum free disk | 20 GB | declared | read docs/architecture/evidence/minimum-specs.json: disk.minimum_gb (source: docs/architecture/evidence/minimum-specs.json) |
| vibey's recommended free disk | 50 GB | declared | read docs/architecture/evidence/minimum-specs.json: disk.recommended_gb (source: docs/architecture/evidence/minimum-specs.json) |
| vibey's minimum memory | 24 GB | declared | read docs/architecture/evidence/minimum-specs.json: ram.minimum_gb (source: docs/architecture/evidence/minimum-specs.json) |
| vibey's recommended memory | 32 GB | declared | read docs/architecture/evidence/minimum-specs.json: ram.recommended_gb (source: docs/architecture/evidence/minimum-specs.json) |
| Memory compressions per hour | 64,502,520 pages/h | measured | vm_stat counter / hours since kern.boottime |
| System-wide memory free | 11 % | measured | memory_pressure -Q |
| Installed memory, GB as sold | 24 GB | measured | sysctl -n hw.memsize |
| Installed memory | 24 GiB | measured | sysctl -n hw.memsize |
| Swap size | 17 GiB | measured | sysctl vm.swapusage |
| Swap in use | 16.38 GiB | measured | sysctl vm.swapusage |
| Swap in use / installed memory | 0.682 ratio | measured | sysctl vm.swapusage |
| Swap-out volume per hour | 62.3 GB/h | measured | vm_stat Swapouts x page size / hours since kern.boottime |
| Swap-outs per hour | 3,802,632 pages/h | measured | vm_stat counter / hours since kern.boottime |
| CPU: SHA-256 throughput, one core | 2965.2 MiB/s | measured | best of 3: SHA-256 over 256 MiB in memory |
| Disk: fsynced sequential write | 1763.6 MiB/s | measured | best of 3: 128 MiB written and flushed to the drive (F_FULLFSYNC on macOS, fsync elsewhere), scratch file removed |
| Hardware obsolete under the vendor's policy | — | skipped | skipped: Apple has not stopped selling it as far as this table records; set last_sold when it does (policy: obsolete 7 years after the last sale; source https://support.apple.com/en-us/102772, verified 2026-10-01) |
| Operating system | macOS 26.6.2 (25G83) | measured | sw_vers |
| OS vendor support ends | — | skipped | skipped: Apple publishes no end-of-support date for a macOS release (its security-releases page lists updates, not end dates) (source https://support.apple.com/en-us/100100, verified 2026-10-01) |
| Crash, panic and shutdown events found | 9 event(s) | measured | list report names in /Library/Logs/DiagnosticReports, /Library/Logs/DiagnosticReports/Retired, ~/Library/Logs/DiagnosticReports |
| jetsam events in the last 30 days | 1 count | measured | list report names in /Library/Logs/DiagnosticReports, /Library/Logs/DiagnosticReports/Retired, ~/Library/Logs/DiagnosticReports |
| kernel panic events in the last 30 days | 1 count | measured | list report names in /Library/Logs/DiagnosticReports, /Library/Logs/DiagnosticReports/Retired, ~/Library/Logs/DiagnosticReports |
| reset events in the last 30 days | 1 count | measured | list report names in /Library/Logs/DiagnosticReports, /Library/Logs/DiagnosticReports/Retired, ~/Library/Logs/DiagnosticReports |
| shutdown stall events in the last 30 days | 6 count | measured | list report names in /Library/Logs/DiagnosticReports, /Library/Logs/DiagnosticReports/Retired, ~/Library/Logs/DiagnosticReports |
| Days since boot | 1.01 d | measured | sysctl -n kern.boottime |
| SSD available spare | 100 % | measured | smartctl --json=c -a disk0 |
| SSD data written, in bytes | 36,554,771,968,000 bytes | measured | smartctl --json=c -a disk0 |
| SSD data written per week | — | skipped | skipped: needs an earlier record of this host with storage.bytes_written |
| SSD critical warning bits | 0 bits | measured | smartctl --json=c -a disk0 |
| SSD error-log entries | — | skipped | skipped: smartctl could not read the error-information log page: Read 1 entries from Error Information Log failed: GetLogPage failed: system=0x38, sub=0x0, code=745 |
| Free disk on the data volume | 492.3 GB | measured | df -Pk /System/Volumes/Data |
| SSD media and data integrity errors | 0 count | measured | smartctl --json=c -a disk0 |
| SSD model | APPLE SSD AP1024Z | measured | smartctl --json=c -a disk0 |
| SSD wear: NVMe percentage used | 1 % | measured | smartctl --json=c -a disk0 |
| SSD power-on hours | 337 h | measured | smartctl --json=c -a disk0 |
| SSD rated endurance (TBW) | — | skipped | skipped: Apple publishes no endurance (TBW) rating for its internal SSDs; a search on 2026-10-01 found only third-party estimates and forum figures, which are not a rating (verified 2026-10-01) |
| Data volume size | 994.6 GB | measured | df -Pk /System/Volumes/Data |
| SSD SMART overall status | passed | measured | smartctl --json=c -a disk0 |
| SSD available spare above its threshold | 1 percentage points | measured | smartctl --json=c -a disk0 |
| SSD data written | 36.55 TB | measured | smartctl --json=c -a disk0 |
| SSD unsafe shutdowns | 10 count | measured | smartctl --json=c -a disk0 |
| SSD writes per power-on hour (lifetime average) | 108.5 GB/h | measured | smartctl --json=c -a disk0 |
| CPU speed limit | 100 % | measured | pmset -g therm |
| Thermal warning level | 0 level | measured | pmset -g therm |
| Generation rate, newest week's median | 25.51 tokens/s | measured | mine ~/.ollama/logs/server*.log (passive; no request is made) |
| Generation rate by week | 2 week(s) of medians | measured | mine ~/.ollama/logs/server*.log (passive; no request is made) |
<!-- END GENERATED health:latest -->
