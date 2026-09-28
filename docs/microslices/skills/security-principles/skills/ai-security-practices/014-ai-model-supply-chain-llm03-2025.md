---
id: skill-ai-model-supply-chain-llm03-2025-0f0cf804e1
purpose: ai model supply chain llm03 2025
source: src/vibey_tools/skills/plugins/security-principles/skills/ai-security-practices/SKILL.md
requires: ["skill-typescript-next-js-security-patterns-29d8bad069"]
links: ["skill-supply-chain-security-sbom-sigstore-provenance-cfd3213d9f"]
---

## AI Model Supply Chain (LLM03:2025)

### Threats
- Malicious weights, pickle-based RCE (PickleScan bypasses: CVE-2025-10156 CRC differential, CVE-2025-10157 subclass substitution — single scanners insufficient)
- Poisoned training data
- Real incidents: Ultralytics compromise (Dec 2024, ~80M downloads/mo), LiteLLM supply-chain compromise, Langflow code injection (CVE-2025-3248)

### Controls
- Prefer **safetensors** over pickle
- Allow-lists not block-lists for model file types
- Hash verification before loading
- Sandboxed model loading
- Update PickleScan ≥0.0.31
- Generate **AI-BOMs** (OWASP AIBOM generator)

---
