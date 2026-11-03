---
id: skill-release-graph-45a35465c1
purpose: release graph
source: src/vibey_tools/skills/plugins/content-engineering-pipeline/skills/pipeline-book-release-engineering/SKILL.md
requires: ["skill-the-governing-rule-no-invisible-manual-state-a90d84f9d7"]
links: ["skill-gate-0-source-and-manuscript-audit-e7687b5dfd"]
---

## Release graph

The release command must own this dependency graph:

```text
source inventory and prose audit
        │
        ▼
release-readiness contract ──► metadata, research, pricing, format feasibility
        │
        ▼
print interior ──► PDF structural and folio checks
        │
        ▼
cover geometry/art ──► cover safe-area and legibility checks
        │
        ▼
reflowable EPUB ──► EPUB structure, navigation, links, and ZIP checks
        │
        ▼
all-page rendering ──► contact sheets and human visual review
        │
        ▼
release manifest ──► author approval and distribution handoff
```

When a title has more than one print interior, make the format matrix part of
the book configuration before building:

```text
locked source
   ├── standard interior ──► paperback cover geometry
   └── compact hardcover interior ──► hardcover cover geometry
   └── EPUB ──► ebook cover
```

Each interior is a format variant of the same source, never a manually edited
copy. The release manifest must record each variant's PDF path, page count,
hash, render report, and configured page-limit policy. A cover spine must read
the page count from the matching final interior; using the standard PDF's page
count for a compact hardcover is a release defect.

The order is load-bearing. A cover cannot know its print spine until the PDF
page count is final. An EPUB cannot embed its cover until the cover exists. A
table of contents cannot be trusted until typesetting has settled. A visual
review cannot be attached to the release until the exact artifact has been
rendered. Never parallelize these steps merely because the tools are available.
