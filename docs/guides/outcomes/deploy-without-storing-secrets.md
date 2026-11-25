---
description: Partly, and not yet for production; vibey's opt-in Azure stages keep no cloud credential, act as the az CLI identity you signed in with, and change nothing until you consent, but no real-Azure run is proven yet.
---

# Can an AI agent deploy my software without holding cloud secrets?

**Short answer:** partly, and not yet for production; vibey's opt-in Azure stages keep no
cloud credential, act as the `az` CLI identity you signed in with, and change nothing until
you consent, but no real-Azure run is proven yet.

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** For anyone weighing an agent that deploys. Rehearse with the
> default in-memory adapter, then opt in at review, consent in writing, and run
> `vibey worker --azure az` after `az login`. The rehearsal takes minutes. Afterwards you know
> exactly what vibey would change, and it holds no key to change it with. Azure is the only
> working cloud; OpenStack and AWS are not built.

## The lesson: the locksmith who keeps no key

The Professor's front door had a new lock, and he was still pleased about it.

**Daniel:** If an agent deploys my software, it needs my cloud key. Doesn't it?

**Professor Feynman:** Picture a locksmith who refuses to take a copy of your key. You open the
door yourself, he works while you are signed in, and he works only in the room you named on a
signed note. Change the room and the note is worthless.

**Daniel:** So he can't do any harm.

**Professor Feynman:** Careful. He works with your hands, so he can reach whatever you can reach.
That is the gap. vibey stores no credential and refuses to change anything without your note,
but it acts as whoever `az` is signed in as, with all that identity's rights.

**Daniel:** Then I sign in as someone who can only open that one room.

**Professor Feynman:** Exactly: an identity scoped to one resource group. The picture stops working
at the note: vibey's note names the place, not the work, so it does not list what will be built
or what it will cost.

## Steps

