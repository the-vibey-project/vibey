---
id: skill-quirk-7-1-card-level-retry-only-fires-on-http-429-and-504-in-connector-builder-3e0d3ea23f
purpose: quirk 7 1 card level retry only fires on http 429 and 504 in connector builder
source: src/vibey_tools/skills/plugins/okta-workflows/skills/okta-workflows-error-handling/SKILL.md
requires: []
links: ["skill-quirk-7-2-custom-retry-status-codes-via-list-construct-19da3d36fb"]
---

## Quirk 7.1 — Card-level retry ONLY fires on HTTP 429 (and 504 in Connector Builder)

"Retries for cards in flows only take place as a result of HTTP 429 Too Many Requests errors. You
can't set error handling for other HTTP errors." Default Retry is 0 times; default After is 5 minutes;
Then options are Halt Flow / Return Values / Run another Flow. In Connector Builder, the default is
"retry on 429 and 504… three times between one and three seconds." For non-429 retries you must use an
If Error block.

- *Sources:* set-error-handling.htm; best-practices-rate-limits.htm
