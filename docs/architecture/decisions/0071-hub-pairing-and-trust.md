# 0071 — Hub pairing and trust: signed requests, a pinned certificate, `_vibey._tcp`

**Status:** proposed · **Date:** 2026-09-25 · **Cites:** SD-01 v1.0; sub-doctrines 10.c, 10.f, 10.g, 12.c, 12.f, 12.j · **Related:** ADR-0016, ADR-0017, ADR-0018, ADR-0068 · **Evidence:** `develop` at `0823cdfd` plus the live feed (#1163), read 2026-09-25 · **Delivers:** ADR-0068's third change, "Pairing and trust"

**Owes:** the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md`
and `docs/index.md`, and a nav entry in `properdocs.yml`, all done in the change that
carries it.

## Context

ADR-0068 gave the hub one principal, the host, identified by a token file only the host's
account can read. A phone on the LAN has no such file, so until now it could not reach the
hub at all. SD-01 §2 says what may replace the file: not the network position of the
caller (being on the LAN proves nothing), not its say-so, but a tangible check -- here, a
secret handed over in person, and a certificate the person saw on the host's own screen.

## Decision

1. **Pairing is an offer the host makes and a device spends.** `vibey hub pair --scope …`
   asks the running hub for an offer: a 6-digit code from the OS CSPRNG, valid 120 seconds
   (`PAIRING_TTL_SECONDS`), for the scopes named -- at least one; an empty grant is
   refused (deny by default, 10.c). The first correct `POST /api/v1/pairing/claim` spends
   the code and returns the device's id and a 32-byte key, once. Wrong codes are counted
   and `MAX_WRONG_CLAIMS` (5) of them withdraw every open offer, and every claim draws
   from a small per-address rate-limit bucket: a guesser gets five tries in a million.
   Offers live only in the running process.

2. **Only the host manages pairings.** Offering, listing and revoking need the host
   principal; a device is refused (403) even for its own record, so no device can widen
   its own grant or pair another (12.j).

3. **Every device request is signed, and there is no session.** HMAC-SHA256 under the
   device's key over the device id, method, path, query, timestamp, nonce and body hash
   (`HubPairingPolicy.canonical`; no field may hold a newline, so no two requests share a
   form), verified by vibey_bootstrap's `verify_hmac_signature` (the dogfood rule). The
   timestamp must be within 60 seconds of the host's clock; a nonce is remembered for two
   windows, and when the memory is full a new nonce is refused rather than an old one
   forgotten, because forgetting would open a replay. With no session, every action -- a
   `spend` answer included -- is verified on its own; this is the "re-verified per action"
   ADR-0068 asked of `spend`.

4. **Revocation is immediate because the registry is read per request.** Paired devices
   live in `<state_dir>/devices.json`, owner-only, beside the host token and with its
   protection (no symlinks; owner and mode checked on the open file). The authenticator
   reads it on every request, so `vibey hub revoke` refuses the device from its next
   request -- on open live feeds too, which re-authenticate before every page (ADR-0068).

5. **Pairing and revocation are ledger events, in every project.** `HubDevicePaired` and
   `HubDeviceRevoked` carry the device's id, name, scopes and who acted -- never the key --
   and are appended to every project's ledger in one transaction, since a device paired
   to the hub may read every project and each project's history should say so. A project
   in a phase this vibey does not know refuses the whole write (writers stay strict,
   vibey#287). The publication policy withholds both kinds.

6. **A declared LAN is TLS with a pinned, self-signed certificate.** With
   `[hub] lan = true`, `vibey serve` makes a P-256 key and self-signed certificate on
   first run (0600, 0700 directory), serves it through uvicorn, and prints its SHA-256
   fingerprint. The pairing URI the QR code carries --
   `vibey-pair://<host>:<port>?fp=<sha256>&code=<code>&v=1` -- is how a device learns
   which certificate to trust, and it trusts no other. On loopback nothing crosses a
   network: plain HTTP, no certificate, no fingerprint.

7. **Discovery is `_vibey._tcp`, only on a declared LAN.** The hub registers
   `_vibey._tcp.local.` through `zeroconf` with its instance name, port, fingerprint and
   API version, and withdraws it on shutdown. Loopback addresses are never announced; a
   loopback hub announces nothing (10.f: an advertisement nobody can reach says something
   false). The advertisement grants nothing.

8. **No cookies, so no CSRF surface.** Every credential is a header the caller sets; the
   hub sets no cookie. Together with the Host allowlist (421 before any route, the claim
   route included), no CORS header, and `default-src 'none'`, a page on another origin has
   no ambient credential to ride and cannot read a response.

`zeroconf` and `segno` (the terminal QR code) join the optional `hub` extra and are
imported only when used.

## Consequences

- A phone can pair and use the hub with exactly the scopes the host chose; the host can
  see and revoke every device from the CLI.
- **Not done here, recorded:** the key and certificate live in owner-only files, not in
  OpenBao through `SecretsPort` as ADR-0068 proposed -- no secrets store is wired into
  `vibey serve` yet, and the files have the host token's protection. Relative lane paths
  for view-only devices, a device re-verifying on a change of network (the client's side),
  platform key storage (Keychain, Keystore, libsecret, WebCrypto: the clients'), and the
  served web app's own CSRF token (there is no served web app yet) remain open.
- A shared-secret HMAC means the hub holds each device's key. An asymmetric device key
  (the device signs, the hub holds only the public half) would remove that; it was not
  chosen because vibey_bootstrap ships HMAC verification and no signature verification,
  and the dogfood rule says extend ours before reaching past it. That extension is the
  natural next step.

## Alternatives considered

- **Bearer device tokens.** Rejected: a captured request is a captured credential, and
  replay protection would need a session anyway.
- **mTLS client certificates.** Rejected for now: every client platform (React Native,
  the browser) handles client certificates differently or not at all.
- **Recording pairing only in a host-wide log.** Rejected: the ledger is where vibey keeps
  history, and a per-project record answers "who could read this project" in the place
  someone would look.
