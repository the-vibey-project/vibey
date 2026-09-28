---
id: skill-encryption-eb57256b0d
purpose: encryption
source: src/vibey_tools/skills/plugins/software-architecture/skills/architecture-patterns/SKILL.md
requires: ["skill-iam-oauth-2-0-flows-3d72903975"]
links: ["skill-etl-vs-elt-a0c0cb6803"]
---

## Encryption
- **At rest**: Storage SSE (PMK default, CMK via Key Vault), Azure Disk Encryption, **TDE** for Azure SQL
- **In transit**: TLS 1.2/1.3
- **Envelope encryption**: DEK wrapped by KEK; rotate without downtime by supporting two active key versions
- **CMK vs PMK**: CMK gives data sovereignty but adds Key Vault dependency to every read/write path

---

# PART 11: DATA PIPELINE ARCHITECTURES
