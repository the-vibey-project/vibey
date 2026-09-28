# Context microslice contract

This is the implementation contract for proposed doctrine 10.k and ADR-0075.
It applies to every skill, agent guide, ADR, bot script, prompt, ledger and
specification that may be loaded into a finite context window.

Each slice answers one question or performs one operation and carries a stable
identity, one purpose, provenance, bounded size, and explicit `requires` and
`links` relationships. Retrieval starts at the matching slice, follows required
safety and acceptance slices, records selected IDs and measured size, and follows
optional links only when needed. If the closure exceeds its budget, split or
park; never silently truncate requirements, safety constraints, evidence, or
uncertainty.

Migration is incremental. Existing large surfaces remain authoritative until
replacement slices link back to them. New and materially changed content adopts
the contract immediately. Summaries are routing aids, not source evidence.

## Conversion operation

The offline converter preserves the source and emits numbered slices plus an
index:

```bash
python3 src/vibey_tools/skills/tools/slice_markdown.py \
  path/to/source.md path/to/microslices --level 2
```

For the authoritative skills tree, the resumable batch form is:

```bash
python3 src/vibey_tools/skills/tools/slice_markdown.py \
  --all-root src/vibey_tools/skills/plugins \
  --all-output docs/microslices/skills --level 2
```

It writes one `index.json` per skill and a top-level `manifest.json`; rerunning
it deterministically reconciles the generated tree without changing any source.

The generated boundaries require review; mechanical splitting is not itself a
semantic quality claim. The context engine remains the preferred family
implementation for bounded retrieval.
