---
id: skill-backend-data-tier-d767de03b8
purpose: backend data tier
source: src/vibey_tools/skills/plugins/mobile-development/skills/mobile-azure-deployment/SKILL.md
requires: ["skill-intune-mdm-mam-3fa4205cc1"]
links: ["skill-ci-cd-after-app-center-retired-march-31-2025-49e257290b"]
---

## Backend & data tier

- **Azure API Management** as the mobile gateway (throttling, policies, **JWT validation**,
  developer portal).
- Hosting on **AKS** (ingress, TLS termination) or **Azure Container Apps** (serverless
  scale-to-zero, built-in **Dapr** `1.13.x-msft`, **Easy Auth** built-in).
- **Azure Static Web Apps** (Standard) serves PWA/hybrid content and links a backend under `/api`
  (no CORS; pass-through `X-MS-CLIENT-PRINCIPAL` auth).
- **Cosmos DB** for data: partition strategy; **change feed** (always returns the full document —
  foundational for offline sync); multi-region conflict resolution (**LWW** default on `_ts`, or a
  **Custom merge stored procedure** — NoSQL API only; patch resolves at path level).
- **Azure SignalR** for realtime; **Azure CDN** for assets; **Functions** for event-driven
  endpoints; **Private Endpoints / NSGs / Azure Firewall** for network isolation.
