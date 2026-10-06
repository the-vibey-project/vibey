* **cli:** `vibey -w <command>` (`--workflows`) runs the command on the repository's
  GitHub-hosted runners through `.github/workflows/vibey-remote.yml`. It prints what the
  command printed there and exits with its code. The hub offers the same path at
  `POST /api/v1/workflows/runs` and `GET /api/v1/workflows/runs/{request_id}`, under the new
  deny-by-default `workflows` scope, and refuses commands that reach what the hub never
  offers (ADR-0085).
