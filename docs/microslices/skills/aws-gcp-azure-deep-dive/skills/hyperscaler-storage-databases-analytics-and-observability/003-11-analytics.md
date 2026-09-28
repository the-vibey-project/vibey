---
id: skill-11-analytics-e379175f99
purpose: 11 analytics
source: src/vibey_tools/skills/plugins/aws-gcp-azure-deep-dive/skills/hyperscaler-storage-databases-analytics-and-observability/SKILL.md
requires: ["skill-10-databases-1e4a91b933"]
links: ["skill-12-ai-ml-services-607931e3af"]
---

## §11. Analytics

```
Warehouse      Redshift         ⚠️ Fabric / Synapse    ⚠️ BIGQUERY
Lake           S3 + Glue + Athena  ADLS + Fabric      GCS + BigLake
ETL            Glue             Data Factory        Dataflow / Dataproc
Streaming      Kinesis / MSK    Event Hubs          Pub/Sub + Dataflow
BI             QuickSight       ⚠️ Power BI          Looker
```
> **⚠️ BigQuery is GCP's strongest product and the clearest reason to choose GCP.**
> ⚠️ **Genuinely serverless — no cluster to size, no nodes to manage, separated storage
> and compute from the start.** **Redshift has moved toward this with serverless options
> but carries its cluster heritage; Fabric is Microsoft's consolidation attempt and is
> capable but has been a moving target.**
> **⚠️ BigQuery's cost model is the thing to watch**: **on-demand pricing charges per byte
> SCANNED, so an unpartitioned table plus `SELECT *` is a genuinely expensive mistake.**
> **Partition, cluster, select only the columns you need, and consider capacity pricing
> above steady volume** (see a reporting/dashboards reference §7).

**⚠️ Power BI is a real reason organizations choose Azure** — **licensing bundled with
Microsoft 365 makes it the default in a large share of enterprises regardless of where
the data lives.**

---
