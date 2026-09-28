---
id: skill-20-sources-and-method-451c88ada2
purpose: 20 sources and method
source: src/vibey_tools/skills/plugins/web-browser-development/skills/browser-development-reference/SKILL.md
requires: ["skill-19-quick-reference-184e7caa88"]
links: []
---

## §20. Sources and Method

**Method.** Narrative (not systematic) review. Durable material — §2 → `browser-engine-architecture-and-networking` (process model and IPC
discipline), §4.1 → `browser-rendering-pipeline` (HTML parsing), §5 → `browser-rendering-pipeline` (cascade and matching), §6 → `browser-rendering-pipeline` (pipeline architecture),
§7.3 → `browser-rendering-pipeline` (event loop), §8.1 → `browser-security-and-privacy`–8.4 (security model), §12 → `browser-extensions-platform-and-standards` (accessibility), §15 (anti-patterns) —
is synthesized from the specifications and from engine documentation listed in §18. Every
**time-sensitive** claim (engine shares, project status, policy changes, security-program
specifics) was verified against a primary or near-primary source in **August 2026** and is
flagged in §17 with a decay-risk rating. Where vendors genuinely disagree, §16 presents
both cases — and names the commercial interest where it is material to the disagreement,
because in this domain it usually is.

**Search log** (August 2026): browser engine landscape and Ladybird/Servo status ·
Privacy Sandbox and third-party cookie policy · Interop 2026 and Baseline · Chrome site
isolation, sandboxing, and memory safety · Manifest V3 and the extension platform ·
RenderingNG, BlinkNG, and LayoutNG architecture.

**Primary and near-primary sources consulted (selected):**
- **chromium.org** — Site Isolation design doc and overview; `process_model_and_site_isolation.md`;
  the **memory safety** page; **Chrome Security quarterly updates**
- **developer.chrome.com** — the **RenderingNG** series (overview, architecture, key data
  structures, BlinkNG, LayoutNG), Chris Harrelson et al.
- **blog.google / Google Security** — "Stronger with every update: How we're making Chrome
  and the web safer in the AI Era" (2026); **SecurityWeek** coverage of the 13-year-old
  flaw found by Google's agent harness
- **privacysandbox.google.com** — "Next steps for Privacy Sandbox and tracking protections
  in Chrome"; contemporaneous reporting on the Oct 2025 API retirements
- **web.dev** — Interop 2026 announcement, Baseline monthly digests; **webkit.org** —
  "Announcing Interop 2026"; **hacks.mozilla.org** — "Launching Interop 2026";
  **web-platform-tests/interop** 2026 README
- **ladybird.org** and the Ladybird W3C/TPAC session description; **servo.org** and Servo's
  W3C presentation materials
- **ublockorigin.com** and the uBlock wiki on MV2 deprecation; **Mozilla Blog** on its MV3
  approach; **Neowin**, **The Register**, **PCWorld** on the MV2 flag removals
- WHATWG and W3C specifications as cited throughout

**Confidence statement.** **High confidence** in §2–§8 → `browser-engine-architecture-and-networking`, `browser-security-and-privacy` and §11–§15 → `browser-extensions-platform-and-standards`, §18–§19 — these rest on
specifications and first-party engine documentation, much of it unusually candid.
**High confidence** in §17's verified items as of the stated date. **Moderate confidence**
in the engine market-share figures in §1.1 → `browser-engine-architecture-and-networking` and §19.1: browser share is measured by
analytics vendors with known sampling biases, varies by region and device class, and the
~81/14/3 split should be read as approximate and directional. **Moderate confidence** in
§9.1 → `browser-security-and-privacy`'s timeline granularity — the third-party-cookie story reversed twice and secondary
sources disagree about which date was "the" reversal, so the dates here follow Google's own
posts and are given as a sequence rather than a single event. The Ladybird timeline in
§1.1 → `browser-engine-architecture-and-networking` and §17 is a **project target**, not a shipped fact, and such targets have slipped
before across this entire field.
