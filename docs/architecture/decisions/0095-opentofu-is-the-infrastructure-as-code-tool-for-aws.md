# 0095 — OpenTofu is the infrastructure-as-code tool for AWS deployments

**Status:** proposed · **Date:** 2026-10-24 · **Cites:** sub-doctrines 8.a, 8.b, 8.h, 10.e · **Related:** ADR-0013, ADR-0042 · **Ruling:** #668, item 5

## Context

Sub-doctrine 8.b makes AWS the cloud that an unnamed paid declaration reaches: declared-only, relaying
through the sovereign host. No AWS adapter exists. Only `src/vibey/infrastructure/azure/` does, and
`CloudClientPort` has one real implementation. The storm's design spike
(`docs/plans/qwenstorm-3.0.0/specs/gap-spike-aws-iac.md`) asks eight questions; the first is which tool
describes and applies an AWS deployment, and every other AWS lane waits on it. The three candidates:

- **OpenTofu** (MPL-2.0): the `tofu` binary and the AWS provider.
- **CloudFormation**: the `aws` CLI, with AWS holding the state.
- **The AWS CDK**: synthesizes CloudFormation, and needs Node.

## Decision

**OpenTofu.** It is the candidate #668 marked as preferred under 8.a's freer-licence tie-breaker
(MPL-2.0), and unlike the other two it does not leave AWS holding the deployment's state:
CloudFormation does, and the CDK compiles to it.

## Consequences

- **It is new code.** Sub-doctrine 10.e asks the family to reuse what it has, and the family has no
  OpenTofu code. The nearest is the OpenStack work, which renders Heat templates (HOT), a CloudFormation
  dialect, so the choice does not reuse it. The operator accepted that.
- **Only the first question is decided.** The spike's other seven stay open and belong to the AWS design
  record: the transport (`tofu` or the `aws` CLI through `CommandExecutor`, or direct signed HTTPS), how
  `AzureTargetScope` maps onto an AWS account, region and stack, the container topology (ECS on Fargate,
  App Runner or another), the command table per `CloudClientPort` verb, credentials, preflight and doctor,
  and where the state of record lives.
- **`tofu` must be installable on Arch Linux and macOS** (8.h), so it joins the local stack as an opt-in
  dependency, like the OpenStack CLI.
- **Rule status.** A tool choice, not a rule: it owes no sub-doctrine (ADR-0020).
