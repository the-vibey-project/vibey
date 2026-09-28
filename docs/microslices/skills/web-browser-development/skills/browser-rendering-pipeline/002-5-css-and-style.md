---
id: skill-5-css-and-style-dd8f2a97f1
purpose: 5 css and style
source: src/vibey_tools/skills/plugins/web-browser-development/skills/browser-rendering-pipeline/SKILL.md
requires: ["skill-4-html-parsing-and-the-dom-e7947ec6a5"]
links: ["skill-6-layout-paint-and-compositing-762ef5074f"]
---

## §5. CSS and Style

### 5.1 The cascade

**[DURABLE] Style resolution is: for each element, find every declaration that applies,
sort by the cascade, and produce a computed value for every property.** The cascade order
(later wins):
```
1. origin & importance   user-agent < user < author < animations
                         < author !important < user !important < UA !important
                         < transitions
2. cascade layers        (@layer — later layers win within the same origin)
3. specificity           (id, class/attr/pseudo-class, type/pseudo-element)
4. order of appearance
```
Then **inheritance** for inherited properties, then computed → used → actual values.

**⚠️ Specificity is not a single number.** It's a 3-tuple compared lexicographically —
`(1,0,0)` beats `(0,99,99)`. Implementations that pack it into an integer eventually
overflow on pathological selectors, and real sites contain pathological selectors.

### 5.2 Selector matching, and why it's backwards

**[DURABLE] Match selectors right-to-left.** Given `div.container > p a`, an engine starts
at the candidate `a` element and walks *up*, because matching left-to-right would require
descending the entire subtree of every `div.container`. This single fact explains most of
CSS performance advice.

Optimizations every engine implements: **bloom filters** for ancestor checks (cheap
"definitely not a match" rejection), **rule hashing** by rightmost simple selector
(id/class/tag buckets), **style sharing caches** for elements with identical inputs, and
**invalidation sets** — precomputed knowledge of which rules could possibly be affected by
a given class/attribute change, so a `classList.toggle` doesn't restyle the document.

**[ENGINE] Servo's Stylo** — parallel style resolution in Rust — is the notable
architectural departure, and it shipped in Firefox. Style is unusually parallelizable
because sibling subtrees are largely independent; layout is much less so.

### 5.3 Invalidation is the hard part

**[DURABLE] Computing style from scratch is easy. Knowing what to recompute when something
changes is where engines live or die.** A DOM mutation, a class change, a media-query
flip, a container resize, or a `:hover` must invalidate the minimum possible set. Getting
this wrong shows up as jank, not as incorrect rendering, which makes it hard to test and
easy to regress.

**Container queries and `:has()` made this dramatically harder** — both create
dependencies that flow *up* or *sideways* rather than down the tree, breaking the
assumption that style depends only on ancestors.

---
