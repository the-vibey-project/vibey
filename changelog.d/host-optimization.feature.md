* **health:** the machine vibey runs on has a declared tuning, and every change to it is
  measured. `scripts/host_tuning.toml` declares each setting with its class, the evidence
  behind it, its expected effect, its risk and the weekly figures that judge it; `python
  scripts/host_health.py tune check|plan|apply|undo` reports drift between declared and
  actual, applies only what each item's gate allows (class A always; class B once a merged
  pull request adopts it after the review canary held; class C once the operator approved
  it), journals every prior value so `undo` restores it, and never restarts a service or
  runs sudo. The Ollama environment is set the way each platform supports: `launchctl
  setenv` plus a login agent on macOS, a staged systemd drop-in on Linux; `check` reads the
  model runner's argv to prove a setting reached it. The weekly host-health record gains
  model loads per day and distinct context sizes, a memory budget by process group, disk
  writes per hour since boot with the share that is swap, and the tuning in force.
  `docs/runbooks/host-optimization.md` has the measured budget (on the operator's 24 GiB
  host, swap-outs were 85% of 152 GB/h of SSD writes, and process file writes 1.2%), the
  classified plan, the class-B adoption procedure and the operator's class-C asks.
