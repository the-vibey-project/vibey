---
id: skill-3-apple-imessage-the-post-quantum-pacesetter-3c0dc9effc
purpose: 3 apple imessage the post quantum pacesetter
source: src/vibey_tools/skills/plugins/private-chat-engines/skills/chat-the-wider-field/SKILL.md
requires: ["skill-2-whatsapp-the-default-e2ee-of-the-planet-now-partially-pried-open-3a3336804e"]
links: ["skill-4-threema-the-swiss-paid-model-now-under-new-ownership-a84a5d480c"]
---

## 3. Apple iMessage — the post-quantum pacesetter

**PQ3**, announced Feb 2024 ([Apple Security Research](https://security.apple.com/blog/imessage-pq3))
and standard between up-to-date devices since, did the thing Signal hadn't yet done: hybrid
ECC+PQ in the *initial* establishment (Kyber/ML-KEM-1024) **and** ongoing PQ rekeying (Kyber-768
roughly every 50 messages, at least weekly), with classical ECDSA authentication. Apple's level
0–3 taxonomy is now the field's shared vocabulary. Apple's 2025–26 OS generation extended
quantum-safe crypto across TLS/VPN/SSH/CryptoKit ([Apple Platform Security guide](https://support.apple.com/guide/security/quantum-secure-cryptography-apple-devices-secc7c82e533/web)).
Caveats that keep iMessage out of most threat-model recommendations: proprietary stack, iCloud
backups historically undermined E2EE (ADP helps; in Feb 2025 Apple pulled ADP from the UK under
a Home Office order — the restoration state post the UK's reported August 2025 climbdown is
**flagged, not verified**), no Android, closed federation, no operator story whatsoever.
Contact Key Verification (2023) was a genuinely good key-transparency step.
