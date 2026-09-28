---
id: skill-16-infrastructure-as-code-4224de5a41
purpose: 16 infrastructure as code
source: src/vibey_tools/skills/plugins/aws-gcp-azure-deep-dive/skills/hyperscaler-cost-reliability-iac-lock-in-and-migration/SKILL.md
requires: ["skill-15-reliability-regions-and-slas-c10ecd7848"]
links: ["skill-17-lock-in-and-multi-cloud-honestly-c1fde39884"]
---

## §16. Infrastructure as Code

```
Native      CloudFormation    ARM / ⚠️ Bicep       Deployment Manager (legacy)
Multi       ⚠️ Terraform / OpenTofu — the de facto standard across all three
Typed       ⚠️ CDK / CDKTF / Pulumi — real languages, real abstractions
Config      Ansible, Chef, Puppet
```
**⚠️ Terraform is the practical default** — **provider coverage across all three, a mature
module ecosystem, and skills that transfer.** ⚠️ **The OpenTofu fork exists following
Terraform's licence change and is a genuine consideration for organizations sensitive to
that.** **Bicep is a real improvement over raw ARM templates and worth using if you're
Azure-only.**
**⚠️ The practices that matter more than the tool**: **remote state with locking** (⚠️ **two
engineers applying simultaneously against local state is a genuine way to destroy
infrastructure**), **state file treated as sensitive — it contains secrets**, **plan
review in CI before apply**, **modules for repeated patterns**, **and drift detection.**
> **⚠️ GOTCHA — manual console changes are the enemy of IaC and everyone makes them.**
> ⚠️ **Once a resource is modified out of band, the next apply may revert it, fail, or
> destroy and recreate it.** **The practical answer is not "never touch the console" —
> it's read access by default, break-glass for writes, and drift detection that tells you
> when it's happened.**

---
