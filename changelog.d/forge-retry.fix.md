- **Delivery estimate:** the hourly issue triage no longer fails on a transient GitHub error. A
  `504 Gateway Timeout` or GraphQL "Something went wrong" on one label edit is asked again, up to
  three times with backoff (`[forge_retry]` in `.vibey-gh.toml`); any other error still fails the
  job, as it did.
