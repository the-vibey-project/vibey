---
id: skill-10-storage-and-operations-e9d31110c5
purpose: 10 storage and operations
source: src/vibey_tools/skills/plugins/web-scraping/skills/scraping-scale-reliability-and-data-quality/SKILL.md
requires: ["skill-9-data-quality-aacb2108bb"]
links: []
---

## §10. Storage and Operations

**Format by purpose**: JSON/JSONL for raw and semi-structured; **Parquet** for analytics
(columnar, compressed, and far faster to query); a relational database for
relationships and deduplication; object storage for raw HTML archives; a vector store only
if you're doing retrieval (§12 → `scraping-ethics-ai-corpora-and-site-defense`).

**[DURABLE] Design for change detection, not just snapshots.** Most scraping value comes
from *what changed* — price movements, new listings, removed items. That means either
storing versions with valid-from/valid-to, or storing a content hash per record and
recording transitions.

**Schema evolution**: sites add and remove fields, so store the raw payload alongside the
parsed record and **make your schema additive**.

**Operational monitoring**: success rate by domain, latency, block/CAPTCHA rate,
records-per-run against baseline, **field-level null rates** (§9), cost per record, and
queue depth. **Alert on trends, not just failures** — a slow decline in fields extracted
is the signal that matters.

**Legal and ethical hygiene at the data layer**: know your **retention period** and
enforce it; **be able to delete a person's data on request** if you hold personal data
(GDPR/CCPA rights are not optional and "it's in a training set" is not an answer — §1.6 → `scraping-legal-landscape-and-permissions`);
document **provenance and legal basis per source**, because that documentation is what a
regulator will ask for and it is very hard to reconstruct retroactively.
