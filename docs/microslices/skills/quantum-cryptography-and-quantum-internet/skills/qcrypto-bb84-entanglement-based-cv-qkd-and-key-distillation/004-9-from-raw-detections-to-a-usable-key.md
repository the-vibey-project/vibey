---
id: skill-9-from-raw-detections-to-a-usable-key-390c8d1659
purpose: 9 from raw detections to a usable key
source: src/vibey_tools/skills/plugins/quantum-cryptography-and-quantum-internet/skills/qcrypto-bb84-entanglement-based-cv-qkd-and-key-distillation/SKILL.md
requires: ["skill-8-continuous-variable-qkd-b7ea6427bd"]
links: []
---

## §9. ⚠️ From Raw Detections to a Usable Key

> **⚠️ The part popular accounts skip entirely, and it is where most of the actual
> engineering lives.**
```
⚠️ 1. SIFTING  discard basis mismatches (§6)
⚠️ 2. PARAMETER ESTIMATION  measure the QBER (quantum bit error
   rate). ⚠️ ALL errors must be attributed to the eavesdropper,
   because you cannot distinguish an attacker from a noisy fibre
⚠️ 3. ERROR RECONCILIATION  ⚠️ classical error correction over the
   public channel (Cascade, LDPC). ⚠️ This LEAKS information, and
   the leak must be accounted for in step 4
⚠️ 4. ⚠️ PRIVACY AMPLIFICATION  compress the corrected key with a
   universal hash so that the eavesdropper's partial knowledge is
   reduced to negligible. ⚠️ You throw away bits to buy secrecy
⚠️ 5. ⚠️ AUTHENTICATION of the classical channel — ⚠️ SEE §10
⚠️ THE RESULT  ⚠️ the final secret key is much shorter than the raw
   detections. ⚠️ Quoted "key rates" should always be SECRET key
   rate after all of this, and marketing sometimes quotes raw
```
**⚠️ Finite-key effects matter**: ⚠️ **asymptotic security proofs assume infinitely long
keys; real finite blocks require a stricter analysis and yield less key.** ⚠️ **A system
quoting asymptotic rates is quoting an upper bound it never achieves.**
