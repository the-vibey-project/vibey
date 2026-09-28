---
id: skill-practical-guidance-9ab950a8a0
purpose: practical guidance
source: src/vibey_tools/skills/plugins/okta-api-reference/skills/okta-iga-governance-api/SKILL.md
requires: ["skill-alternatives-to-a-python-sdk-b095bb780d"]
links: []
---

## Practical guidance

1. Before building any IGA integration, confirm the target org actually has the OIG subscription and
   the specific feature flags for the resources you need (Collections, V2 Access Requests, Realms,
   etc.) — don't assume parity with the base Management API's availability.
2. Do not search for an official Python SDK for governance endpoints — none exists as of this
   snapshot. Plan for either raw HTTP or the Terraform provider from the start, rather than
   discovering the gap mid-project.
3. If service-to-service (`client_credentials`) access to V2 Access Request endpoints is required,
   validate it against the specific org and API version early — this has been a historically
   inconsistent area.
4. Remember OIG is OAuth-only: any design that assumes SSWS-token access will work "the same way it
   does for core Okta" will fail for governance endpoints specifically.
