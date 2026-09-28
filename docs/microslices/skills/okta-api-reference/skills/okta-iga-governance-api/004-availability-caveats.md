---
id: skill-availability-caveats-f3f88ab983
purpose: availability caveats
source: src/vibey_tools/skills/plugins/okta-api-reference/skills/okta-iga-governance-api/SKILL.md
requires: ["skill-resource-surface-c9671154fe"]
links: ["skill-no-dedicated-python-sdk-36924bd4aa"]
---

## Availability caveats

- OIG is a **paid subscription add-on** — the API is generally available on both Preview and
  Production for subscribed customers, but individual endpoints (Collections, some V2 Access
  Request features) may still be in Beta.
- Several capabilities are additionally gated by feature flags on top of the subscription. The
  source this was distilled from names: Realms, Resource Collections, Govern Okta Admin Roles,
  Bidirectional Group Management for AD, Campaign types, Slack notifications, Security Access
  Reviews, and the Unified Requester Experience. A 404 or 403 on a documented endpoint can mean
  "feature not enabled for this org," not necessarily a bug in calling code — check
  feature-flag/subscription state before assuming an integration defect.
- Historically, V2 Access Request APIs did **not** accept the `client_credentials` grant (tracked
  under internal Okta issue IDs referenced as OKTA-1044065 / OKTA-926552 in Okta's 2025 release
  notes). Test `client_credentials` against your specific org and API version before depending on
  it for service-to-service access-request automation — this may or may not still apply depending
  on when it shipped relative to your org's release train.
