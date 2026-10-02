- **Fix:** `vibey-gh issue-triage` asks GitHub again after a transient failure instead of failing
  the hourly sweep: a `502`, `503` or `504`, GraphQL's "Something went wrong while executing your
  query", or a secondary rate limit that carries `Retry-After`. Up to three retries, backing off
  from 5 seconds; each one is announced on stderr, and every other failure fails exactly as it
  did. The new `[forge_retry]` table configures all of it. `GhTransport` takes the policy as an
  opt-in `retry`, for calls that are safe to repeat; without one it runs each call once, as before.
