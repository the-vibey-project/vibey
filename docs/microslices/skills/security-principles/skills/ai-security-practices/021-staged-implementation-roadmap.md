---
id: skill-staged-implementation-roadmap-19c96234f0
purpose: staged implementation roadmap
source: src/vibey_tools/skills/plugins/security-principles/skills/ai-security-practices/SKILL.md
requires: ["skill-observability-for-security-90d8f12867"]
links: ["skill-the-first-rule-517515289e"]
---

## Staged Implementation Roadmap

### Stage 1 — This Week (Stop Active Bleeding)
1. **Patch Next.js/React** to current patched versions; strip `x-middleware-subrequest` at proxy/WAF; confirm no auth relies solely on middleware — verify with CVE-2025-29927 / CVE-2025-66478 detection templates
2. **Turn on secret scanning** (Gitleaks/detect-secrets) as pre-commit + CI gate; rotate any exposed AI keys; move to project/workspace-scoped keys; set provider spend caps
3. **Add token-aware rate limiting + `max_tokens` + spend alerts** to every LLM endpoint

### Stage 2 — This Quarter (Build the Baseline)
4. Wire **SAST + SCA + DAST** into CI as blocking gates; pin deps with hashes and Actions to SHA; generate SBOMs; sign artifacts with cosign (SLSA L2)
5. Stand up a **guardrail layer** (NeMo Guardrails or LLM Guard + Llama Guard 3) with input/retrieval/execution/output rails; enforce Pydantic/Zod schemas on all model output
6. For **RAG:** authenticate document sources, strip hidden text on ingest, enforce per-tenant isolation at the DB layer, encrypt the vector store
7. **Mandate human review gates** and "rule files" for AI-assisted PRs

### Stage 3 — This Year (Mature the Program)
8. Adopt **NIST AI RMF** + map to the Cyber AI Profile and ISO 42001; maintain an AI/Agent inventory with named owners
9. **Sandbox all agents** (Firecracker/gVisor), enforce least-privilege tool scoping, default-deny secret reads, egress allow-lists, human approval for high-impact actions
10. Move secrets to a manager with dynamic/short-lived credentials (Vault) or OIDC federation (Anthropic WIF, OpenAI service accounts); rotate on 90-day cadence

### Thresholds That Change the Plan
- Any agent with write/financial/PII access → require sandbox + human-in-the-loop before launch
- LLM spend variance >X% week-over-week → tighten token quotas
- Any unauthenticated public endpoint → WAF + rate limit mandatory
- SAST/SCA HIGH/CRITICAL finding → block deploy

---
