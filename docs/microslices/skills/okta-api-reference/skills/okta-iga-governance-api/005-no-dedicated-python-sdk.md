---
id: skill-no-dedicated-python-sdk-36924bd4aa
purpose: no dedicated python sdk
source: src/vibey_tools/skills/plugins/okta-api-reference/skills/okta-iga-governance-api/SKILL.md
requires: ["skill-availability-caveats-f3f88ab983"]
links: ["skill-alternatives-to-a-python-sdk-b095bb780d"]
---

## No dedicated Python SDK

There is no `okta-iga`, `okta-governance`, or equivalently-named package on PyPI (official or
community, as of the source this was distilled from). The official `okta` Python package (see
`okta-core-management-api`) is generated from the Management OpenAPI spec (`management.yaml`), which
does not declare any `/governance/api/...` paths. Two practical options for calling this API from
Python:

1. Drop to the SDK's underlying request executor / HTTP transport (effectively raw HTTP), reusing
   only its OAuth token-acquisition machinery.
2. Bypass the SDK entirely: use `httpx` or `requests` with your own client-credentials JWT exchange
   against `/oauth2/v1/token`, then call `/governance/api/v1|v2/...` directly with the resulting
   bearer token. This is the pattern Okta's own documentation demonstrates — every IGA example in
   Okta's docs uses raw `curl`, never SDK calls.

### Practical pattern

Use a library like `authlib`, or a hand-rolled JWT assertion, to perform the client-credentials
exchange, then make direct calls, e.g.:

```
requests.get(
    f"{org}/governance/api/v1/campaigns",
    headers={"Authorization": f"Bearer {token}"},
)
```
