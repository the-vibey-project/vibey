---
id: skill-12-quantum-networking-and-sensing-dce2c7ef2e
purpose: 12 quantum networking and sensing
source: src/vibey_tools/skills/plugins/quantum-computing/skills/quantum-applications-and-post-quantum-crypto/SKILL.md
requires: ["skill-11-applications-eb3cf9f7fe"]
links: ["skill-13-post-quantum-cryptography-246c9f6706"]
---

## §12. Quantum Networking and Sensing

**[DURABLE] These are separate fields from quantum computing and are commercially closer.**

**Quantum sensing** is the most mature quantum technology commercially: atomic clocks,
magnetometry (SQUIDs, NV centers), gravimetry, inertial navigation. **Real products, real
revenue, today** — and often ignored because it isn't a computer.

**Quantum networking / repeaters** — entanglement distribution, quantum memories, the
long-term "quantum internet" vision, and near-term links between quantum processors (which
is how trapped-ion and photonic architectures plan to scale).

**QKD (quantum key distribution)** — **[CONTESTED, and the disagreement is unusually
sharp]**. *For*: information-theoretic security grounded in physics rather than
computational assumptions. *Against*: **NSA, NCSC, and ANSSI all recommend post-quantum
cryptography over QKD** for national security systems, citing the requirement for
special-purpose hardware, the inability to provide authentication (QKD needs a classical
authenticated channel anyway), distance limitations and trusted-relay requirements,
denial-of-service exposure, and side-channel attacks on real implementations. **CNSA 2.0
explicitly rejects QKD for NSS.** **The practical guidance: PQC (§13) is the answer for
essentially all organizations; QKD is a niche with specific physical-layer requirements.**

---
