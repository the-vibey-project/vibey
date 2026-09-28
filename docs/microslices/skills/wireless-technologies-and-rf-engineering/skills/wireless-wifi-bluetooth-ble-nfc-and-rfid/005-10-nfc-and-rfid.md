---
id: skill-10-nfc-and-rfid-15098ee9bb
purpose: 10 nfc and rfid
source: src/vibey_tools/skills/plugins/wireless-technologies-and-rf-engineering/skills/wireless-wifi-bluetooth-ble-nfc-and-rfid/SKILL.md
requires: ["skill-9-ble-programming-c4a14d643e"]
links: []
---

## §10. ⚠️ NFC and RFID

```
⚠️ ⚠️ NFC IS NOT RADIO IN THE USUAL SENSE. ⚠️ At 13.56 MHz over
   centimetres you are in the NEAR FIELD — this is INDUCTIVE
   COUPLING, essentially a loosely coupled transformer, not
   propagating waves. ⚠️ Field strength falls off far faster than
   1/r², which is precisely what makes it short-range BY PHYSICS
   rather than by power limit
⚠️ ⚠️ PASSIVE TAGS HAVE NO BATTERY — ⚠️ the reader's field powers
   them, and the tag replies by LOAD MODULATION (changing its
   own impedance so the reader sees the change). Elegant, and
   the reason tags cost cents
⚠️ THE STANDARDS  ⚠️ ISO 14443 (A/B — the payment and access
   card standard) · ISO 15693 (vicinity, longer range) ·
   FeliCa · ⚠️ NFC Forum tag types 1-5 and NDEF as the data format
⚠️ NFC MODES  ⚠️ reader/writer · card emulation (⚠️ HCE — how
   phone payments work) · peer-to-peer (largely deprecated)
⚠️ RFID BY FREQUENCY  ⚠️ LF 125 kHz (short, penetrates water and
   tissue — animal tags) · HF 13.56 MHz · ⚠️ UHF 860-960 MHz
   (⚠️ FAR FIELD backscatter, metres of range, bulk inventory
   reading — and REGION-SPECIFIC frequencies, §5)
⚠️ ⚠️ THE PRACTICAL FAILURE MODES  ⚠️ METAL DETUNES AND SHIELDS —
   a tag on metal needs an on-metal design with a spacer ·
   ⚠️ multiple cards in a wallet collide · antenna size sets range
   more than power does
⚠️ SECURITY  ⚠️ MIFARE Classic's Crypto1 is thoroughly broken and
   still widely deployed · ⚠️ relay attacks are the structural
   weakness of proximity-implies-presence (§22, §24)
```
