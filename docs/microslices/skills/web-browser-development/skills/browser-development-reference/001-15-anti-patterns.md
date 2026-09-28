---
id: skill-15-anti-patterns-3170c11eb6
purpose: 15 anti patterns
source: src/vibey_tools/skills/plugins/web-browser-development/skills/browser-development-reference/SKILL.md
requires: []
links: ["skill-16-contested-questions-498f11528f"]
---

## §15. Anti-Patterns

| Anti-pattern | Why | Instead |
|---|---|---|
| Trusting an origin claimed by a renderer | Compromised renderer = full cross-site read | Re-derive and validate in the browser process (§8.4 → `browser-security-and-privacy`) |
| Giving a renderer direct file/network/device access | Removes the sandbox's entire point | Broker through validated IPC |
| Unvalidated sizes/indices/handles over IPC | Memory corruption in the privileged process | Validate every field; fuzz the surface |
| Custom HTML error recovery | Compatibility divergence from the whole web | Implement the spec algorithm exactly (§4.1 → `browser-rendering-pipeline`) |
| Left-to-right selector matching | Pathological performance | Right-to-left + bloom filters (§5.2 → `browser-rendering-pipeline`) |
| Recomputing all style on any mutation | Jank | Invalidation sets (§5.3 → `browser-rendering-pipeline`) |
| Mutable layout tree holding inputs and outputs | Unpredictable incremental layout | Immutable fragment tree (§6.2 → `browser-rendering-pipeline`) |
| Doing scroll or transform animation on the main thread | Jank whenever JS is busy | Property trees + compositor thread (§6.1 → `browser-rendering-pipeline`) |
| `will-change` on everything | GPU memory exhaustion | Layerize deliberately |
| Interleaving geometry reads and style writes | Forced synchronous layout, N× cost | Batch reads, then writes (§7.3 → `browser-rendering-pipeline`) |
| Sniffing content into an executable type | XSS vector | Honour `nosniff`; restrict sniffing |
| Shipping an XSS filter as a security boundary | Bypassable; introduces its own bugs; all were removed | CSP + Trusted Types (§8.3 → `browser-security-and-privacy`) |
| Unpartitioned storage or cache | Cross-site tracking and timing side channels | Partition everything by top-level site (§9.2 → `browser-security-and-privacy`) |
| High-resolution timers plus shared-process secrets | Spectre | Coarsen timers; isolate by site (§8.6 → `browser-security-and-privacy`) |
| Adding a capability API without an entropy review | Permanent fingerprinting surface | Review entropy and permission model together (§9.3 → `browser-security-and-privacy`, §11 → `browser-extensions-platform-and-standards`) |
| Shipping a web feature without an exit plan | You can never remove it | Origin trial + use counters first (§14 → `browser-extensions-platform-and-standards`) |
| Prefixed CSS properties | `-webkit-` became a de facto standard other engines had to implement | Flags and origin trials, never prefixes |
| Reverse-engineering another engine's quirks instead of specifying them | Perpetuates the divergence | Spec it, add WPT, take it to Interop (§13 → `browser-extensions-platform-and-standards`) |
| Treating accessibility as a post-architecture concern | It crosses the process boundary; retrofitting is expensive | Design the a11y tree with the process model (§12 → `browser-extensions-platform-and-standards`) |
| Assuming the network service is trusted | It parses hostile input for all sites at once | Sandbox and memory-harden it (§3.1 → `browser-engine-architecture-and-networking`) |

---
