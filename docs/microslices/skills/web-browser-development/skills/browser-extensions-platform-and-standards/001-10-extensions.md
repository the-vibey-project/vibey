---
id: skill-10-extensions-f6bd740699
purpose: 10 extensions
source: src/vibey_tools/skills/plugins/web-browser-development/skills/browser-extensions-platform-and-standards/SKILL.md
requires: []
links: ["skill-11-storage-media-and-capabilities-49308be52b"]
---

## §10. Extensions

### 10.1 The architecture

Manifest, background context (persistent page → **service worker** in MV3), content scripts
(isolated worlds sharing a DOM), permission model, and — the crux — the network
interception API.

### 10.2 Manifest V3, precisely

**[VERSIONED, and the most politically charged topic in browser development.]**

MV3 replaced the **blocking `webRequest`** API — which let an extension observe and modify
each request in real time — with **`declarativeNetRequest`**, where the extension registers
static rules in advance and the browser applies them.

**Google's stated rationale**: security (no remote code execution, no arbitrary
request-time interception), privacy (the extension never sees request contents), and
performance.

**The consequences, as they actually landed:**
- **uBlock Origin's full version cannot be implemented under MV3.** Chrome users get
  **uBlock Origin Lite**, a reduced-functionality build; the author has stated there is no
  MV3 version of uBO proper.
- **MV3 caps the number of filtering rules** and eliminates the dynamic blocking that is
  effective against rapidly-changing ad delivery.
- Timeline: Chrome Web Store warnings from June 2024; auto-disabling from early 2025;
  **by June 2026 Chromium removed the `kExtensionManifestV2Disabled` feature flag** that
  had allowed controlled MV2 availability, with **Chrome 150/151 removing the last
  overrides**. Edge and Opera follow Chromium.
- **Firefox supports both MV2 and MV3, and retains blocking `webRequest` alongside
  `declarativeNetRequest`** — a deliberate divergence, stated in terms of Mozilla's
  manifesto principle that individuals must be able to shape their own experience.
  Full uBO remains available on Firefox and Brave.

**[CONTESTED — and state the conflict of interest plainly, because it's material.]**
*For MV3*: the security argument is real — blocking `webRequest` gave every extension
plaintext access to all traffic, and extension compromise is a genuine and recurring attack
vector. *Against*: Google's advertising revenue creates an obvious conflict when the
capability being removed is the one that makes ad blocking effective; **CISA has
recommended ad blockers as a defence against malvertising**, so this is a security
trade-off in both directions, not security versus convenience.

**[DURABLE] If you're designing an extension platform, the real lesson is that the network
interception API *is* the policy.** Whatever you allow there determines what class of
extension can exist, and you will not be able to change it later without a multi-year
migration and a public fight.

---
