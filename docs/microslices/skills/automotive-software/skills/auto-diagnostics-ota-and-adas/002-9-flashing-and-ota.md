---
id: skill-9-flashing-and-ota-0e162e1b01
purpose: 9 flashing and ota
source: src/vibey_tools/skills/plugins/automotive-software/skills/auto-diagnostics-ota-and-adas/SKILL.md
requires: ["skill-8-diagnostics-d0352fede1"]
links: ["skill-10-adas-and-autonomy-2c60d92366"]
---

## §9. Flashing and OTA

**Reprogramming sequence** (typically UDS-based):
```
Enter programming session → security access → erase → 0x34 request download
  → 0x36 transfer data (blocks) → 0x37 exit → ⚠️ verify checksum/signature
  → reset → verify version
```
**⚠️ The bootloader is the most safety-critical software in the ECU**, because a failure
there is unrecoverable without physical access. **Design rules mirror flight software:**
- **⚠️ The bootloader must be immutable, or A/B redundant with a golden image.**
- **⚠️ A/B (dual-bank) partitions: write to the inactive bank, verify, then switch.**
- **Anti-rollback protection** and **signature verification before activation.**
- **⚠️ Power-loss safety at every step** — the customer will unplug it mid-update.

**OTA adds**: campaign management and staged rollout, **preconditions** (⚠️ **vehicle
parked, in Park, sufficient battery state of charge, not in a tunnel**), driver consent,
bandwidth and cost management, and **fleet-wide rollback.**

**⚠️ And OTA is now regulated (§7.2 → `auto-real-time-safety-and-cybersecurity`).** R156's SUMS requires: a documented **secure update
chain** with authenticity, integrity, **anti-rollback and eligibility checks**; **campaign
planning and approval**; and **post-update validation with records.** ⚠️ **You must be able
to prove, per vehicle, what software it is running and that the update was authorized —
and for updates that affect type-approved functions, the approval itself may need
revisiting.**

**⚠️ The cultural point**: OTA does not make automotive software agile in the web sense.
It makes it **recallable without a service visit**, which is enormous — but the approval,
validation and evidence burden per release is unchanged.

---