**1. Rehearse with nothing real.** A worker deploys to an in-memory adapter by default
(`vibey worker --azure memory`). Run the whole path this way first
([`vibey worker`](../../reference/cli.md#vibey-worker)).

**2. Opt in at the end of review.** After you accept a review, vibey asks whether to deploy.
`local_only` records the choice and finishes with no deployment job
([ADR-0014](../../architecture/decisions/0014-optional-visual-design-and-deployment-opt-in.md)).

```bash
vibey gates
vibey answer GATE_ID --choice deploy
```

**3. Answer the deployment interview with real values.** `--choice accept_defaults` fills
visible placeholders such as `default-tenant`, which only the in-memory adapter accepts.

```bash
vibey answer GATE_ID --raw '{"tenant_id": "…", "subscription_id": "…",
  "resource_group": "rg-my-app", "environment": "dev", "region": "westeurope"}'
```

**4. Consent, explicitly.** The specification gate defaults to `reject`, and no flag sends
consent ([how each gate is answered](../../reference/cli.md#how-each-kind-of-gate-is-answered)):

```bash
vibey deploy inspect     # the specification and its scope digest
vibey answer GATE_ID --raw '{"verdict": "accept", "explicit_mutation_authorized": true}'
```

Consent is stored with a SHA-256 digest of the target scope, and every mutating call checks
that digest again before it runs.

**5. Sign in, then run a real worker.**

```bash
az login
vibey worker --azure az
vibey deploy status      # phase, endpoints and verification state
```

The worker checks `az account show` first and exits if you are not signed in. Each `az`
command gets a short allow-list of Azure CLI settings and none of the worker's variables, so no
vibey or database secret reaches it
([`az_cli.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey/infrastructure/azure/az_cli.py)).

## Which clouds are real

Ratified sub-doctrine 8.b names self-hosted OpenStack as the sovereign default cloud and Azure,
AWS and GCP as declared-only. Today only Azure has a working adapter. No OpenStack adapter
exists; the AWS adapter is a contract-testing stub
([`aws/adapter.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey/infrastructure/aws/adapter.py)),
and [ADR-0095](../../architecture/decisions/0095-opentofu-is-the-infrastructure-as-code-tool-for-aws.md),
which picks OpenTofu for AWS, is proposed.

vibey's own releases show publishing with nothing stored: PyPI uploads use trusted publishing,
a short-lived token issued to the workflow run
([`vibey-engine.yml`](https://github.com/the-vibey-project/vibey/blob/develop/.github/workflows/vibey-engine.yml)).

## Daniel's teach-back

**Daniel:** vibey keeps no cloud key. I rehearse in memory, opt in, give real identifiers, and
consent in writing; the consent is bound to a digest of the scope, and every change checks it.
The real run acts as my `az` login, so I sign in as an identity limited to one resource group.

**Professor Feynman:** All true. Add one thing: it is Azure only, and not yet proven against a
real subscription.

## The evidence

| Claim | Where it is proved |
|---|---|
| No mutation without digest-bound consent | `test_mutations_are_refused_without_digest_bound_consent` in [`test_az_cli.py`](https://github.com/the-vibey-project/vibey/blob/develop/tests/infrastructure/azure/test_az_cli.py) |
| `az` sees none of the worker's secrets | `test_a_real_az_process_sees_none_of_the_workers_secrets`, same file |
| Deployment is opt-in and declining finishes locally | [ADR-0014](../../architecture/decisions/0014-optional-visual-design-and-deployment-opt-in.md) |
| The digest covers provider, tenant, subscription, resource group and environment | [`deployment.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey/domain/deployment.py) |

## Limits

- **Not proven against real Azure.** The offline path is tested end to end; no real-Azure run
  is recorded ([implementation plan, 10.13](https://github.com/the-vibey-project/vibey/blob/develop/docs/plans/implementation-plan.md),
  working notes that still mark it partial).
- **No workload identity or OIDC.** ADR-0013's
  [safety model](../../architecture/decisions/0013-deployment-is-a-three-phase-stage-set.md#safety-model)
  calls for Entra workload identity; none is built.
- **Consent covers a scope, not a plan.** No `what-if`, preflight or cost estimate is shown,
  and the digest leaves out region, size, cost limit and image. Its `provider` field defaults
  to `openstack` even on the Azure path.
- **One shape of deployment:** an Azure Container App from an ARM template, a sample image by
  default. The specification's identity and cost fields are recorded, not enforced.
- **Three commands are placeholders.** `vibey deploy plan`, `cancel` and `rollback` change
  nothing yet ([`vibey deploy`](../../reference/cli.md#vibey-deploy)).
- **Other parts of vibey do hold secrets.** Operational surfaces such as OpenBao take tokens
  from `vibey.toml` or `VIBEY_*` variables
  ([configuration](../../reference/configuration.md#operational-surface-environment-variable-overlay)).

## When it goes wrong

| You see | It means | Do this |
|---|---|---|
| The worker exits before claiming work with `--azure az` | `az account show` failed | `az login`, then start it again |
| A real deploy refuses `default-tenant` | You accepted the placeholders | Answer step 3 with real identifiers |
| A mutation is refused for consent | No consent, or the scope changed after it | Re-run step 4 for the scope you mean |

## Where next

- [ADR-0013](../../architecture/decisions/0013-deployment-is-a-three-phase-stage-set.md): the
  three deployment phases and the safety model they are built toward.
- [The six-phase machine](../../paper.md#the-six-phase-machine), in the research paper.

## Say it in one line

vibey's Azure deploy keeps no cloud key, acts as your az login, and changes nothing without written consent bound to the scope, but it is not yet proven on real Azure.

## Improve this guide

The limits above are the roadmap, and each is a real contribution: a `what-if` before
consent, workload identity, a first recorded real-Azure run. Smaller fixes to this page
count too. It is
[`docs/guides/outcomes/deploy-without-storing-secrets.md`](https://github.com/the-vibey-project/vibey/blob/develop/docs/guides/outcomes/deploy-without-storing-secrets.md);
[your first hour](https://github.com/the-vibey-project/vibey/blob/develop/CONTRIBUTING.md#your-first-hour)
takes you from a fork to a pull request, and [an issue](https://github.com/the-vibey-project/vibey/issues/new/choose)
is the place to propose the larger ones.
