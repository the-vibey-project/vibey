## Title
docs(adr): design spike — AWS, 8.b's default paid cloud, behind CloudClientPort: IaC tool, primitives, scope, credentials and children

## Why
Sub-doctrine 8.b (`src/vibey_tools/gh/docs/doctrines.md:136-137`, `:179-186`, `:188-194` at
integration HEAD `d3b4a388`) makes AWS the cloud an unnamed paid declaration reaches, declared-only
and relaying through the sovereign host. Gap C1 (`issue-audit/gaps.md:171-187`): there is no AWS
adapter at all — only `src/vibey/infrastructure/azure/` exists, `CloudClientPort` has one real
implementation (`src/vibey/infrastructure/azure/az_cli.py:47-165`), and the OpenStack lanes refuse
`target = "aws"` (`issue-audit/updates/330.md` child 1: "a declared-only cloud with no adapter yet
… is refused"). #85's child 3 (`issue-audit/updates/85.md:132-133`) says "design needed first on
which deploy primitives map". The IaC tool is an operator ruling (`specs/gap-ops-canon-rulings.md`
item 5: OpenTofu, CloudFormation or the AWS CDK), and every AWS code lane depends on it.

Implementer: a large model or the operator (design, not code); the storm runner skips gap-spike-*.

## Deliverable
One file, `STORM/specs/ADR-gap-aws-iac.md`: a draft ADR
(number assigned at ratification), written like `specs/ADR-two-loops.md`. Nothing else is written.

## Questions the ADR must decide (each with a stated answer, or "operator ruling: <item>")
1. **IaC tool.** OpenTofu (MPL-2.0, `tofu` binary + the AWS provider), CloudFormation (the `aws`
   CLI; AWS holds the state), or the AWS CDK (synthesizes CloudFormation; needs Node). Weigh 8.a's
   freer-licence tie-breaker, 10.e (Heat is a CloudFormation dialect — `specs/openstack-client-p2.md`
   renders HOT; the family has no OpenTofu code), 8.h (both tools installable on Arch Linux and
   macOS), and who holds the state (question 8). Present a recommendation; the choice itself is
   `gap-ops-canon-rulings` item 5, and the ADR records the ruling when it is given.
2. **Transport.** The `aws` CLI through `CommandExecutor` (as `az_cli.py` and #331 child 2's
   `OpenStackCliAdapter` do), `tofu` through `CommandExecutor`, or direct HTTPS with the family's
   SigV4 signer (`src/vibey/infrastructure/blob/garage.py:26-45`, 10.e). State what each costs in
   installation (8.h) and testability (a scripted executor or an in-memory HTTP transport).
