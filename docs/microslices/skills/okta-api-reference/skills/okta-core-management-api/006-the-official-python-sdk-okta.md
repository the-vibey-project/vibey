---
id: skill-the-official-python-sdk-okta-6479b7c855
purpose: the official python sdk okta
source: src/vibey_tools/skills/plugins/okta-api-reference/skills/okta-core-management-api/SKILL.md
requires: ["skill-system-log-polling-pattern-b38a44e25d"]
links: ["skill-practical-guidance-f383c12129"]
---

## The official Python SDK — `okta`

- **Install**: `pip install okta`. **Do not confuse this with `okta-sdk-python` (hyphenated) on
  PyPI** — that is an inactive community fork (last release 0.2.1 as of the source this was
  distilled from) and is not the maintained package. The maintained package name is `okta`.
- **Version snapshot** (verify current values on PyPI before relying on them — this package ships
  frequent regens): the source this skill was distilled from recorded the latest release as
  **3.4.2**, dated **April 15, 2026**, with a PyPI dependency specifier of **`Python >=3.10`**.
  Watch for drift between docs and package metadata here: some older GitHub README/contributor docs
  reference "Python 3.9+" while the live PyPI specifier on 3.4.2 requires 3.10+ — trust the installed
  package's actual `Requires-Python` metadata over prose docs if the two disagree.
- **Repository**: `github.com/okta/okta-sdk-python`, Apache-2.0, maintained by Okta.
- **Architecture (v3.x)**: a breaking rewrite from v2.x. The SDK's own CHANGELOG states: "The SDK
  has been regenerated using the v5.1.0 Okta Management OpenAPI specifications, bringing support
  for new endpoints and enhanced functionality across the API surface." The generation toolchain is
  named explicitly in Okta's contributor guide (`developer.okta.com/code/contribute-sdk/`):
  "OpenAPI Generator: openapi-generator-cli version 7.7.0." Models moved from a custom `OktaObject`
  base class to Pydantic `BaseModel` subclasses; modules moved from `okta/resource_clients/` to
  `okta/api/`. Every list method returns a `(data, response, error)` tuple, with `_with_http_info`
  variants available when you need raw response headers (e.g. to read `X-Rate-Limit-Remaining`
  yourself).
- **Coverage**: the Okta **Management** API surface only — Users, Groups, Apps, Policies,
  Factors/Authenticators, System Log, Devices, Brands, Authorization Servers, etc.
- **Auth support**: SSWS token (`config={'orgUrl': ..., 'token': ...}`) or OAuth 2.0 Private Key JWT
  — but the SDK's own README states this OAuth support is **only for service-to-service
  applications** (verbatim: "This SDK supports this feature (OAuth 2.0) only for service-to-service
  applications."). It does not implement user-context OAuth flows (authorization code, etc.) — for
  those, use the Sign-In Widget or AuthJS instead.
- **Known gaps** (verify current status before relying on the absence of these — SDKs evolve):
  - Does **not** wrap the Identity Governance (`/governance/api/v1|v2`) endpoints — separate OpenAPI
    spec, separate URL prefix. See `okta-iga-governance-api` for that surface.
  - Does not cover the legacy Authentication (`/api/v1/authn`) primary-auth flows as a first-class
    citizen — those are typically driven through the Sign-In Widget or AuthJS instead.
  - Coverage of newly released Management endpoints lags spec releases until the SDK's next
    regeneration/release cycle.
  - A separately-named PyPI package, **`okta-sdk-python`** (with hyphens), exists and is an
    inactive community fork (last release 0.2.1) — do not use it; the supported package is `okta`.
