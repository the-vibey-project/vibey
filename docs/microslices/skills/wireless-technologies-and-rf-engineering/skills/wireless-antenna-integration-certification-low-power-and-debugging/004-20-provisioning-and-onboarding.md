---
id: skill-20-provisioning-and-onboarding-989600fcb7
purpose: 20 provisioning and onboarding
source: src/vibey_tools/skills/plugins/wireless-technologies-and-rf-engineering/skills/wireless-antenna-integration-certification-low-power-and-debugging/SKILL.md
requires: ["skill-19-low-power-design-694d5e4610"]
links: ["skill-21-rf-debugging-9b346ccab2"]
---

## §20. Provisioning and Onboarding

**⚠️ The genuinely hard UX problem in wireless products**: ⚠️ **how does a device with no
screen and no keyboard join a network whose credentials it doesn't have?**
**⚠️ The approaches**: ⚠️ **SoftAP (device becomes an AP, phone joins, hands over
credentials); BLE provisioning (⚠️ now the most common, because the phone has BLE anyway);
⚠️ WPS (deprecated — the PIN mode was badly broken); Wi-Fi Easy Connect / DPP (QR-code
based, the modern answer); ⚠️ NFC tap (§10 → `wireless-wifi-bluetooth-ble-nfc-and-rfid`); and out-of-band methods including
light-flicker and audio.**
**⚠️ Matter's commissioning flow** uses a QR or numeric code with a certificate chain
(§11 → `wireless-thread-matter-lora-cellular-uwb-and-choosing`).
**⚠️ The security requirements** are easy to get wrong: ⚠️ **credentials must not be
transmitted in clear, the provisioning window must close, and the DEVICE must be
authenticated too — many products authenticate only in one direction.**
**⚠️ Factory reset and re-provisioning** must exist and be discoverable, ⚠️ **and ownership
transfer is a real requirement people forget until a device is resold.**

---
