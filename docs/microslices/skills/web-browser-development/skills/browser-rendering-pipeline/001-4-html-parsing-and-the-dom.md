---
id: skill-4-html-parsing-and-the-dom-e7947ec6a5
purpose: 4 html parsing and the dom
source: src/vibey_tools/skills/plugins/web-browser-development/skills/browser-rendering-pipeline/SKILL.md
requires: []
links: ["skill-5-css-and-style-dd8f2a97f1"]
---

## §4. HTML Parsing and the DOM

### 4.1 The parser must never fail

**[DURABLE] The HTML parsing algorithm is fully specified, including error recovery, and
you must implement it exactly.** This is unusual and important: HTML is not a grammar you
can choose how to recover from. The spec defines a tokenizer state machine plus a tree
construction stage with ~23 "insertion modes," and it defines the correct output for
*every* malformed input — including the famous **"adoption agency algorithm"** for
mis-nested formatting tags.

**Why it's specified this way**: before HTML5, every engine recovered differently, so
malformed pages (which is most pages) rendered differently everywhere. The spec codified
what browsers already did. **Deviating from it is a compatibility bug, not a design
choice.**

Other parser realities:
- **Speculative/preload scanning** — while the main parser is blocked on a synchronous
  script, a second scanner races ahead to find subresources and start fetching them. A
  large real-world performance win.
- **`document.write`** — can inject content into the token stream mid-parse. It is the
  single ugliest constraint on parser architecture and the reason streaming parsers have to
  be re-entrant.
- **Scripts block by default**; `async` and `defer` change the ordering guarantees.
  Getting the ordering exactly right is required for compatibility.

### 4.2 The DOM

A mutable tree with live collections, mutation observers, ranges, and shadow trees.
Implementation concerns that dominate:
- **Memory layout and node size** — multiplied by hundreds of thousands of nodes.
- **Live `NodeList`s and `HTMLCollection`s** — must reflect mutations, which means either
  recomputing or maintaining invalidation. A classic performance trap for both engine and
  page author.
- **Shadow DOM** — encapsulation boundaries that affect selector matching, event
  retargeting, and style scoping. Each of those is real work.
- **The JS binding layer** (§7.2) is where a surprising fraction of the complexity lives.

---
