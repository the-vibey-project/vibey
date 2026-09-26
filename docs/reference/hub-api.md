# Hub API reference

The hub is `vibey serve` ([ADR-0068](../architecture/decisions/0068-the-hub.md)): one HTTP
API that every Krypton client -- desktop, mobile, web, the VS Code extension -- reaches.
Version 1. The machine-readable contract is the OpenAPI 3.1 document, committed at
[`docs/reference/hub-api.json`](https://github.com/the-vibey-project/vibey/blob/main/docs/reference/hub-api.json)
and served by a running hub at `/api/v1/openapi.json`. A test fails when the two differ, so
the file is always the truth.

## One contract with the CLI

Every document the hub returns is the one the matching command prints with `--json`, from
the same presenter, so a client reads the same keys whichever way it asks:

| Route | Same document as |
|---|---|
| `GET /api/v1/projects` | `vibey projects --json` |
| `GET /api/v1/projects/{project_id}/status` | `vibey status PROJECT_ID --json` |
| `GET /api/v1/gates[?project_id=…]` | `vibey gates [PROJECT_ID] --json` |
| `GET /api/v1/projects/{project_id}/budget` | `vibey budget show PROJECT_ID --json` (read only) |
| `GET /api/v1/projects/{project_id}/queue` | `vibey queue list PROJECT_ID --json` |
| `POST /api/v1/projects/{project_id}/queue/{job_id}/bump` | `vibey queue bump JOB_ID --json` |
| `GET /api/v1/projects/{project_id}/ledger?text=&kind=&actor=&limit=` | `vibey ledger search … --json` |
| `GET /api/v1/loops` | `vibey loops --json` |

Three routes have no single command behind them:

- `POST /api/v1/gates/{gate_id}/answer` takes `{"answer": {...}, "request_id": "…"}`,
  where `answer` is what `vibey answer --raw` takes. It answers through the same service as
  `vibey answer`: once, recorded under the caller's name. The same `request_id` with the
  same answer is a no-op (`"replayed": true`); a gate another request answered first is 409.
- `GET /api/v1/lanes` lists the lanes on this computer, each with its byte `offset`.
- `GET /api/v1/doctor` runs the checks the hub can run itself (the database, `hub-exposure`)
  and says so; `vibey doctor` on the host is the full check.

`GET /health/live` and `GET /health/ready` need no credentials and say only whether the
process is up and whether the database answers. `GET /api/metrics` returns
`vibey_bootstrap`'s metrics snapshot and needs `view`.

## Live

A ledger feed resumes from a **position**, never a time (sub-doctrine 10.g): the last
`seq` a client has. Every ledger append announces itself on the database channel
`vibey_ledger_appended` (migration 0019), and the hub reads every event after the last
seq it sent, so an announcement that is missed costs latency, never an event.

| Route | What it does |
|---|---|
| `WS /api/v1/projects/{project_id}/live?after=N` | Sends `{"project_id", "events", "last_seq"}` pages of events with seq > N, up to 200 at a time until caught up, then one page per append. A quiet feed sends `{"heartbeat": last_seq}` every 25 s. |
| `GET /api/v1/projects/{project_id}/ledger/after?seq=N&limit=L` | The same page, for a client that polls. |
| `WS /api/v1/lanes/live?path=P&after=B` | A listed lane's complete lines after byte B, as `{"events_path", "from", "offset", "lines"}`, checked every second. Resume from `offset`. |
| `GET /api/v1/lanes/tail?path=P&after=B` | The same, once. |

`path` must be the `events_path` of a lane `GET /api/v1/lanes` lists; any other path is
404, and nothing else is ever opened. A WebSocket is refused (close code 1008) when its
`Host` or `Origin` is not one the hub answers, or it proves no principal; and the
principal is checked again before every page, so one revoked while a feed is open is cut
off at its next message. Events are carried exactly as `vibey ledger search --json`
carries them.

## Who may do what

Every `/api/v1` route and `/api/metrics` needs a principal. On the host, that is the host
token: `Authorization: Bearer <content of <state_dir>/token>`, which holds every scope.
A paired device instead signs every request (see [Pairing](#pairing)) and holds only the
scopes the host granted it.

| Scope | Permits |
|---|---|
| `view` | Every read above. |
| `answer` | Answering a gate that does not spend. |
| `spend` | Answering a gate that does (`budget_exhausted`, the `deploy_*` gates), with `answer`. |
| `run` | Reserved for starting and stopping work; no route uses it yet. |
| `bump` | Bumping a job -- and only when the project's `[queue.priority] sources` admits `vibey-hub`. |

Nothing is permitted without a scope. And no scope, ever, can declare paid use, lift or
change a cap, change the database DSN, run migrations or touch the canon: no route offers
them.

## Pairing

Only the host pairs, lists and revokes; a device never can, not even for itself.

| Route | Who | What |
|---|---|---|
| `POST /api/v1/pairing/offers` `{"scopes": [...]}` | host | A 6-digit code, valid 120 seconds and spent by the first claim, with the pairing URI `vibey-pair://<host>:<port>?fp=<sha256>&code=<code>&v=1` the QR code carries. At least one scope. |
| `POST /api/v1/pairing/claim` `{"code", "name"}` | anyone | The device's id, its key (returned this once) and scopes. Rate-limited per address; five wrong codes withdraw every open offer. |
| `GET /api/v1/devices` | host | The paired devices, never their keys. |
| `DELETE /api/v1/devices/{id}` | host | Revokes the device at once: its next request is refused. |

A paired device signs each request with four headers: `x-vibey-device` (its id),
`x-vibey-timestamp` (seconds since the epoch, within 60 of the host's clock),
`x-vibey-nonce` (never reused) and `x-vibey-signature`, which is `sha256=` and the hex
HMAC-SHA256, under the device's key, of these lines joined by `\n`: device id, method
(upper case), path, query, timestamp, nonce, and the hex SHA-256 of the body. A replayed
nonce, a stale timestamp, a changed method, path, query or body, another device's key or
a revoked device proves nothing (401). There is no session and no cookie, so each action
-- a `spend` answer included -- is verified on its own, and there is no ambient credential
for a cross-site request to ride.

Every pairing and revocation is written to every project's ledger as `HubDevicePaired` /
`HubDeviceRevoked` (the device's id, name, scopes and who acted -- never its key).

## Refusals

| Status | Meaning |
|---|---|
| 401 | The request proves no principal. Nothing else is said. |
| 403 | The principal's scopes do not permit it, a device asked to manage pairings, a pairing code was wrong, spent or expired, or the repository does not admit the hub's bump. |
| 404 | No such project, open gate or paired device. |
| 409 | The gate was already answered by another request, or the queue refused the reorder. |
| 421 | The `Host` header is not one this hub answers (the DNS-rebinding defence). |
| 422 | The body or a filter is malformed. |
| 429 | Too many requests (empty body). |
| 503 | Pairing is not enabled on this hub. |

Every response carries `Content-Security-Policy: default-src 'none'`, `X-Frame-Options:
DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` and
`Cache-Control: no-store`, and none ever carries a CORS header.

## Where it listens

Loopback, unless `vibey.toml` declares [`[hub] lan = true`](configuration.md#hub). With
the LAN declared, the hub also answers this computer's host name, its `.local` name, its
addresses and any `[hub] names`.
