---
id: skill-27-flight-software-fdir-command-and-telemetry-and-in-flight-update-559741efc0
purpose: 27 flight software fdir command and telemetry and in flight update
source: src/vibey_tools/skills/plugins/military-space-rockets-and-fusion/skills/endeavour-satellites-flight-software-and-instruments/SKILL.md
requires: ["skill-26-satellite-and-space-probe-design-types-and-orbits-bf7b914aba"]
links: ["skill-28-scientific-instrumentation-and-planetary-protection-9b8c0e136b"]
---

## §27 Flight software: FDIR, command and telemetry, and in-flight update

Three properties make spacecraft software different from all other software.

1. **You cannot patch your way out.** Uplink is bandwidth-limited, latency-bound, and sometimes
   impossible. A bug that bricks the receiver ends the mission.
2. **The hardware is actively hostile.** Radiation flips bits in RAM and registers with no warning
   and no error signal. Software must assume its own memory is corrupting underneath it.
3. **Correct-but-late is wrong.** A control loop that misses its deadline has failed regardless of
   the answer it eventually produces.

> **DETERMINISM OUTRANKS THROUGHPUT.** That ordering inverts almost every instinct from server-side
> engineering, where throughput is the headline number and a late answer is merely slow. Here a late
> answer is a wrong answer, and a fast average with an unbounded tail is a failed design.

### FDIR: fault detection, isolation, and recovery

FDIR is **the organizing principle of flight software, not a feature of it**. The chain:

- **Detect** — limit checks, watchdogs, consistency checks, checksums, heartbeat monitors.
- **Isolate** — determine *which* component, avoiding misattribution. This is **the hardest step**:
  a detector fires on a symptom, and the symptom is rarely local to the fault.
- **Recover** — an escalation ladder: retry → reconfigure to a redundant unit → reset component →
  reset processor → safe mode. Redundancy types and common-cause failure are §22 →
  `endeavour-mission-architecture-and-spacecraft-subsystems`.

**Safe mode is the design that saves missions**: power-positive, thermally stable, Sun- or
Earth-pointed, minimal software, survivable indefinitely awaiting ground instruction. Every
deep-space mission enters safe mode. **The design question is not whether, but whether it can sit
there for a month without degrading.** The operational companions to safe mode — command loss timers
that reconfigure after N days without contact — are §19 →
`endeavour-mission-architecture-and-spacecraft-subsystems`.

### The hard-won lessons

- **Fault protection that misfires is itself a hazard.** A spurious safe-mode entry during orbit
  insertion or EDL can lose the mission, so critical sequences **inhibit selected fault responses**.
- **Don't recover into the fault.** Repeated automatic resets that re-trigger the same condition burn
  power and can exhaust a resource.
- **Log everything before acting.** The telemetry that explains a fault is often lost in the recovery
  that follows it.

### Command and telemetry

**CCSDS is the international standard set, and it is genuinely worth following rather than
inventing.** Command design principles:

- **Idempotent where possible** — a retransmitted command should not do the thing twice.
- **Two-stage arm/fire for hazardous commands** — deployments, pyros, engine starts.
- **Validate before execute** — checksum, authenticate, range-check every parameter.
- **Reject, don't clamp.** Silently clamping an out-of-range parameter hides the ground error that
  produced it, which is the error you actually needed to see.

Four telemetry types, each doing a different job:

| Type | What it is | Why it exists |
|---|---|---|
| Housekeeping | Periodic state | The continuous health picture |
| Event / EVR messages | The spacecraft's log | **Your only debugger** |
| Science data | The payload's output | The reason for the mission |
| Diagnostic dwell | Read arbitrary memory addresses | Indispensable for in-flight debugging |

**Design telemetry for the anomaly you haven't had yet.** The recurring operational regret is
insufficient telemetry to diagnose a fault after it occurs — and by then the channel list is fixed.

### In-flight software update

> **THE HIGHEST-STAKES OPERATION IN THE DISCIPLINE.** Six design rules, each written in blood:
> (1) the bootloader must be immutable, or dual-redundant with a golden image; (2) uplink to inactive
> memory, verify checksum, then switch; (3) automatic rollback on failure to check in after N
> minutes; (4) never patch the receive chain and the patch mechanism at once; (5) test the exact
> uplink product on the exact testbed configuration; (6) keep patch granularity small enough to fit
> the uplink budget. **A failed update that bricks the command receiver is unrecoverable and has
> ended missions.**

The counterexample worth knowing: **Voyager received a software patch in 2023–24 to work around
degraded memory, 46 years after launch**, on a system whose original engineers had retired or died.
That is only possible because the update path was designed conservatively from the start — the whole
case for rules that look paranoid on the ground.

---
