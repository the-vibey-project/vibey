---
id: skill-24-what-s-live-checked-august-2026-0c8ff4161b
purpose: 24 what s live checked august 2026
source: src/vibey_tools/skills/plugins/quantum-cryptography-and-quantum-internet/skills/qcrypto-reference/SKILL.md
requires: []
links: ["skill-25-misconceptions-1fb9ca2159"]
---

## §24. What's Live — checked August 2026

### 24.1 ⚠️ Quantum repeaters crossed a real threshold
**⚠️ §14 → `qcrypto-repeaters-memory-entanglement-distribution-and-satellite`'s bottleneck moved in early 2026, and this is the development the NCSC named as
most likely to change its assessment** (§20 → `qcrypto-official-position-qrng-quantum-threat-and-choosing`).

- **⚠️ THE USTC RESULT.** ⚠️ **A team led by Jian-Wei Pan and Qiang Zhang, published in
  Nature in February 2026, demonstrated remote memory-memory entanglement between trapped
  calcium-40 ions connected by 10 km of spooled telecom fibre — achieving a coherence time
  of 550 ± 36 ms against an average entanglement generation time of 450 ms.**
- **⚠️ WHY THAT SPECIFIC COMPARISON IS THE WHOLE POINT** (§14 → `qcrypto-repeaters-memory-entanglement-distribution-and-satellite`, §15 → `qcrypto-repeaters-memory-entanglement-distribution-and-satellite`): ⚠️ **entanglement now
  SURVIVES LONGER THAN IT TAKES TO CREATE, which is the threshold that lets neighbouring
  segments be connected reliably and makes multi-stage repeaters physically possible.**
  ⚠️ **Coverage describes it as "what the field has been waiting for."**
- **⚠️ The same architecture produced a DI-QKD result** (§12 → `qcrypto-security-claims-attacks-and-trusted-nodes`): ⚠️ **1,917 secret key bits
  over 10 km with finite-size security analysis, and a positive asymptotic key rate over
  101 km — reported as extending achievable DI-QKD distance by more than two orders of
  magnitude.** ⚠️ **DI-QKD bases security on measurable quantum correlations rather than
  assumptions about trusted hardware, which directly addresses §11 → `qcrypto-security-claims-attacks-and-trusted-nodes`'s entire attack class.**
- **⚠️ Other 2026 milestones worth knowing:**
```
⚠️ Metropolitan multiplexed repeater with BELL NONLOCALITY certified —
   heralded entanglement between solid-state memories over 14.5 km,
   fidelity 78.6% ± 2.0%, CHSH violation by 3.7σ.
   ⚠️ Reported as the FIRST Bell nonlocality certification at
   metropolitan scale, combining single-photon heralding rates
   with two-photon phase robustness (§16)
⚠️ Multimode storage — entanglement between a telecom photon through
   25.3 km fibre and a stored photon, across 16,340 temporal modes
   (§15's multiplexing requirement)
⚠️ 420 km memory-memory entanglement reported to beat the
   repeaterless channel capacity (§5's bound)
⚠️ New York City — entanglement swapping across three nodes on
   ALREADY-DEPLOYED commercial telecom fibre (NYU, Qunnect, Cisco)
⚠️ Earlier Delft work: heralded entanglement between independently
   operated nodes 10 km apart via 25 km of deployed fibre
```
> **⚠️ GOTCHA — "physics validated" is not "product available," and the sources are
> explicit about this.** ⚠️ **One assessment notes the quantum link efficiency exceeds the
> deterministic threshold and the entanglement fidelity, while above classical bounds, is
> modest.** ⚠️ **Another states plainly that no commercial quantum repeater exists, and that
> programme planning should NOT assume availability on PQC migration timescales of roughly
> 2026–2033.**
> **⚠️ So the correct reading is: a genuine scientific threshold was crossed, the
> engineering runway to a deployable device remains long, and nothing about your
> cryptographic migration plan should change because of it.**

### 24.2 ⚠️ The QKD split: agencies against, Europe investing
**⚠️ The most useful thing to understand before reading any QKD claim, because the
disagreement is real and partly non-technical.**

- **⚠️ THE SCEPTIC CAMP is consistent and hardening** (§20 → `qcrypto-official-position-qrng-quantum-threat-and-choosing`). ⚠️ **NSA concludes
  quantum-resistant cryptography is "more cost effective and easily maintained" than QKD
  and does "not anticipate certifying or approving any QKD" products for national security
  use unless the limitations are overcome.** ⚠️ **NCSC took a 2025 position mirroring it.**
  ⚠️ **ANSSI and BSI reach similar conclusions on maturity and cost.** ⚠️ **CNSA 2.0
  explicitly rejects QKD for NSS, and reporting indicates a DoD memorandum banned it in DoD
  systems outright while setting a 31 December 2030 PQC deadline.**
- **⚠️ EUROPE IS SIMULTANEOUSLY INVESTING**, ⚠️ **treating QKD deployment as a strategic
  priority — which is why the EuroQCI programme and national quantum networks exist
  alongside ANSSI's and BSI's technical scepticism.** ⚠️ **China has invested at
  substantially greater scale** (§17 → `qcrypto-repeaters-memory-entanglement-distribution-and-satellite`, §24.1).
- ⚠️ **These positions are not straightforwardly contradictory. A government can
  simultaneously judge that QKD is not currently the right way to secure its own classified
  traffic AND that it wants domestic capability in a strategically significant technology.**
  **⚠️ Sovereignty, industrial policy and research capacity are legitimate reasons that are
  not security-per-euro arguments — and conflating them is how the debate gets confused.**

> **⚠️ GOTCHA — the criticism most worth internalizing is the DENIAL-OF-SERVICE one,
> because it is structural rather than an implementation flaw** (§20 → `qcrypto-official-position-qrng-quantum-threat-and-choosing`). ⚠️ **QKD's security
> mechanism is refusing to produce key when disturbance is detected — so an attacker who
> injects light to saturate the single-photon detectors cannot read anything AND leaves
> the parties unable to communicate.**
> **⚠️ A security property that converts a confidentiality attack into an availability
> attack is a real trade, not a pure gain.**

**⚠️ How I'd advise reading vendor claims in this space.** ⚠️ **"Unhackable" and "secured by
the laws of physics" are not supportable as stated** (§10 → `qcrypto-security-claims-attacks-and-trusted-nodes`, §11 → `qcrypto-security-claims-attacks-and-trusted-nodes`). ⚠️ **Ask: how is the
classical channel authenticated; how many trusted nodes; decoy states implemented; what
countermeasures against detector blinding and Trojan-horse attacks; is the quoted rate
SECRET key rate with finite-key analysis; and is this offered as defence in depth alongside
PQC or as a replacement for it?** **⚠️ A vendor with good answers to all six is selling
something real and narrower than the brochure.**

---
