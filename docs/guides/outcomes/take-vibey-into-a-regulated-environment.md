---
description: vibey holds no certification, but it gives an assessor concrete mechanisms to examine, each linked to its evidence, and it says plainly which controls stay with you.
---

# Can I use vibey in a regulated environment?

**Short answer:** vibey holds no certification, but it gives an assessor concrete
mechanisms to examine, each linked to its evidence, and it says plainly which controls stay
with you.

A security review of an AI coding tool asks the same questions every time: who did what,
where the code went, what held the secrets, who approved the change, and what the build
pulled in. This page answers each with the mechanism vibey has, the link that proves it,
and what you still own. It is a checklist to bring to your assessment, not an attestation:
vibey has no mapping to SOC 2, ISO 27001, FedRAMP, HIPAA or any other framework, and makes
no claim of compliance with one.

## Steps

**1. Run the sovereign path** if code must not leave your network: one local engine, no
paid engine allowed ([run agents on your own hardware](run-agents-on-your-own-hardware.md)).

**2. Split the database roles and require passwords.** The owner's connection string goes
to `vibey migrate` alone; everything else connects as a role that can only read and append
to the ledger. Use `scram-sha-256` for every connection
([ADR-0061](../../architecture/decisions/0061-every-postgresql-connection-authenticates-with-scram-sha-256.md)).

**3. Run `vibey doctor` and keep its output.** `ledger-guard` and `db-passwordless` must
both say `PASS`; either failing makes the command exit 1
([`vibey doctor`](../../reference/cli.md#vibey-doctor)).

**4. Export the ledger on a schedule** and keep the shards off the database host
([keep a tamper-evident record](keep-a-tamper-evident-record.md)).

**5. Declare your branch rules** with vibey-gh, so change control is a file you can show an
assessor ([review AI changes before merge](review-ai-changes-before-merge.md)).

## The checklist

| Question | What vibey provides | Evidence |
|---|---|---|
| Who did what? | Every ledger event names its engine and a provenance: `trusted`, `agent` or `untrusted`. A person's command also records the operating-system account that ran it. | [`ledger.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey/domain/ledger.py); [`vibey ledger`](../../reference/cli.md#vibey-ledger) |
| Can the record be rewritten? | The database refuses updates and deletes to the ledger; exports walk a SHA-256 chain. | [ADR-0055](../../architecture/decisions/0055-the-ledger-is-append-only-by-the-database.md); [`test_ledger_guard.py`](https://github.com/the-vibey-project/vibey/blob/develop/tests/infrastructure/db/test_ledger_guard.py) |
| Where does the code go? | On the sovereign path, to three local ports only, measured; no telemetry is sent. | [Host allowlist](../../reference/system-requirements.md#host-allowlist) |
| What can an agent see? | Engine sessions and gate commands start from an allow-listed environment; vibey's own variables and database credentials never reach them. Credentials are redacted before an event is stored. | [SECURITY.md](https://github.com/the-vibey-project/vibey/blob/develop/SECURITY.md), §5; [`redact.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey/infrastructure/ledger/redact.py) |
| Who approves a change? | Design, review and deployment wait for a recorded human answer. vibey-gh merges only on exact-head evidence, and never a stranger's pull request unattended. | [ADR-0009](../../architecture/decisions/0009-human-gates-are-parked-jobs.md); [ADR-0053](../../architecture/decisions/0053-the-unattended-run-admits-no-stranger.md) |
| Is change control declared? | Required checks, approvals, code-owner review and merge rules live in `.vibey-gh.toml`; paths that need a person are held in step with `CODEOWNERS` by a test. | [`.vibey-gh.toml`](https://github.com/the-vibey-project/vibey/blob/develop/.vibey-gh.toml); [`test_protected_paths_agree.py`](https://github.com/the-vibey-project/vibey/blob/develop/tests/meta/test_protected_paths_agree.py) |
| What does the build pull in? | The lock file is checked, and every change runs `bandit` and `pip-audit`. Releases publish to PyPI with no stored token. | [`ci.yml`](https://github.com/the-vibey-project/vibey/blob/develop/.github/workflows/ci.yml); [`vibey-engine.yml`](https://github.com/the-vibey-project/vibey/blob/develop/.github/workflows/vibey-engine.yml) |
| How are flaws reported? | A written disclosure policy. | [SECURITY.md](https://github.com/the-vibey-project/vibey/blob/develop/SECURITY.md#reporting-a-vulnerability) |

## What vibey does not provide

- **Access control inside vibey.** Anyone who can run vibey against the database can answer
  any gate; the name recorded with an answer is a label, beside the account that ran it.
  Restrict who can reach the host and the database.
- **Process isolation.** Every engine session runs as the worker's operating-system user in
  a git worktree. The container isolation level has no effect today
  ([`[isolation]`](../../reference/configuration.md#isolation)).
- **Some built controls are not switched on.** Destructive-command prevention and
  scope-bound mutation are implemented and tested but not yet on an active runtime path
  (SECURITY.md, §2 and §3).
- **Strong defence against prompt injection.** The framing of untrusted text is active on one
  path, the GitHub intake, and SECURITY.md reports it did not reduce injection when measured.
  The control that works is refusing text from people you have not trusted.
- **Build provenance.** No software bill of materials, build attestation or signed artifact
  is published. vibey-gh's "provenance" means attribution headers in the source, not
  build provenance.
- **Secrets from a vault.** Operational tokens come from `vibey.toml` or environment
  variables; an OpenBao adapter exists, but vibey does not yet read its own secrets from it.
- **Hosting, backups and residency.** Where the database, the model and the backups live is
  your deployment's decision.

## The evidence

Each row of the checklist links its own evidence. The underlying record is
[SECURITY.md](https://github.com/the-vibey-project/vibey/blob/develop/SECURITY.md), whose
sections say for every control whether it is implemented, tested and active, and the
[decision records](../../architecture/decisions/0055-the-ledger-is-append-only-by-the-database.md),
each with the alternatives it rejected.

## Limits

This page describes vibey as of its date; SECURITY.md and the linked tests are the current
truth when they differ. Whether a mechanism satisfies a control in your framework is a
judgement for you and your assessor. vibey records and enforces what is described here and
nothing more.

## Go deeper

- [The ledger invariant](../../paper.md#the-ledger-invariant) and
  [what an engine may see](../../paper.md#what-an-engine-may-see), in the research paper.
- [What gets published](../ledger-publication.md), for sharing a redacted ledger.

## Improve this guide

If your assessment asked a question this checklist does not, adding the row — with its
evidence, or with the plain statement that vibey does not do it — is a good first
contribution. This page is
[`docs/guides/outcomes/take-vibey-into-a-regulated-environment.md`](https://github.com/the-vibey-project/vibey/blob/develop/docs/guides/outcomes/take-vibey-into-a-regulated-environment.md);
[your first hour](https://github.com/the-vibey-project/vibey/blob/develop/CONTRIBUTING.md#your-first-hour)
takes you from a fork to a pull request. Found a security flaw instead? Follow
SECURITY.md's disclosure policy, not a public issue.