3. **Scope mapping.** How `AzureTargetScope`'s fields (`src/vibey/domain/deployment.py:14-32`) map:
   `subscription_id` → the 12-digit AWS account id (checked against `sts get-caller-identity`),
   `tenant_id` → ? (an Organizations id, the account again, or a named profile), `resource_group` →
   the stack or workspace name, `region` → `--region`, `environment` → a tag. Whether AWS needs
   provider-specific validation in `DeploymentSpec.validate()` (`deployment.py:88-155`). The digest
   is the provider-first form (#330 child 2, `updates/330.md`), so consent cannot cross clouds.
4. **The container topology.** What `service_type = "container_app"` becomes on AWS: ECS on Fargate
   plus an ALB (runbook 03, `docs/runbooks/expansion/03-multicloud-aws-gcp.md:35-40`), App Runner,
   or another; how `instances`, `ingress_enabled` and `tls_enabled` map (TLS needs a certificate:
   ACM needs a domain — say what happens without one); which network; the default image parameter
   (compare `arm.py:21` and #331's `DEFAULT_IMAGE`). Anything unsupported is refused, never
   improvised (`arm.py:13-14`).
5. **The command table.** For each `CloudClientPort` verb (`src/vibey/application/interfaces/azure.py:44-68`)
   and for `CloudPlanPreviewPort.preview_plan` (lane `gap-deploy-plan-1`): the exact argv, its
   success output, and what a non-zero exit means — in the table form of `specs/openstack-client.md:395-411`.
   Create-or-update (idempotent under replay), not-found delete returns (idempotent), the state
   mapping to `Succeeded`/`Running`/`Failed`/`Unknown` (as `OpenStackCliAdapter.stack_state`), and
   the preview's mapping to `NormalizedResourceChange` (`deployment.py:210-217`; CloudFormation change
   sets or `tofu plan -json`).
6. **Credentials.** Secrets from `SecretsPort` through lane `gap-aws-secrets`
   (`AwsCredentialSource` + `AwsCredentialedExecutor`), ambient credentials (a profile or SSO), or
   both with a stated precedence; whether long-lived access keys are allowed at all (ADR-0013's
   Azure rule "do not create or store client secrets", `docs/architecture/decisions/0013-deployment-is-a-three-phase-stage-set.md:60-61`).
   The `[deploy.aws]` keys, env overrides and defaults (12.c).
7. **Preflight and doctor.** The `PREFLIGHT_ARGV` and `LOGIN_HINT` class attributes (the #331 child
   2/3 pattern, `updates/331.md` "Proposed child lanes"), `preflight() -> bool`, and the doctor lines.
8. **Relay posture and the state of record.** 8.b says a declared paid platform "relays through the
   sovereign host rather than replacing it". Say what the sovereign host holds for an AWS
   deployment (the ledger, 7.c; the IaC state — for OpenTofu, an S3 backend on the sovereign Garage,
   ADR-0043; for CloudFormation, AWS itself) and hand the relay mechanics to the relay spike
   (gap C3, `gap-spike-relay`) rather than deciding them here.
9. **Defaults.** `DEPLOY_IAC_BY_TARGET["aws"]` (the IaC token or tokens, first is the default) and
   `DEPLOY_REGION_BY_TARGET["aws"]` (#330 child 1 declares both maps).
10. **Test isolation and the live contract.** Which executables join `[tool.vibey.test_isolation]
    forbidden_executables` (lane `fakes-isolation-guard`: at least `aws`, and `tofu` if chosen); where
    the opt-in live test lives (`tests/live/**` is protected — `.vibey-gh.toml` protected paths), its
    marker (`integration`, `paid`), its gate variable (`VIBEY_AWS_LIVE`, runbook 03:48-54), its cost
    ceiling and its teardown proof.
11. **Measurement.** What each AWS call records once `gap-measure-port` exists (8.g,
    `doctrines.md:316-324`): latency and outcome per verb, at least.

## Evidence to gather (read, cite file:line at the integration HEAD you read)
- `src/vibey/domain/config.py:137-140`, `:453-459` and `updates/330.md` child 1 (the target map).
- `src/vibey/domain/deployment.py:14-32`, `:88-155`, `:210-255` (scope, validation, `evaluate_iac_plan`).
- `src/vibey/application/interfaces/azure.py:19-71`, `src/vibey/application/azure_port.py:14-26`.
- `src/vibey/infrastructure/azure/az_cli.py:36-165`, `arm.py:1-93`, `iac.py:43-80` (what-if normalizer).
- `specs/openstack-client-p1.md`, `specs/openstack-client-p2.md`, `issue-audit/updates/330.md`,
  `issue-audit/updates/331.md` (children 1-5, `CloudClientSelector`, `preflight()`).
- `src/vibey/application/deploy_execute_handler.py:62-172`, `deploy_review_routing.py:145-147`.
- `src/vibey/infrastructure/blob/garage.py:26-45` (SigV4), `src/vibey/infrastructure/secrets/openbao.py`.
- `docs/runbooks/expansion/03-multicloud-aws-gcp.md:26-87`; ADR-0013 `:56-99`; ADR-0042 `:58-64`, `:82-89`.
- `specs/gap-deploy-plan-1.md` (the preview port), `specs/gap-aws-secrets.md`, `specs/fakes-isolation-guard.md`.
- The package names for the chosen tools on Arch Linux (`pacman -Si`, the AUR helper's `-Si`) and
  macOS (`brew info`), recorded with the date (10.f).

## Canon the ADR must honour
8.a (`doctrines.md:99-118`), 8.b cloud, relay and paid defaults (`:136-137`, `:179-186`,
`:188-194`), 8.g (`:316-324`), 8.h (`:326-334`), 7.c (`:82-91`: no credential in the ledger, and
every redaction recorded), 9.b (`:349`), 10.d (`:395-410`), 10.e (`:417`), 10.f (`:419`), 12.c
(`:455`); ADR-0013's safety model; ADR-0016; ADR-0042; the non-negotiables in `CLAUDE.md` (never
block a worker; idempotent under replay; append-only ledger). SD-01 §2 and §5: an AWS account is a
counterparty, unverified until checked (`sts get-caller-identity` against the declared account).

## Required ADR sections
**Status** (proposed; the IaC choice "pending `gap-ops-canon-rulings` item 5" until ruled) ·
**Owes** · **Context** · **Decision** (one numbered subsection per question above) · **Security
impact** · **Migration** · **Consequences** · **Alternatives rejected** · **Verification owed at
implementation** · **Child lanes** (below, each with its exact scope, files and dependencies).

## Child lanes the ADR must name (written after the ruling, not now)
Each is one source file plus its interface and one test file, per `STORM/SPEC-TEMPLATE.md`.
1. `gap-aws-iac-renderer` — renders a `DeploymentSpec` into the ruled IaC document, a class beside
   its interface (the #331 child 1 shape). Depends: this spike, `gap-ops-canon-rulings`.
2. `gap-aws-cli-client` — `AwsCliCloudClient` implementing `CloudClientPort` and
   `CloudPlanPreviewPort`, with `PROVIDER = "aws"`, `PREFLIGHT_ARGV`, `LOGIN_HINT`, `preflight()`,
   the refusal order (`ScopeProviderMismatchError`, digest-bound consent, stack name, topology)
   before any subprocess, `AwsCredentialedExecutor` as its default executor, tests through
   `ScriptedCommandExecutor`, and the new executables added to `forbidden_executables`. Split -1/-2
   if the command table is large. Depends: `gap-aws-iac-renderer`, `gap-aws-secrets`,
   `gap-deploy-plan-1`, `openstack-client-p1`, `fakes-process-executor`.
3. `gap-aws-target` — `DEPLOY_IAC_BY_TARGET["aws"]`, `DEPLOY_REGION_BY_TARGET["aws"]`, the
   `[deploy.aws]` keys and env overrides feeding `AwsCredentialSource`, and any AWS scope
   validation. Depends: `gap-aws-cli-client`, `openstack-client-p1`.
4. `gap-aws-deploy-execute` — the worker's `CloudClientSelector` (#331 child 4, under
   `openstack-client-p2`) maps `"aws"` to `AwsCliCloudClient`; DEPLOY_EXECUTE and DEPLOY_REVIEW run on
   AWS end to end over a scripted executor, through the real handlers. Depends: `gap-aws-target`,
   `openstack-client-p2`, `gap-deploy-execute-control`.
5. `gap-aws-doctor` — `vibey doctor` lines for an AWS target: the CLI(s) present, the credential
   source (secret key names, never values), the reached account against the declared one. Depends:
   `gap-aws-cli-client`, `gap-aws-target`, `installer-doctor`.
6. `gap-aws-install` — opt-in `cloud`-group installer entries for the chosen tools on Arch Linux and
   macOS, verified on the day (the #331 child 5 shape). Depends: `installer-catalogue`,
   `installer-toolchain`, `gap-ops-canon-rulings`.
7. `gap-aws-live-contract` — the opt-in live test (question 10). Depends: `gap-aws-deploy-execute`,
   and an operator-funded account (a `gap-ops-*` item the ADR names).

## Acceptance criteria
- [ ] `specs/ADR-gap-aws-iac.md` exists with every required section, and every question above has
      an answer or an explicit "operator ruling: gap-ops-canon-rulings item N".
- [ ] Every `file:line` it cites resolves at the integration HEAD it names.
- [ ] Each child lane names its files, its dependencies, and nothing a later ruling could change.

## Tests to write first (TDD)
None: a design lane. The reviewer checks the acceptance criteria.

## Checks the lane must run (all must pass)
None in code. `git -C STORM/integration status --short`
stays empty (the spike never touches the integration clone).

## Out of scope
- Any code, and the other gap-C lanes (`gap-paid-defaults`, `gap-deploy-target-paid`, `gap-aws-secrets`).
- GCP (a follow-up after this ADR, per `updates/85.md` child 4) and the relay mechanics (`gap-spike-relay`).
- Editing docs/, ADRs in the tree, runbook 03 (the docs wave), or `gap-ops-canon-rulings`.

Commit as `docs(adr): draft the AWS cloud adapter ADR` (only when the operator moves the draft into the tree; the spike itself commits nothing). Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
