---
id: skill-the-governing-rule-one-source-every-other-file-derived-6ecce3a212
purpose: the governing rule one source every other file derived
source: src/vibey_tools/skills/plugins/content-engineering-pipeline/skills/pipeline-serial-fiction-production/SKILL.md
requires: []
links: ["skill-the-per-unit-manifest-0dfb94338d"]
---

## The governing rule: one source, every other file derived

The draft of a unit is the only file anyone writes for that unit. Everything
downstream is generated from it, and the generation is provable:

```text
drafts ──► lint ──► per-unit manifest ──► typeset units ──► manuscript chapters ──► books
              │            │                    │                   │                │
           rules as     parameters        regenerate to a      regenerate to a    release
            a gate      in a file         temp dir, compare    temp dir, compare   gates
```

Every arrow needs three things:

1. **A generator**: a command, not a procedure. If building a unit requires
   remembering which arguments to pass, the arguments belong in a file.
2. **A `--check`**: regenerate into a temporary folder and fail on any
   difference from what is committed, naming the unit and the command that fixes
   it.
3. **A test that runs the check without the heavy toolchain**, so the chain is
   exercised on every change in seconds and CI fails before LaTeX starts.

Do not compare bytes when a build embeds a document ID or timestamps. Compare
what the reader sees (page count, text per page), and normalise what the reader
cannot see (unused macro definitions, trailing blank lines) explicitly, with the
reason written next to the normaliser, so the check never hides a real change.
