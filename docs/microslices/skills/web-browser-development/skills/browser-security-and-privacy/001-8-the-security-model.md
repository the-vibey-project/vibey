---
id: skill-8-the-security-model-77b0564f7a
purpose: 8 the security model
source: src/vibey_tools/skills/plugins/web-browser-development/skills/browser-security-and-privacy/SKILL.md
requires: []
links: ["skill-9-privacy-and-anti-tracking-5d20a30fa6"]
---

## §8. The Security Model

### 8.1 Same-origin policy

**[DURABLE] The foundational rule: an origin is the (scheme, host, port) triple, and code
from one origin cannot read data from another.** Everything else in web security is an
exception to, or a reinforcement of, this.

The historically-permitted cross-origin operations are the source of most web
vulnerabilities: you may **embed** cross-origin (images, scripts, iframes, styles) and you
may **send** cross-origin requests (forms) — you just can't *read* the results. CSRF exists
because sending is allowed with ambient credentials; XSSI and side-channel leaks exist
because embedding is allowed.

### 8.2 The mitigation alphabet

| Mechanism | Does what |
|---|---|
| **CORS** | Server opt-in to cross-origin *reads*. Simple vs. preflighted requests; `Access-Control-Allow-*` |
| **CSP** | Author-declared allow-list of sources and behaviours. **Nonce/hash-based CSP with `strict-dynamic`** is the modern form; host allow-lists are widely bypassable |
| **Trusted Types** | Prevents DOM XSS structurally by requiring typed objects rather than strings at injection sinks. **Reached Baseline in February 2026** |
| **SameSite cookies** | CSRF defence; `Lax` by default in most engines |
| **`__Host-`/`__Secure-` prefixes** | Cookie integrity guarantees |
| **HSTS**, **CT**, **CAA** | Transport and PKI integrity |
| **Subresource Integrity** | Hash-pinned third-party scripts |
| **COOP / COEP / CORP / CORB-ORB** | Cross-origin isolation and read blocking (§8.6) |
| **Permissions Policy** | Delegating or denying powerful features per-frame |
| **Sandbox attribute / `sandbox` CSP** | Capability reduction for embedded content |
| **Secure contexts** | Powerful APIs restricted to HTTPS |

### 8.3 XSS, still

**[DURABLE] XSS remains the dominant web vulnerability class, and the browser's role is
to make it structurally impossible rather than to filter it.** The history is
instructive: engines shipped XSS *auditors* (Chrome's XSS Auditor, IE's XSS Filter), and
**all of them were removed** — they were bypassable, they introduced their own
vulnerabilities, and they caused false positives that broke sites. The lesson generalizes:
**a filter that must guess intent on a Turing-complete input is not a security boundary.**
Trusted Types and CSP are the structural replacements.

### 8.4 Never trust the renderer

**[DURABLE] The single most important implementation rule in browser security.** A
compromised renderer will lie about its origin, its URL, its permissions, and the contents
of any structure it hands you. Every privileged operation must be re-derived and
re-validated in the browser process from state the browser process owns.

**Chromium is now moving this enforcement into Rust**: the security team has been
**migrating `ChildProcessSecurityPolicy` to Rust** with a live Canary experiment, both for
memory safety and to strengthen the security-relevant invariants that Site Isolation
depends on — and has an initial **Rust Mojo client** enabling services to be implemented
fully in Rust.

### 8.5 Memory safety

**[VERSIONED — the most active area of browser security engineering.]** Roughly 70% of
serious browser vulnerabilities have historically been memory-safety bugs. The 2026 state
of the art, using Chrome as the documented example:
- **MiraclePtr / BackupRefPtr** — reference-counted raw pointers that neutralize
  use-after-free by keeping the allocation quarantined. Already credited with a major UAF
  reduction; **being expanded to Skia, ANGLE, Dawn, C++ iterators, and `std::` containers**.
- **MiracleObject** — being deployed on the **GPU main thread**, targeting up to **90%** of
  UAFs there, explicitly trading local runtime performance for temporal safety.
- **PartitionAlloc** — a hardened allocator; now enabled in Skia.
- **"Spanification"** — a systematic effort to eliminate out-of-bounds bugs by replacing
  raw pointer+length pairs with bounds-checked spans.
- **UBSan `-fsanitize=return` enabled by default in release builds**, with plans to expand.
- **Rust** — a centralized Rust SDK, new modular components written in Rust, and the
  `ChildProcessSecurityPolicy` migration above. The stated architectural payoff is
  significant: *writing new components in Rust lets complex features run inside
  high-privilege processes without the performance penalty of sandboxing* — i.e. **memory
  safety buys back architectural freedom that process isolation was spending.**
- Google has also stated it is **exploring implementing the browser's top-level UI in
  HTML/CSS/TypeScript** to reduce dependence on C++ frameworks.
- **AI-assisted vulnerability finding is now real**: Google built an agent harness in early
  2026 that found a sandbox escape — a compromised renderer tricking the browser into
  reading local files — that **had survived in the codebase for more than 13 years**.

**Engine comparison [ENGINE]:** Gecko relies on Rust for newer components (Stylo,
WebRender) but older C++ doesn't benefit from a BackupRefPtr equivalent, and mozjemalloc
is less hardened than PartitionAlloc. WebKit leans on OS integration — **pointer
authentication on ARM64**, strict code signing on iOS — and mostly uses system allocators.

### 8.6 Spectre and the transient-execution problem

**[DURABLE, and the reason the architecture looks like it does.]** Spectre showed that
**any** high-resolution timer plus speculative execution lets attacker JS read arbitrary
memory *in its own process*. There is no software fix for the CPU behaviour. So the
browsers' response was architectural: **if the secret isn't in the process, it can't be
read.** That is Site Isolation's origin story.

The supporting mitigations: reduced timer resolution and jitter, disabling
`SharedArrayBuffer` unless **cross-origin isolated** (COOP+COEP), **CORB/ORB** to stop
sensitive cross-origin responses from ever entering a renderer, and per-site process locks.

---
