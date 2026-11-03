---
id: skill-operating-procedure-96e9c803c0
purpose: operating procedure
source: src/vibey_tools/skills/plugins/content-engineering-pipeline/skills/pipeline-book-release-engineering/SKILL.md
requires: ["skill-retrospective-lessons-made-executable-d2068f6822"]
links: ["skill-references-7a159b3efc"]
---

## Operating procedure

1. Lock the manuscript and configuration; do not begin from an old output file.
2. Run the source audit and resolve every hard failure. Read warnings as a
   revision queue, not as decoration.
3. Run the release-readiness contract and resolve every hard failure or record
   the explicit platform/format exception.
4. Build PDF, cover, and EPUB in dependency order.
5. Render every page and inspect the contact sheets and representative full-size
   pages. Record human review.
6. Run the external retailer/previewer checks available for the intended format.
7. Write the manifest, compare artifact hashes to the reviewed files, and only
   then prepare the distribution handoff.
8. If a conflict, content edit, metadata edit, page repair, or cover repair
   occurs, invalidate the old manifest and rerun from Gate 0.

For repositories with a native command, use that command rather than copying
this sequence into a shell. In engineering-influence the canonical entry point
is `scripts/publish_book.py`; the skill supplies the method, while the
repository owns the implementation details and thresholds.
