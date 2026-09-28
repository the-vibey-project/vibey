---
id: skill-22-wireless-security-339d0f6975
purpose: 22 wireless security
source: src/vibey_tools/skills/plugins/wireless-technologies-and-rf-engineering/skills/wireless-security-coexistence-and-positioning/SKILL.md
requires: []
links: ["skill-23-coexistence-0935160e1d"]
---

## §22. ⚠️ Wireless Security

```
⚠️ ⚠️ THE STRUCTURAL FACT: THERE IS NO PHYSICAL BOUNDARY. ⚠️ An
   attacker need not touch anything. Encryption is not optional
⚠️ WI-FI  ⚠️ WEP broken · WPA2 (⚠️ KRACK, and offline dictionary
   attack on captured handshakes with weak PSKs) → ⚠️ WPA3 with
   SAE, which resists offline attack and gives forward secrecy ·
   ⚠️ OWE encrypts OPEN networks (huge for public Wi-Fi) ·
   ⚠️ 802.1X/EAP for enterprise — ⚠️ and CERTIFICATE VALIDATION
   ON THE CLIENT is the step most often skipped, enabling evil
   twin attacks
⚠️ BLUETOOTH  ⚠️ pairing methods matter: ⚠️ "Just Works" gives NO
   MITM protection · passkey and numeric comparison do ·
   ⚠️ LE Secure Connections (4.2+) uses ECDH — legacy pairing
   does not and is broken. ⚠️ Known attack families: BlueBorne,
   KNOB (key negotiation downgrade), BIAS, and repeated pairing
   flaws
⚠️ ⚠️ RELAY ATTACKS are the deep problem for proximity-implies-
   authorization systems (cars, access control). ⚠️ Signal
   strength CANNOT defend against a relay — only cryptographic
   DISTANCE BOUNDING can (§14, §24, §25.2)
⚠️ NFC/RFID  ⚠️ cloning of weak tags, relay, and skimming (§10)
⚠️ IoT-SPECIFIC FAILINGS  ⚠️ hardcoded and shared keys ·
   unauthenticated firmware update · no key rotation ·
   ⚠️ debug interfaces left enabled in production · secrets
   readable from flash
⚠️ TRAFFIC ANALYSIS AND PRIVACY  ⚠️ MAC randomization exists
   because MAC addresses enabled physical tracking; ⚠️ BLE
   resolvable private addresses do the same, ⚠️ and static
   identifiers in advertising payloads defeat both
```

---
