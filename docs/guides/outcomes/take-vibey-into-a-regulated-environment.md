---
description: vibey holds no certification, but it gives an assessor concrete mechanisms to examine, each linked to its evidence, and it says plainly which controls stay with you.
---

# Can I use vibey in a regulated environment?

**Short answer:** vibey holds no certification, but it gives an assessor concrete
mechanisms to examine, each linked to its evidence, and it says plainly which controls stay
with you.

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** For security reviewers and the teams who face them. Run the
> sovereign path with web access shut, split the database roles, keep `vibey doctor` output and
> ledger exports, and bring the checklist below. vibey maps to no framework (SOC 2, ISO 27001,
> FedRAMP, HIPAA or any other) and claims compliance with none.

## The lesson: the inspector's walk

The assessor's questionnaire ran to forty pages, and Daniel had read all of them.

**Daniel:** Can I just tell them vibey is secure?

**Professor Feynman:** No one should believe that sentence. Think of a building inspector. You
do not hand her a brochure; you open each door and show what is behind it.

**Daniel:** So the checklist is the walk.

**Professor Feynman:** Yes. Each row is a door: the mechanism, and the test or decision record
that proves it. Some doors open onto an empty room, listed under "What vibey does not provide";
show those before she finds them. The picture stops working at the certificate: an inspector may
issue one, and nobody issues one for vibey.

## Steps

**1. Run the sovereign path with web access shut:** one local engine, no paid engine, no
SearXNG, no Brave key, and `[web] allow_hosts = []`
([run agents on your own hardware](run-agents-on-your-own-hardware.md)).

**2. Split the database roles and require passwords.** The owner's string goes to
`vibey migrate` alone; use `scram-sha-256` for every connection
([ADR-0061](../../architecture/decisions/0061-every-postgresql-connection-authenticates-with-scram-sha-256.md)).

