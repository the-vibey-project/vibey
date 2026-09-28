---
id: skill-7-javascript-integration-aca3e44e21
purpose: 7 javascript integration
source: src/vibey_tools/skills/plugins/web-browser-development/skills/browser-rendering-pipeline/SKILL.md
requires: ["skill-6-layout-paint-and-compositing-762ef5074f"]
links: []
---

## §7. JavaScript Integration

### 7.1 The engine

V8 (Chromium), SpiderMonkey (Gecko, and Servo), JavaScriptCore (WebKit), LibJS (Ladybird).
All modern ones are **tiered**: interpreter → baseline JIT → optimizing JIT, with
type-feedback-driven speculation, guards, and **deoptimization** back to the interpreter
when a guard fails. **Hidden classes/shapes plus inline caches** are what make dynamic
property access fast, and are the biggest single idea in dynamic-language performance.

**⚠️ Note the design tension Ladybird surfaces:** it has argued for **no JIT**, on
security and complexity grounds — JITs are a huge exploit surface and require W^X gymnastics
— at an obvious performance cost. That's a real, live trade-off, not a settled question,
and it's the same trade Apple makes by restricting JIT entitlements on iOS.

### 7.2 Bindings — the underestimated layer

**[DURABLE] The DOM is C++; the DOM is also JavaScript objects. Reconciling those two
object models is a large, subtle subsystem.** WebIDL defines the interfaces; a code
generator produces the glue. The hard parts:
- **Cross-heap garbage collection cycles.** A DOM node references a JS event listener which
  closes over the DOM node. Neither collector alone can see the cycle. Solutions: Blink's
  **Oilpan** (tracing GC for C++ DOM objects, unified with V8's collector), Gecko's
  cycle collector. **Getting this wrong means leaking every page the user visits.**
- **Wrapper lifetime and identity** — the same DOM node must yield the same JS object every
  time.
- **Security checks on every cross-origin access** — a `window` reference across origins
  exposes a tiny allow-list, and every access must be checked.
- **The cost of crossing the boundary** is real; hot DOM APIs are why engines invest in
  fast paths.

### 7.3 The event loop and rendering lifecycle

**[DURABLE] Exactly one specification governs when things happen, and page-visible
behaviour depends on it:**
```
run a task (one macrotask: event, timer, network callback)
  → drain the MICROTASK queue completely (promises, MutationObserver)
    ⚠️ microtasks that enqueue microtasks can starve the loop forever
→ if it's time to render:
     run rAF callbacks
     run ResizeObserver / IntersectionObserver
     update rendering: style → layout → paint → commit
→ idle callbacks (requestIdleCallback) if time remains
```
**⚠️ Forced synchronous layout ("layout thrashing")** — reading a geometry property
(`offsetHeight`, `getBoundingClientRect`) after a write forces layout *immediately*,
mid-task. Interleaving reads and writes in a loop turns one layout into N. This is the
single most common page-performance bug, and the engine's only defence is to expose it in
DevTools.

**Scheduling** is now a first-class engine concern: task prioritization, `scheduler.yield()`,
`isInputPending`, long-task attribution, and — the metric that made all of this visible —
**INP** (Interaction to Next Paint), which measures the *full* interaction lifecycle rather
than just input delay.
