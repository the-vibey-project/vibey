---
id: skill-operating-procedure-e187a550f6
purpose: operating procedure
source: src/vibey_tools/skills/plugins/content-engineering-pipeline/skills/pipeline-serial-fiction-production/SKILL.md
requires: ["skill-retrospective-lessons-made-executable-da1e7b396b"]
links: ["skill-references-0457168b07"]
---

## Operating procedure

1. Put the manifest, linter, generators and chain check in the repository
   before the second volume, not after the third.
2. Before each batch, search the corpus; after it, record what it established.
3. Treat every hand edit of a generated file as a bug in a generator.
4. Make the chain check the first CI step after unit tests, and trigger CI on
   changes to the source directories.
5. Rebuild and read at least one rendered page of any new form.
6. Hand the author a short list of open decisions with each batch.
7. Release through `pipeline-book-release-engineering`, which owns the gates
   from a locked manuscript to evidence.
