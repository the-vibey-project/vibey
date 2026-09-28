---
id: skill-3-workflow-automation-c9b091d735
purpose: 3 workflow automation
source: src/vibey_tools/skills/plugins/low-code-no-code/skills/lowcode-landscape-automation-and-ai-generation/SKILL.md
requires: ["skill-2-education-and-block-based-tools-c07a64b434"]
links: ["skill-4-ai-app-generation-the-disruption-f4d4b055f6"]
---

## §3. Workflow Automation

**[DURABLE] The tier most working engineers will actually touch**, because it sits exactly
where "write a script" and "buy a product" overlap.

| Tool | Position |
|---|---|
| **Zapier** | ⚠️ **The easiest, the most integrations, and the most expensive at volume.** Per-task pricing |
| **Make** (ex-Integromat) | More powerful visual model, better value at volume, steeper |
| **n8n** | ⚠️ **Self-hostable, developer-oriented, code nodes when you need them.** §3.1 |
| **Power Automate** | The default if you're already Microsoft-shop; deep M365 integration |
| **Activepieces, Windmill, Node-RED, Huginn** | ⚠️ **Genuinely open-source alternatives** (§3.1's licensing point) |
| **Temporal, Airflow, Prefect, Dagster** | ⚠️ **Not low-code — the code-first answer** when durability and complexity matter |

### 3.1 ⚠️ n8n and the "open source" question

**[VERSIONED] n8n is the developer favourite in this tier and its licence is the first
thing to understand**, because the confusion is widespread and consequential.

**Scale**: **~127,000 GitHub stars by early 2026**, **230,000+ active users**, **2,200+
community extensions**, **6,500+ community workflow templates**. Funding: **€55M Series B
(March 2025, Highland Europe)**, then **$180M (October 2025, led by Accel with Nvidia's
NVentures) at a reported $2.5B valuation** — with ARR reported around $40M by mid-2025 and
growing roughly 5× year on year.

> **⚠️ GOTCHA — n8n is not open source by the OSI definition, and this matters
> commercially.** It uses the **Sustainable Use License** (introduced March 2022,
> replacing Apache 2.0 + Commons Clause), which n8n describes as **"fair-code."**
>
> **What you can do**: read the source, modify it, self-host, and run it **for internal
> business purposes** — free, indefinitely.
> **⚠️ What you cannot do**: **white-label n8n and make it available to customers for
> payment, or host n8n and grant users access for money.** n8n names those two examples
> explicitly. There is also a **separate n8n Enterprise Licence** covering
> enterprise-marked code in the public repo — ⚠️ **a public repository does not mean every
> part is community-licensed.**
>
> **The practical line: legally clean while automation stays inside the organisation;
> blocked the moment automation becomes a value proposition for external users.**
> Note also there's **no free cloud tier beyond a 14-day trial** — the free path is
> self-hosting, which means you run, patch and scale it.
>
> **If you need genuine OSI-licensed workflow automation**, the alternatives are
> **Node-RED, Activepieces, Windmill, and Huginn** — and "open source n8n alternative" is
> one of the most-searched phrases in this category for exactly this reason.

**[DURABLE] The honest assessment of this tier**: excellent for glue — API-to-API,
notification routing, scheduled data movement, approval flows, AI-agent orchestration.
⚠️ **Weak at**: complex branching logic (visual flows become unreadable fast), version
control and code review, testing, and anything requiring durable execution semantics.
**When a workflow exceeds roughly 20–30 nodes or needs real error compensation, you have
outgrown the tier** — move to Temporal, Airflow, or code.

---
