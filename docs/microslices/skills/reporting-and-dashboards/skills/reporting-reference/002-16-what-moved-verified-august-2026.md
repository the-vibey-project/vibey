---
id: skill-16-what-moved-verified-august-2026-b3232ed4e3
purpose: 16 what moved verified august 2026
source: src/vibey_tools/skills/plugins/reporting-and-dashboards/skills/reporting-reference/SKILL.md
requires: ["skill-15-misconceptions-9950dc90c3"]
links: ["skill-17-numbers-36a88d0931"]
---

## §16. What Moved — verified August 2026

### 16.1 The semantic layer
**⚠️ It stopped being an optional BI feature.** **Gartner elevated it to essential
infrastructure in its 2025 Hype Cycle for BI and Analytics**, and the market has
consolidated around a handful of options.

**⚠️ The market splits four ways, and the split is the useful framing:**
- **Standalone/vendor-neutral** — **dbt Semantic Layer (MetricFlow)**, ⚠️ **described
  across multiple sources as the most widely adopted vendor-neutral approach**; **Cube**
  (⚠️ **headless and API-first — SQL, REST, GraphQL, MDX — with an Apache-2.0 open-source
  core, and the usual pick for embedded analytics and products**); **AtScale**.
- **Warehouse-native** — ⚠️ **and this is the genuinely new part: Snowflake Semantic Views
  reached SQL-query GA in March 2026, and Databricks Metric Views reached GA in April
  2026.**
- **BI-native** — **LookML** (⚠️ **and it's worth noting Google's $2.6bn Looker
  acquisition is widely read as having been for LookML, not the visualization layer**),
  **Power BI semantic models**, **Tableau Semantics**.
- **Context/catalog layers** sitting above them.

**⚠️ Two structural developments:**
- **The Open Semantic Interchange (OSI)** specification — ⚠️ **launched with dbt Labs and
  Snowflake backing and reported as finalized in January 2026** — **a vendor-neutral
  standard for moving semantic definitions between tools and AI systems.** ⚠️ **If it
  gains adoption it addresses the portability problem, which is currently the main
  argument against committing to any one layer.**
- **dbt Labs and Fivetran merged**, ⚠️ **reported as completed in April 2026** —
  consolidating ingestion, transformation and semantic modelling under one company.
  ⚠️ **Whether that's convenience or lock-in depends on how much you value platform
  independence, and it's a legitimate open question rather than a settled one.**

> **⚠️ GOTCHA — the trade-offs are concrete and the marketing obscures them.**
> ⚠️ **The dbt Semantic Layer requires dbt Cloud: MetricFlow is open source, but the
> serving layer that makes metrics queryable is a Cloud feature, so dbt Core alone won't
> do it.** **Warehouse-native layers are convenient right up until you need embedded,
> multi-warehouse, or agent access.** **BI-native layers are strongest inside their own
> platform, and portability is the price.**
>
> ⚠️ **And the honest constraint that applies to all of them, which one source states
> well: adoption fails on the unglamorous work** — **bootstrapping the model, keeping
> definitions consistent as systems evolve, and migrating logic as tools change.** **A
> technically correct metric definition that nobody owns, reviews or tests is not a
> solution.** ⚠️ **Choose the layer that matches how your team already ships, not the one
> with the best architecture diagram.**

### 16.2 ⚠️ Natural-language querying — read the benchmarks, not the demos
**⚠️ This is the clearest gap between marketing and evidence in the current BI market, and
the research literature is unusually blunt about it.**

**The benchmark progression tells the story:**
```
Spider 1.0    ⚠️ ~91% execution accuracy — 200 clean databases, 10–20 tables
BIRD          ⚠️ ~73% — "dirty" databases, real content, external knowledge needed
Spider 2.0    ⚠️ ~21% — ENTERPRISE conditions: 3,000+ column schemas,
              multiple SQL dialects, multi-step agentic workflows
```
> **⚠️ GOTCHA — that is not a gentle degradation, it is a cliff, and it is the number that
> matters for your organization.** ⚠️ **Frontier models reported at 17–21% on Spider 2.0
> against ~91% on original Spider.** **Your warehouse looks like Spider 2.0, not Spider
> 1.0.**

**⚠️ Why the benchmarks flatter, and each reason is independently documented:**
- **⚠️ Benchmark data is in the training corpus.** **A senior practitioner's summary in
  CACM puts it plainly: the data is "in the pile," and an LLM finds what it has seen
  before. Real warehouses sit behind enterprise access controls and are not in any
  training set.**
- **⚠️ BIRD itself has annotation errors** — **one analysis reports 52.8% annotation
  errors in certain subsets, with performance shifting between −3% and +31% after
  correction.** ⚠️ **Cross-benchmark numbers are not directly comparable, and the
  literature says so explicitly.**
- **⚠️ Real schemas are far larger.** **Even Spider 2.0 averages ~52 tables and ~800
  columns per database; enterprise warehouses exceed this.** **The BEAVER benchmark, built
  from actual data warehouses, finds off-the-shelf LLMs perform poorly on real enterprise
  data.**
- **⚠️ Production adds problems benchmarks don't model** — **LinkedIn's deployment study
  identifies ambiguous user intent, evolving schemas, and the need for explanation
  alongside results.**

**⚠️ The failure mode is the important part, and it's the same one as §3 → `reporting-architecture-modelling-and-aggregation-traps`**: **a wrong query
that runs successfully and returns a plausible number.** ⚠️ **Silent, scalable error** —
which is exactly why this belongs in the same document as the fan-out trap.

**⚠️ What actually helps, and it's the §5 → `reporting-semantic-layer-time-and-performance` argument again**: **point the model at a
governed semantic layer rather than raw tables.** **Metric definitions, declared joins,
and enforced row-level security constrain what the model can get wrong**, and ⚠️ **the
consistency test is the useful one to run: ask "total revenue last quarter" and then
"revenue growth quarter-over-quarter" and check the answers are mathematically
consistent.** **Systems where the calculation shifts with phrasing fail on anything
business-critical.**

⚠️ **Note the incentive structure when reading this material**: **semantic-layer vendors
have an obvious interest in the "agents need governed metrics" argument, and I've leaned
on the peer-reviewed benchmark literature rather than vendor blogs for the numbers.**
**The mechanism they propose is nonetheless well-supported.**

**⚠️ The defensible position**: **natural-language querying is a genuine productivity tool
over curated, governed data, and it is not a replacement for analysts or for a modelled
warehouse.** **Treat generated SQL as a draft requiring review**, ⚠️ **especially for
financial or executive reporting where a silently wrong number is expensive.**

---
