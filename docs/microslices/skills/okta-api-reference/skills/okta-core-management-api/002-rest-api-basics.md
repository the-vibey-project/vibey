---
id: skill-rest-api-basics-bf4d5132a1
purpose: rest api basics
source: src/vibey_tools/skills/plugins/okta-api-reference/skills/okta-core-management-api/SKILL.md
requires: ["skill-coverage-snapshot-7f23fb0db5"]
links: ["skill-authentication-two-schemes-5575d8bc28"]
---

## REST API basics

- **Base URL pattern**: `https://{yourOktaDomain}/api/v1/{resource}`. `{yourOktaDomain}` is a
  tenant-specific subdomain, e.g. `integrator-1234567.okta.com` (free developer orgs) or
  `acme.okta.com` / `acme.oktapreview.com` / `acme.okta-emea.com` in production. All requests must be
  HTTPS.
- The API is versioned and uses HAL/JSON hypermedia (`_links` for navigation) — see
  `developer.okta.com/docs/reference/core-okta-api/`.
- **Pagination**: cursor-based via an `after` query parameter (`limit` up to 200). Always follow the
  response's `Link` header for the next page rather than constructing your own `since`/`until` or
  offset URLs — this is true for both general resource listing and System Log polling.
- **Rate limiting**: 429 responses include an `X-Rate-Limit-Reset` header. Well-behaved clients also
  watch the `X-Rate-Limit-Remaining` header on every response and back off before hitting 429,
  rather than only reacting after the fact.
