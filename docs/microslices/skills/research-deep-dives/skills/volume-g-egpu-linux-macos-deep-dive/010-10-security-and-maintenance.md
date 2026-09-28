---
id: skill-10-security-and-maintenance-c340490a33
purpose: 10 security and maintenance
source: src/vibey_tools/skills/plugins/research-deep-dives/skills/volume-g-egpu-linux-macos-deep-dive/SKILL.md
requires: ["skill-9-cost-model-093841fb62"]
links: ["skill-11-decision-matrix-ff18b33204"]
---

## 10. Security and maintenance

An eGPU is a high-value DMA-capable peripheral in a physical security model. Thunderbolt security, IOMMU behavior, firmware, kernel policy, device authorization, and physical access matter. Keep host firmware, OS, drivers, and enclosure firmware current, but do not update production systems without rollback and recovery planning.

For research or production:

- pin known-good driver/runtime versions;
- record firmware and BIOS settings;
- maintain a known-good kernel;
- keep backups and recovery media;
- test after OS updates;
- restrict untrusted physical access;
- monitor crashes, GPU resets, thermal throttling, and data corruption;
- treat vendor download and package provenance as part of the supply chain.