**3. Run `vibey doctor` and keep its output.** `ledger-guard` and `db-passwordless` must both
say `PASS`; either failing makes it exit 1. Its `hub-exposure` line passes only when a running
hub listens on loopback, or on a network `[hub] lan` declares
([`vibey doctor`](../../reference/cli.md#vibey-doctor)).

**4. Export the ledger on a schedule** and keep the shards off the database host
([keep a tamper-evident record](keep-a-tamper-evident-record.md)).

**5. Declare your branch rules** with vibey-gh ([review AI changes](review-ai-changes-before-merge.md)).

## The checklist

| Question | What vibey provides | Evidence |
|---|---|---|
| Who did what? | Every ledger event names its engine and a provenance (`trusted`, `agent`, `untrusted`); a person's command also records the operating-system account. | [`ledger.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey/domain/ledger.py) |
| Can the record be rewritten? | The database refuses updates and deletes; exports walk a SHA-256 chain. | [ADR-0055](../../architecture/decisions/0055-the-ledger-is-append-only-by-the-database.md); [`test_ledger_guard.py`](https://github.com/the-vibey-project/vibey/blob/develop/tests/infrastructure/db/test_ledger_guard.py) |
| Where does the code go? | To PostgreSQL, Ollama and the hub on this machine; no telemetry. Web research reaches out unless shut (step 1). The hub's web tools record `WebSearched` and `WebFetched` without query or URL. | [ADR-0102](../../architecture/decisions/0102-local-first-search-and-a-provisioned-searxng.md); [Host allowlist](../../reference/system-requirements.md#host-allowlist) |
| What can an agent see? | Sessions start from an allow-listed environment; vibey's variables and database credentials never reach them, and credentials are redacted before storage. | [SECURITY.md](https://github.com/the-vibey-project/vibey/blob/develop/SECURITY.md), §5; [`redact.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey/infrastructure/ledger/redact.py) |
| Who may act remotely? | The hub denies by default. A paired device holds only the scopes you grant (`view`, `answer`, `spend`, `run`, `bump`); a driving LLM never holds `spend`, the only scope that answers a spending gate. Caps, migrations and the database string are never reachable. `vibey hub devices` and `vibey hub revoke` manage pairings. | [`hub_scope.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey/domain/hub_scope.py); [ADR-0071](../../architecture/decisions/0071-hub-pairing-and-trust.md) |
| Who approves a change? | Design, review and deployment wait for a recorded answer; vibey-gh merges only on exact-head evidence, never a stranger's pull request unattended. | [ADR-0009](../../architecture/decisions/0009-human-gates-are-parked-jobs.md); [ADR-0053](../../architecture/decisions/0053-the-unattended-run-admits-no-stranger.md) |
| Is change control declared? | Checks, approvals, code-owner review and merge rules live in `.vibey-gh.toml`, held in step with `CODEOWNERS` by a test. | [`test_protected_paths_agree.py`](https://github.com/the-vibey-project/vibey/blob/develop/tests/meta/test_protected_paths_agree.py) |
| What does the build pull in? | The lock file is checked. Every merge into `develop` runs the full CI tier in the merge queue, `bandit` and `pip-audit` included; a pull request's own run covers what its diff touches. | [`ci.yml`](https://github.com/the-vibey-project/vibey/blob/develop/.github/workflows/ci.yml) |
| How are releases proven? | Every release file gets a `SHA256SUMS` line and a build-provenance attestation; PyPI uploads use no stored token. | [`release-binaries.yml`](https://github.com/the-vibey-project/vibey/blob/develop/.github/workflows/release-binaries.yml) |
| How are flaws reported? | A written disclosure policy. | [SECURITY.md](https://github.com/the-vibey-project/vibey/blob/develop/SECURITY.md#reporting-a-vulnerability) |

## Daniel's teach-back

**Daniel:** I don't claim vibey is compliant. I shut the web door, keep doctor output and ledger
exports, and walk the assessor through each mechanism and the test behind it, empty rooms too.

**Professor Feynman:** That is the honest walk.

## What vibey does not provide

- **Access control for local users.** Anyone who can run vibey against the database can answer
  any gate; the recorded name is a label beside the account. Restrict the host and database.
- **Process isolation.** Engine sessions run as the worker's user in a git worktree; the
  container level has no effect today ([`[isolation]`](../../reference/configuration.md#isolation)).
- **Some built controls are off.** Destructive-command prevention and scope-bound mutation are
  tested but not on an active path (SECURITY.md, §2 and §3).
- **Strong prompt-injection defence.** Framing is active on the GitHub intake only and did not
  reduce injection when measured; refusing untrusted authors is the control that works.
- **A software bill of materials**, or notarised desktop builds: the macOS `.dmg` is ad-hoc
  signed while the Developer ID secrets are absent, and the Android APK carries the debug key.
  vibey-gh's "provenance" means attribution headers, not build provenance.
- **Secrets from a vault.** An OpenBao adapter exists, but vibey does not read its own secrets
  from it.
- **Hosting, backups and residency.** `vibey state` can seal the database with AES-256-GCM onto
  a GitHub branch ([ADR-0086](../../architecture/decisions/0086-state-sync.md)), only if you
  run it; where data lives is your decision.
- **Isolation from pull-request content.** The sovereign review runner reads untrusted pull
  requests on the operator's machine, an accepted risk (SECURITY.md, §9).

## The evidence

Each row links its own. Behind them,
[SECURITY.md](https://github.com/the-vibey-project/vibey/blob/develop/SECURITY.md) says for every
control whether it is implemented, tested and active.

## Limits

This page describes vibey 0.4.0 on 2026-11-24; SECURITY.md and the tests are the truth when they
differ. Whether a mechanism satisfies a control is for you and your assessor.

## When it goes wrong

| You see | It means | Do this |
|---|---|---|
| `db-passwordless` FAIL | The database accepts a connection with no password | Set `scram-sha-256` in `pg_hba.conf` |
| `hub-exposure` FAIL | The hub listens beyond loopback, undeclared | Bind it to `127.0.0.1`, or declare `[hub] lan` |

## Where next

- [What an engine may see](../../paper.md#what-an-engine-may-see), in the research paper.
- [What gets published](../ledger-publication.md), for sharing a redacted ledger.

## Say it in one line

vibey is not certified, but each control an assessor asks about links to the code or test behind it, and the gaps are listed first.

## Improve this guide

If your assessment asked a question this checklist does not, adding the row — with its
evidence, or with the plain statement that vibey does not do it — is a good first
contribution. This page is
[`docs/guides/outcomes/take-vibey-into-a-regulated-environment.md`](https://github.com/the-vibey-project/vibey/blob/develop/docs/guides/outcomes/take-vibey-into-a-regulated-environment.md);
[your first hour](https://github.com/the-vibey-project/vibey/blob/develop/CONTRIBUTING.md#your-first-hour)
takes you from a fork to a pull request. Found a security flaw instead? Follow
SECURITY.md's disclosure policy, not a public issue.
