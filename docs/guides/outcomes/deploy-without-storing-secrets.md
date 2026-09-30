---
description: Partly, and not yet for production; vibey's opt-in Azure stages keep no cloud credential, act as the az CLI identity you signed in with, and change nothing until you consent, but no real-Azure run is proven yet.
---

# Can an AI agent deploy my software without holding cloud secrets?

**Short answer:** partly, and not yet for production; vibey's opt-in Azure stages keep no
cloud credential, act as the `az` CLI identity you signed in with, and change nothing until
you consent, but no real-Azure run is proven yet.

Handing an agent a cloud key is handing it everything the key can do, for as long as the
key lives. vibey's deployment stages are built the other way round: vibey stores no cloud
credential, borrows the identity you are already signed in as, and binds its right to
change anything to a scope you approved. This page shows how far that goes today, and says
plainly where it stops. Read the limits before you point it at anything that matters.

## Steps

**1. Rehearse with nothing real.** By default a worker deploys to an in-memory adapter that
touches no infrastructure (`vibey worker --azure memory`, the default). Run the whole path
this way first ([`vibey worker`](../../reference/cli.md#vibey-worker)).

**2. Opt in at the end of review.** After you accept a review, vibey asks whether to
deploy. The default answer, `local_only`, records the choice and finishes locally with no
deployment job ([ADR-0014](../../architecture/decisions/0014-optional-visual-design-and-deployment-opt-in.md)).

```bash
vibey gates
vibey answer GATE_ID --choice deploy
```

**3. Answer the deployment interview with real values.** `--choice accept_defaults` fills
the target with visible placeholders such as `default-tenant`, which only the in-memory
adapter accepts. For a real target, answer with the identifiers:

```bash
vibey answer GATE_ID --raw '{"tenant_id": "…", "subscription_id": "…",
  "resource_group": "rg-my-app", "environment": "dev", "region": "westeurope"}'
```

**4. Consent, explicitly.** vibey then asks you to accept the deployment specification. Its
default is `reject`, and no flag sends consent; you write it
([how each gate is answered](../../reference/cli.md#how-each-kind-of-gate-is-answered)):

```bash
vibey answer GATE_ID --raw '{"verdict": "accept", "explicit_mutation_authorized": true}'
```

Consent is stored with a SHA-256 digest of the target scope, and every mutating call
checks that digest again before it runs.

**5. Sign in, then run a real worker.**

```bash
az login
vibey worker --azure az
```

The worker checks `az account show` first and exits if you are not signed in. Each `az`
command the deployment runs gets a short allow-list of Azure CLI settings and none of the
worker's own variables, so no vibey or database secret reaches it
([`az_cli.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey/infrastructure/azure/az_cli.py)).

## What vibey itself does

vibey's own releases are the working example of publishing with nothing stored: its
release workflow uploads to PyPI through trusted publishing, a short-lived token issued to
the workflow run, with no API token kept anywhere
([`vibey-engine.yml`](https://github.com/the-vibey-project/vibey/blob/develop/.github/workflows/vibey-engine.yml)).

## The evidence

| Claim | Where it is proved |
|---|---|
| No mutation without digest-bound consent | `test_mutations_are_refused_without_digest_bound_consent` in [`test_az_cli.py`](https://github.com/the-vibey-project/vibey/blob/develop/tests/infrastructure/azure/test_az_cli.py) |
| `az` sees none of the worker's secrets | `test_a_real_az_process_sees_none_of_the_workers_secrets`, same file |
| Deployment is opt-in and declining finishes locally | [ADR-0014](../../architecture/decisions/0014-optional-visual-design-and-deployment-opt-in.md) |
| The default adapter touches no infrastructure | [`vibey worker`](../../reference/cli.md#vibey-worker), `--azure` |

## Limits

- **Not proven against real Azure.** The offline path is tested end to end; the real-Azure
  proof has not been run
  ([implementation plan, 10.13](https://github.com/the-vibey-project/vibey/blob/develop/docs/plans/implementation-plan.md)).
- **No workload identity or OIDC.** ADR-0013's
  [safety model](../../architecture/decisions/0013-deployment-is-a-three-phase-stage-set.md#safety-model)
  calls for Entra workload identity; none is built. vibey uses whatever identity `az` holds, with that identity's full rights. Sign in
  as an identity scoped to the one resource group.
- **Consent covers a scope, not a plan.** You approve a specification. No `what-if`, preflight
  or cost estimate is shown first, and the digest covers the provider, tenant, subscription,
  resource group and environment, not the region, size, cost limit or image.
- **One shape of deployment.** Only an Azure Container App from an ARM template, with a
  sample image by default. The specification's identity and cost fields are recorded, and
  the deployment enforces neither.
- **Three commands are placeholders.** `vibey deploy plan`, `cancel` and `rollback` change
  nothing yet ([`vibey deploy`](../../reference/cli.md#vibey-deploy)).
- **Other parts of vibey do hold secrets.** Operational surfaces such as OpenBao take tokens
  from `vibey.toml` or `VIBEY_*` variables
  ([configuration](../../reference/configuration.md#operational-surface-environment-variable-overlay)).

## Go deeper

- [ADR-0013](../../architecture/decisions/0013-deployment-is-a-three-phase-stage-set.md):
  the three deployment phases and the safety model they are built toward.
- [The six-phase machine](../../paper.md#the-six-phase-machine), in the research paper.

## Improve this guide

The limits above are the roadmap, and each is a real contribution: a `what-if` before
consent, workload identity, a first recorded real-Azure run. Smaller fixes to this page
count too. It is
[`docs/guides/outcomes/deploy-without-storing-secrets.md`](https://github.com/the-vibey-project/vibey/blob/develop/docs/guides/outcomes/deploy-without-storing-secrets.md);
[your first hour](https://github.com/the-vibey-project/vibey/blob/develop/CONTRIBUTING.md#your-first-hour)
takes you from a fork to a pull request, and [an issue](https://github.com/the-vibey-project/vibey/issues/new/choose)
is the place to propose the larger ones.
