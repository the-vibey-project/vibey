---
id: skill-6-functional-safety-iso-26262-6140994c36
purpose: 6 functional safety iso 26262
source: src/vibey_tools/skills/plugins/automotive-software/skills/auto-real-time-safety-and-cybersecurity/SKILL.md
requires: ["skill-5-real-time-and-scheduling-6256ce9ef2"]
links: ["skill-7-cybersecurity-and-regulation-e0856c030b"]
---

## §6. Functional Safety — ISO 26262

**⚠️ The governing standard, and it structures everything about how automotive software
is built.**

### 6.1 ASIL — and how it's determined
**Hazard Analysis and Risk Assessment (HARA)** rates each hazardous event on three axes:
```
S  Severity     S0 none → S3 life-threatening
E  Exposure     E0 improbable → E4 high probability of the operating situation
C  Controllability  C0 controllable in general → C3 difficult/uncontrollable
                ⚠️ C is about whether the DRIVER can avert the harm
    ↓
ASIL A (lowest) → B → C → D (highest)     plus QM = "quality management only,
                                          no ISO 26262 requirements"
```
**⚠️ The three-axis structure is the part people miss**: a severe hazard that occurs rarely
*and* is easily controlled may still come out QM. **Exposure and controllability genuinely
reduce the rating** — which is why the same failure means different things in different
vehicles.

**Typical ratings**: ⚠️ **steering and braking ASIL D; airbag deployment ASIL D; engine
management typically C or D; adaptive cruise B–C; instrument cluster warnings B;
infotainment QM.**

### 6.2 ASIL decomposition
**⚠️ A powerful and frequently-abused mechanism.** You may decompose an ASIL-D requirement
into two ASIL-B(D) elements — **but only if they are genuinely independent.**
> **⚠️ GOTCHA — decomposition requires demonstrated freedom from interference.**
> Shared power supply, shared clock, shared memory, shared bus, common design error,
> common tooling — ⚠️ **any of these is a common-cause failure that invalidates the
> decomposition.** **A dependent-failure analysis is mandatory, and "we put them on
> different cores of the same chip" is usually not sufficient on its own.**

### 6.3 The safety lifecycle
```
Item definition → HARA → Safety goals (each with an ASIL)
  → Functional Safety Concept → Technical Safety Concept
    → Hardware and Software development (⚠️ V-model, §11)
      → Integration and verification → Safety validation
        → Production, operation, ⚠️ and field monitoring
```
**Work products**: the **safety case** (⚠️ **the argued, evidenced claim that the item is
acceptably safe — this is the deliverable**), FMEA, **FTA**, **FMEDA** for hardware metrics,
and confirmation measures (review, audit, assessment).

**Hardware metrics** for ASIL D: **SPFM ≥ 99%**, **LFM ≥ 90%**, and a **PMHF target of
<10⁻⁸ failures/hour** (⚠️ **10 FIT**). **ASIL B: SPFM ≥ 90%, LFM ≥ 60%, <10⁻⁷/h.**

### 6.4 Software mechanisms you'll actually implement
**Memory protection between partitions**, **program flow monitoring** (⚠️ **a watchdog
that checks the *sequence* of checkpoints, not just aliveness — an alive-but-wrong task is
the failure mode a simple watchdog misses**), **end-to-end (E2E) protection** on
communicated data (⚠️ **CRC + alive counter + data ID, so a receiver detects corruption,
repetition, loss or masquerade regardless of what the network did**), **dual-storage and
inverse-storage of critical variables**, **plausibility checks**, **lockstep cores with
comparator**, and **the safe state** — ⚠️ **every safety concept must define what safe
looks like, and "shut down" is not always safe: losing power steering assist at speed is
itself a hazard.**

**Tool confidence**: ⚠️ **your compiler and code generator need a TCL/TD classification
and qualification evidence.** You cannot silently upgrade a toolchain.

### 6.5 SOTIF — ISO 21448
**⚠️ ISO 26262 covers malfunction. SOTIF covers the case where everything works as
designed and the behaviour is still unsafe** — insufficient specification, or performance
limitations in the intended function.

**⚠️ This is the standard that matters for ADAS and autonomy**, because a perception system
that correctly executes its algorithm and still fails to detect a pedestrian in unusual
lighting has no *malfunction*. The framework works in four areas:
```
Area 1  known, safe          Area 2  ⚠️ known, UNSAFE  → mitigate
Area 3  ⚠️ unknown, unsafe    → the real problem: find them and move them to Area 2
Area 4  unknown, safe
```
**⚠️ The engineering task is shrinking Area 3**, via scenario catalogues, field data, and
enormous validation mileage — **and it does not have a clean termination criterion, which
is the honest difficulty at the centre of autonomous-vehicle validation** (§10.4 → `auto-diagnostics-ota-and-adas`).

---
