---
id: skill-10-databases-1e4a91b933
purpose: 10 databases
source: src/vibey_tools/skills/plugins/aws-gcp-azure-deep-dive/skills/hyperscaler-storage-databases-analytics-and-observability/SKILL.md
requires: ["skill-9-storage-1db28501f2"]
links: ["skill-11-analytics-e379175f99"]
---

## §10. Databases

```
Relational     RDS / Aurora     Azure SQL / Flexible Server  Cloud SQL / AlloyDB
Distributed    ⚠️ Aurora DSQL / Spanner-likes  Cosmos DB    ⚠️ SPANNER
NoSQL doc/kv   DynamoDB         Cosmos DB          Firestore / Bigtable
Cache          ElastiCache      Azure Cache        Memorystore
Graph/other    Neptune, Timestream  various        Bigtable
```
**⚠️ Spanner and Cosmos DB are genuinely distinguishing**: **globally distributed with
strong consistency (Spanner) or tunable consistency (Cosmos).** ⚠️ **Both are expensive
and both solve a problem most applications do not have.**
**⚠️ DynamoDB's constraint is its virtue**: **single-digit-millisecond at any scale,
provided you design the access patterns first.** ⚠️ **It punishes relational thinking
severely — if you find yourself wanting a join, you modelled it wrong or picked the wrong
store.**
**⚠️ The managed-database tradeoff, stated plainly**: **you give up superuser access, some
extensions, and fine-grained tuning, in exchange for backups, patching, failover and
replication you'd otherwise build.** **For most teams that's the right trade** —
⚠️ **but check extension support and version currency before committing, because the gap
between "PostgreSQL" and "managed PostgreSQL" is where migrations stall.**

---
