---
id: skill-system-log-polling-pattern-b38a44e25d
purpose: system log polling pattern
source: src/vibey_tools/skills/plugins/okta-api-reference/skills/okta-core-management-api/SKILL.md
requires: ["skill-resource-surface-representative-not-exhaustive-4fb4c4d7ab"]
links: ["skill-the-official-python-sdk-okta-6479b7c855"]
---

## System Log polling pattern

The canonical, safe way to consume the System Log for near-real-time event ingestion:

- `GET /api/v1/logs?after={cursor}`, always in ascending order.
- Follow the response's `Link` header for continuation — never hand-construct `since`/`until` query
  parameters, since Okta's own guidance and real-world integrations both treat `Link`-header
  following as the only supported pagination contract for this endpoint.
- Persist the cursor after every processed batch (not just at the end of a run) so that a crash or
  restart resumes exactly where it left off rather than skipping or re-processing events.
- Okta may return up to 1,000 events per page.
