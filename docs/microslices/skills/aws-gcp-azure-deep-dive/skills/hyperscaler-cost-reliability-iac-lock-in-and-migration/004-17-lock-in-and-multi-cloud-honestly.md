---
id: skill-17-lock-in-and-multi-cloud-honestly-c1fde39884
purpose: 17 lock in and multi cloud honestly
source: src/vibey_tools/skills/plugins/aws-gcp-azure-deep-dive/skills/hyperscaler-cost-reliability-iac-lock-in-and-migration/SKILL.md
requires: ["skill-16-infrastructure-as-code-4224de5a41"]
links: ["skill-18-migration-7bae3ab2fc"]
---

## §17. ⚠️ Lock-In and Multi-Cloud, Honestly

**⚠️ Lock-in is real and it is not primarily about APIs.**
```
LOW lock-in     VMs, containers, object storage, managed Postgres/MySQL,
                Kubernetes ⚠️ (portable in principle; the surrounding
                integrations are what actually bind you)
MEDIUM          managed queues, load balancers, IAM integration patterns
⚠️ HIGH         proprietary databases (DynamoDB, Spanner, Cosmos), serverless
                event architectures, ⚠️ the analytics stack, and IAM itself
⚠️ HIGHEST      DATA GRAVITY and TEAM EXPERTISE — the two nobody puts on the list
```
**⚠️ Multi-cloud is frequently proposed and rarely done well.** **The honest breakdown:**
- **⚠️ Multi-cloud for *resilience* mostly doesn't work as intended.** **You end up with
  the lowest common denominator of both platforms, double the operational surface, a team
  expert in neither, and — critically — an active/passive setup whose failover has never
  been tested and therefore won't work.**
- **⚠️ Multi-cloud that DOES work is usually best-of-breed per workload**: **analytics on
  BigQuery, the enterprise estate on Azure, a product on AWS.** **Separate workloads,
  separate teams, deliberate seams.**
- **⚠️ Multi-cloud as negotiating leverage is real** — **credible ability to move improves
  your terms even if you never move** (see a business reference §12 on BATNA).
- **⚠️ Much multi-cloud is not chosen. It's acquired** — through mergers, shadow IT, and
  SaaS vendors running elsewhere. **Reported multi-cloud adoption figures largely
  describe this, not deliberate architecture.**

**⚠️ The pragmatic middle**: **keep the portable things portable — containers, standard
SQL, IaC, and avoid gratuitous proprietary dependencies — while using managed services
where they genuinely earn their lock-in.** ⚠️ **Refusing all proprietary services to
preserve optionality means rebuilding what you're already paying for, which is usually the
more expensive mistake.**

---
