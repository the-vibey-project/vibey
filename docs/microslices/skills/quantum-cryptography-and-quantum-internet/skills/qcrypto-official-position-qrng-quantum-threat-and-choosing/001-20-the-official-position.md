---
id: skill-20-the-official-position-7bcc15f1a1
purpose: 20 the official position
source: src/vibey_tools/skills/plugins/quantum-cryptography-and-quantum-internet/skills/qcrypto-official-position-qrng-quantum-threat-and-choosing/SKILL.md
requires: []
links: ["skill-21-quantum-random-number-generation-0d13076d04"]
---

## §20. ⚠️ The Official Position

> **⚠️ The most important section for anyone evaluating a QKD procurement, and it is
> strikingly consistent across the anglophone agencies while Europe diverges** (§24.2 → `qcrypto-reference`).
**⚠️ The NSA's published position** identifies five limitations and concludes it does not
recommend QKD for national security systems.
```
⚠️ THE FIVE NSA LIMITATIONS, in substance
   ⚠️ 1. ⚠️ PARTIAL SOLUTION — QKD supplies keying material for
      confidentiality but ⚠️ CANNOT AUTHENTICATE ITS OWN
      TRANSMISSION SOURCE, so authentication requires asymmetric
      cryptography or pre-placed keys anyway (§10)
   ⚠️ 2. SPECIAL-PURPOSE EQUIPMENT — dedicated fibre or managed
      free-space transmitters; cannot be a software upgrade
   ⚠️ 3. Significant infrastructure and maintenance cost
   ⚠️ 4. ⚠️ IMPLEMENTATION SECURITY — the theory-device gap (§11)
   ⚠️ 5. ⚠️ DENIAL OF SERVICE — the quantum channel is trivially
      disruptable, and detecting an "eavesdropper" means REFUSING
      TO PRODUCE KEY, so an attacker who cannot read can still
      stop you communicating
```
**⚠️ The UK NCSC is equally direct**: ⚠️ **it "will not support the use of QKD for
government or military applications," endorses PQC as the best mitigation, and makes the
structural point plainly — QKD does not provide authentication, nor do any other quantum
techniques, so it must be combined with other cryptographic services and "should not be
relied on as a mechanism that provides substantial security value."** ⚠️ **For other
sectors it recommends QKD should not be solely relied upon.**
**⚠️ France's ANSSI** concludes QKD is usable "only in some niche use cases," is "not yet
sufficiently mature from a security perspective," and that the clear priorities should be
migration to PQC and/or adoption of symmetric keying. ⚠️ **Germany's BSI has published in
similar terms, with cost cited as a primary barrier.**
**⚠️ In the US this has hardened into policy**: ⚠️ **CNSA 2.0 explicitly rejects QKD for
national security systems, NSA advises agencies not to invest in or deploy QKD without
direct consultation, and reporting indicates a DoD PQC migration memorandum explicitly
BANNED QKD in DoD systems.**
> **⚠️ GOTCHA — read this as a genuine technical disagreement, not a settled fact, because
> the QKD community has responded substantively.** ⚠️ **A published rebuttal by Swiss
> researchers argues some NSA objections don't hold and others are expected to be resolved
> as cheaper optics and quantum repeaters arrive — explicitly framing the assessment as
> depending on which technological epoch you assume.**
> ⚠️ **And the NCSC's non-endorsement is reportedly not framed as permanent, with quantum
> repeaters cited as the development that would most change the assessment** (§14 → `qcrypto-repeaters-memory-entanglement-distribution-and-satellite`, §24.1 → `qcrypto-reference`).
> **⚠️ Verify current wording against the source documents rather than any paraphrase —
> including mine.**

---
