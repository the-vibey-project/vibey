---
id: skill-secrets-management-for-ai-services-7902448662
purpose: secrets management for ai services
source: src/vibey_tools/skills/plugins/security-principles/skills/ai-security-practices/SKILL.md
requires: ["skill-mcp-security-new-under-secured-layer-baec8d2947"]
links: ["skill-denial-of-wallet-llm10-2025-unbounded-consumption-0370c770f1"]
---

## Secrets Management for AI Services

### The Scale of the Problem
GitGuardian State of Secrets Sprawl 2026 (March 2026):
- 28.65 million new hardcoded secrets added to public GitHub commits in 2025 (+34% YoY, largest single-year jump)
- AI-assisted commits leak secrets at **3.2%** vs 1.5% GitHub-wide baseline
- 1,275,105 AI service secrets detected in 2025 (+81% over 2024)
- 8 of 10 fastest-growing detector categories tied to AI services
- ~113,000 leaked DeepSeek API keys as one example

### OpenAI Key Management
- Use **project-scoped keys** (`sk-proj-` prefix, replaces legacy org-wide `sk-` keys since April 2024)
- Use **service account keys** for CI/agents
- Separate **Admin key** for the management API
- RBAC at org/project level; IP allowlisting
- **Ephemeral Realtime client secrets** for browser sessions (never expose long-lived keys client-side)
- On compromise: rotate immediately from the API Keys page

### Anthropic Key Management
- Keys (`sk-ant-`) are **workspace-scoped**
- **Admin API keys** (`ANTHROPIC_ADMIN_KEY`) for management — org-admin only
- **Workload Identity Federation:** exchanges OIDC tokens for short-lived `sk-ant-oat01-` tokens (default 3,600s, min 60s) — no `ANTHROPIC_API_KEY` secret to create, store, or rotate
- Official guidance: rotate keys ~every 90 days; set usage/spend limits as a safeguard

### Secrets Managers
| Tool | Approach | Notes |
|---|---|---|
| **HashiCorp Vault** | True dynamic/short-lived secrets | BSL license; acquired by IBM 2025 |
| **AWS Secrets Manager / Azure Key Vault / GCP Secret Manager** | Managed, scheduled rotation | Cloud-native |
| **Doppler** | SaaS secrets sync | Developer-friendly |
| **Infisical** | MIT, self-hostable | Open-source option |

Never store AI keys client-side — route through a server-side proxy.

### Python Implementation
- **pydantic-settings** (`BaseSettings` + `SettingsConfigDict(env_file=...)` with `SecretStr` and `.get_secret_value()`; supports `secrets_dir` for Docker secrets)
- **python-dotenv** (does not override existing env vars by default)
- Add `.env` to `.gitignore` on day one; ship `.env.example`
- Pre-commit hooks: **detect-secrets** / **Gitleaks** / **TruffleHog**

### Next.js Implementation
- Only `NEXT_PUBLIC_`-prefixed vars reach the browser (inlined at build time) — never put secrets there
- Access `process.env` only in a server-only Data Access Layer (`import 'server-only'`)
- React **taint APIs** (`experimental_taintObjectReference`/`taintUniqueValue`) prevent accidental client exposure
- Post-build: grep `.next/static/chunks` for leaked secrets

---
