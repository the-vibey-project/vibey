---
id: skill-20-method-333bae37a2
purpose: 20 method
source: src/vibey_tools/skills/plugins/reporting-and-dashboards/skills/reporting-reference/SKILL.md
requires: ["skill-19-quick-reference-bb6e6ec4cc"]
links: []
---

## §20. Method

**§1–§15 → `reporting-architecture-modelling-and-aggregation-traps`, `reporting-semantic-layer-time-and-performance`, `reporting-dashboard-design-charts-and-alerting`, `reporting-access-control-embedded-and-testing` and §17 rest on stable material** — **Kimball's dimensional modelling (1996),
Cleveland and McGill's perceptual work (1984), Few's dashboard design, and the
aggregation and additivity rules, which are properties of arithmetic rather than of
tools.** ⚠️ **The fan-out trap in §3.1 → `reporting-architecture-modelling-and-aggregation-traps` was a problem in 1998 and it is a problem in every
BI tool shipping today.** **None of that needed verification.**

**Two searches were run in August 2026**, on **the semantic layer market** and
**text-to-SQL accuracy.**

**Confidence.** **High** in §1–§15 → `reporting-architecture-modelling-and-aggregation-traps`, `reporting-semantic-layer-time-and-performance`, `reporting-dashboard-design-charts-and-alerting`, `reporting-access-control-embedded-and-testing`. ⚠️ **§3 → `reporting-architecture-modelling-and-aggregation-traps` is the section I'd most want read — those bugs
are common, they produce plausible wrong numbers rather than errors, and I have seen every
one of them described as a mystery rather than as the well-known trap it is.**

⚠️ **Two sourcing cautions.**

**§16.1's landscape is drawn largely from vendor and vendor-adjacent comparison content**,
and ⚠️ **almost every "best semantic layer tools 2026" article is published by a company
selling one.** **I have reported the structural facts that recur across independent
sources** — the four-way market split, dbt Semantic Layer's adoption position, Cube's
headless architecture and Apache-2.0 core, ⚠️ **the Snowflake (March 2026) and Databricks
(April 2026) GA dates, OSI's January 2026 finalization, and the dbt-Fivetran merger** —
**and I have deliberately included the trade-offs those articles tend to bury**,
especially **the dbt Cloud dependency for the serving layer** and **the adoption problem,
which the most candid source frames as the real reason semantic layers stall.**

⚠️ **§16.2 I have grounded deliberately in peer-reviewed benchmark literature rather than
vendor claims, because the gap between the two is the whole story.** **The Spider 1.0 →
BIRD → Spider 2.0 progression from ~91% to ~73% to ~21% comes from the academic papers
themselves**, ⚠️ **including their own explicit caveat that cross-benchmark figures are
not directly comparable and that BIRD contains substantial annotation errors.** **The
CACM practitioner piece and the BEAVER and LinkedIn findings independently corroborate the
enterprise gap.**

⚠️ **I want to be clear about my own position there**: **the semantic-layer-plus-LLM
argument is one that semantic layer vendors have an obvious commercial interest in
making.** **I think the mechanism is nonetheless right — constraining a model to governed
metric definitions with declared joins genuinely removes classes of error** — **but the
supporting numbers in this document come from the benchmark literature, not from the
vendors making that argument.** **The defensible claim is a productivity tool over curated
data requiring review, not a replacement for analysts.**
