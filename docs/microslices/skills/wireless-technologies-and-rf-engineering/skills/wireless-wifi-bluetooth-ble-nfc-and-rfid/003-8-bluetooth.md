---
id: skill-8-bluetooth-6c026af017
purpose: 8 bluetooth
source: src/vibey_tools/skills/plugins/wireless-technologies-and-rf-engineering/skills/wireless-wifi-bluetooth-ble-nfc-and-rfid/SKILL.md
requires: ["skill-7-wi-fi-in-practice-888c8e8ed9"]
links: ["skill-9-ble-programming-c4a14d643e"]
---

## §8. ⚠️ Bluetooth

```
⚠️ ⚠️ TWO DIFFERENT TECHNOLOGIES SHARING A NAME
   ⚠️ BR/EDR ("Classic")  ⚠️ connection-oriented, streaming,
      audio, higher power. ⚠️ 79 channels, 1 MHz, FHSS
   ⚠️ LE (Low Energy)  ⚠️ COMPLETELY DIFFERENT radio and protocol
      stack. ⚠️ 40 channels, 2 MHz, designed around short bursts
      and long sleep. ⚠️ Introduced in 4.0 (2010) — it is not new
⚠️ THE LE STACK  PHY → Link Layer → HCI → L2CAP → ⚠️ ATT → GATT
   → application (§9) · SMP for pairing (§22) · GAP for roles
⚠️ ROLES  ⚠️ advertiser/scanner, then central/peripheral —
   ⚠️ and these are independent of client/server at the GATT layer,
   which confuses newcomers constantly
⚠️ KEY LE FEATURES BY VERSION
   ⚠️ 4.2 privacy and longer packets · ⚠️ 5.0 2M PHY (double rate)
      and CODED PHY (⚠️ long range via FEC, at lower rate) ·
      5.1 direction finding (AoA/AoD) · ⚠️ 5.2 LE AUDIO and the
      LC3 codec · ⚠️ 5.4 PAwR — ⚠️ the protocol that enables
      Auracast · ⚠️ 6.0 Channel Sounding (§25.2)
⚠️ ⚠️ LE AUDIO IS NOT A VERSION NUMBER. ⚠️ The SIG now encourages
   advertising "supports LE Audio" or "supports Auracast" rather
   than a core version, because features and versions decoupled
⚠️ AURACAST  ⚠️ broadcast audio — one source to unlimited
   receivers. ⚠️ Genuinely transformative for hearing aids and
   public venues, and REQUIRES PAwR, so 5.3 and earlier cannot
   participate
⚠️ THE PRACTICAL PARAMETERS  ⚠️ CONNECTION INTERVAL and slave
   latency dominate both latency AND battery life (§19); MTU
   size dominates throughput
```

---
