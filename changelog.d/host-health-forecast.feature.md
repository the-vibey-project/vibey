* **health:** a weekly check of the machine vibey and krypton run on, and a forecast of when
  it needs replacing (`scripts/host_health.py`, configured in `scripts/host_health.toml`).
  The probes run on the host itself, from a launchd agent or a systemd user timer that
  `python scripts/host_health.py install` renders. They cannot run in the self-hosted
  runner, a Linux container on the host that sees none of its hardware. Nothing needs
  `sudo`. The probes cover SSD health through smartctl, or the OS's own SMART verdict
  without it, and free space; battery cycles and capacity against design; thermal
  limits; memory, swap and pressure; panic, reset, shutdown-stall and jetsam reports, read
  by name and date only; the sovereign model's weekly generation rate, mined passively
  from the Ollama log; an idle-gated CPU and disk microbenchmark; the OS's vendor support
  date; and vibey's own memory and disk requirements, read from the minimum-specs record.
  Every figure is measured, declared or skipped with its reason. The record is append-only
  JSON lines with a hashed host fingerprint and no serials or host name. Each driver is
  fitted with Theil-Sen and Sen's interval on the slope against its declared threshold.
  The machine's replacement date is the earliest driver's, with its interval and the
  driver that binds; a trend with fewer than four weekly points says "insufficient
  history". Each week lands as a pull request from a clone of its own, carrying any week
  that has not merged yet. `.github/workflows/host-health.yml` keeps one tracking issue
  open while a host goes quiet, a probe goes missing, or a driver nears or passes its
  threshold. `vibey doctor` prints the newest record, its age and the forecast. There is
  a new page, "Host health".
  The probes' tools are declared per platform in `[host_health.tools]`. `install` runs a
  privilege-free install (`brew install smartmontools`) and prints the `sudo` command for
  apt, pacman or dnf instead of running it. The Apple SSD is read without `sudo`. Its
  unreadable error-log page is recorded as skipped with smartctl's own reason. Bytes
  written, writes per power-on hour and bytes written per week are recorded. The primary
  SSD driver is data written against rated endurance; Apple publishes no TBW rating for
  its SSDs, so that driver says so and the forecast falls back to percentage used. A
  declared hypothesis (swap as a possible contributor to SSD writes) is printed as a
  note, never as a finding.
