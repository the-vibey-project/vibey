---
id: skill-2-process-model-ipc-and-sandboxing-d1fb104f6f
purpose: 2 process model ipc and sandboxing
source: src/vibey_tools/skills/plugins/web-browser-development/skills/browser-engine-architecture-and-networking/SKILL.md
requires: ["skill-1-the-engine-landscape-9fffda8f79"]
links: ["skill-3-networking-326883cfb7"]
---

## §2. Process Model, IPC, and Sandboxing

### 2.1 Why multiple processes

**[DURABLE]** Chrome's 2008 multi-process design solved three problems at once and every
engine has since converged on it: **stability** (a renderer crash kills a tab, not the
browser), **performance** (parallelism across cores; one page's main thread can't block
another's), and — the one that turned out to matter most — **security** (renderers run in
a restricted sandbox with no direct filesystem, network, or device access).

**The Chromium terminology, precisely, because people conflate these:**
- **Multi-process architecture** — the broad design choice of separate OS processes.
- **Site Isolation** — the stricter *policy* that a renderer process is locked to a single
  site or origin, including for iframes.
- **Sandboxing** — the OS-level restriction layer limiting what a compromised process can
  do *after* code execution.

### 2.2 Site Isolation

**[ENGINE, and the reference design]** Chrome enabled Site Isolation by default in Chrome
67, motivated directly by **Spectre** (§8.6 → `browser-security-and-privacy`). Its two halves:
1. **Locked renderer processes** — a renderer may contain documents and workers from only
   one site or origin, *even in iframes*. Getting this right required solving genuinely
   hard cases: `srcdoc` URLs, `data:` URLs, base URLs, and sandboxed frames (Chrome enabled
   **isolated sandboxed frames** by default in 2024, adding a process boundary between an
   origin and the untrustworthy content it hosts).
2. **Browser-enforced restrictions** — the privileged browser process validates every IPC
   message and refuses cross-site data requests (`ChildProcessSecurityPolicy::
   CanAccessDataForOrigin` is the canonical check). This is what stops a *fully compromised*
   renderer from simply asking for another site's cookies.

**Firefox's equivalent is Project Fission**, which isolates at the **origin** boundary
rather than the site boundary — stricter than Chrome's default, because Chrome's site
boundary does not separate `mail.example.com` from `pay.example.com`.

**[DURABLE] The security payoff, stated precisely:** under Site Isolation, an attacker with
full remote code execution inside a renderer still cannot read another site's DOM, cookies,
or JS heap, because **those objects are simply not in that process's address space**. To
reach them the attacker must chain a second exploit — a browser-process privilege
escalation or a kernel sandbox escape. That's the whole design.

> **⚠️ GOTCHA — the cost is memory and process count, and it binds hardest on mobile.**
> Chromium's own security documentation is unusually candid: *"we are reaching the limits
> of sandboxing and site isolation. A key limitation is that the process is the smallest
> unit of isolation, but processes are not cheap. Especially on Android, using more
> processes impacts device health overall: background activities get killed with far
> greater frequency."* It also notes that processes still share information about multiple
> sites — the network service is one large C++ component parsing complex input from
> anyone on the network. **Process isolation has a ceiling, and the industry has hit it.**

### 2.3 Sandboxing, per platform

| Platform | Mechanism |
|---|---|
| **Windows** | Restricted token + job object + alternate desktop + **AppContainer** + **Win32k lockdown** (blocking direct access to the win32k syscall surface, historically a huge kernel attack surface) |
| **macOS** | Seatbelt (`sandbox_init`) profiles |
| **Linux** | **seccomp-bpf** syscall filter + user namespaces + `setuid` sandbox (legacy) |
| **Android** | Process sandbox reinforced by **SELinux** policy; isolated processes |
| **iOS** | System sandbox; JIT requires special entitlement — hence the WebKit mandate historically |

**[DURABLE] Renderers must be denied filesystem, network, and device access.** All of it
routes through brokered IPC to the browser process, which validates. Any capability you
hand directly to the renderer is a capability the attacker gets.

### 2.4 IPC design

**[DURABLE] The IPC layer is a security boundary, and it must be treated like a network
protocol from a hostile peer.** The rules:
- **Validate everything in the privileged process.** Never trust a size, an index, a
  handle, or — especially — an *origin* claimed by a renderer.
- **Capability-style interfaces** (Chromium's **Mojo**) beat giant switch statements on
  message IDs: a renderer holds a pipe to a specific service with a specific interface,
  rather than the ability to send any message.
- **Fuzz the IPC surface.** It is the highest-value fuzzing target in the browser.
- Mind the **serialization** cost: IPC on the rendering hot path shows up directly in
  frame time.

---
