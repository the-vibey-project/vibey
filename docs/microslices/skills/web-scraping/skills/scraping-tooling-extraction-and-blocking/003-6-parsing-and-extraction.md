---
id: skill-6-parsing-and-extraction-2d66e58407
purpose: 6 parsing and extraction
source: src/vibey_tools/skills/plugins/web-scraping/skills/scraping-tooling-extraction-and-blocking/SKILL.md
requires: ["skill-5-the-tool-ladder-4f25f53280"]
links: ["skill-7-why-you-re-getting-blocked-6d0991cc97"]
---

## §6. Parsing and Extraction

**Selectors**: **CSS selectors** for most work (readable, sufficient), **XPath** when you
need axes CSS can't express (`following-sibling`, `ancestor`, text-content matching).

**[DURABLE] Selector stability is what determines your maintenance burden**, and it's worth
deliberate thought:
```
✓ STABLE    semantic ids, data-* attributes, ARIA roles, schema.org markup,
            structural relationships to stable text labels
⚠️ FRAGILE  auto-generated class names (`css-1x7f2k9` — these change every build),
            deep positional paths (`div > div > div:nth-child(3)`),
            anything tied to visual layout
```
**Prefer anchoring to meaning rather than to position.** "The `<dd>` following the `<dt>`
containing 'Price'" survives a redesign that "the fourth div" does not.

**Always extract defensively**: assume any field may be missing, return `None` rather than
raising, **and record that it was missing** (§9 → `scraping-scale-reliability-and-data-quality`). And **normalize at extraction time** —
strip whitespace, parse dates into datetimes with timezones, convert prices to numbers
*with their currency*, resolve relative URLs against the base.

**[VERSIONED] LLM-assisted extraction** is now practical for messy or highly variable
pages, and tools like Firecrawl and various "AI scraping" products build on it. **⚠️ The
trade-offs are real**: cost per page, latency, non-determinism, and **hallucinated fields
that look plausible** — which is §9 → `scraping-scale-reliability-and-data-quality`'s failure mode with a new cause. **The defensible
pattern is LLM-assisted *selector generation* (deterministic at runtime) rather than
LLM-in-the-loop extraction**, plus validation on everything.

---
