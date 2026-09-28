---
id: skill-16-contested-questions-655fd56384
purpose: 16 contested questions
source: src/vibey_tools/skills/plugins/smart-tv-app-development/skills/smart-tv-reference/SKILL.md
requires: ["skill-15-anti-patterns-0b2cd95d56"]
links: ["skill-17-currency-snapshot-verified-august-2026-ea6b93725b"]
---

## §16. Contested Questions

**16.1 Native vs. web vs. React Native.** §13.1 → `smart-tv-monetization-certification-and-operations`. The calculus genuinely changed in 2026:
React Native became strategically relevant because Amazon made it a **first-class citizen
on Vega**, with core RN and common dependencies precompiled into the OS. If your mix is
Vega + Android TV + tvOS, RN is now a defensible primary choice in a way it wasn't before.
If your mix is Tizen + webOS + the long tail, a web app still wins.

**16.2 How far back to support.** Every additional model year you support drags your web
baseline backwards (§1.3 → `smart-tv-platforms-and-10-foot-ui`) and adds DRM and codec permutations. *For long support*: those
TVs are in living rooms for a decade and their owners are real users. *Against*: the
engineering tax is superlinear. **Decide with usage data from your own analytics, not with
market-share reports.**

**16.3 SSAI vs. CSAI.** §9.2 → `smart-tv-monetization-certification-and-operations`. SSAI wins on user experience and blocker resistance; CSAI
gives the client richer signal and simpler debugging. SSAI is the default and the argument
is mostly settled, but the measurement complexity it introduces is real.

**16.4 Is CTV measurement trustworthy?** §9.3 → `smart-tv-monetization-certification-and-operations`.

**16.5 Platform billing.** *For*: frictionless signup, the platform's stored payment
method, and higher conversion. *Against*: revenue share, and the platform owns your
customer relationship and churn flow. There's no universal answer; there is a very
different answer for a $5/month niche service than for a major studio.

**16.6 Turnkey OTT platform vs. custom build.** *For turnkey*: fast, covers many
platforms, handles certification and updates. *Against*: you don't control the UX, you're
one of thousands of similar apps, and differentiation is limited to branding. Reasonable
if content is your product and the app is a delivery mechanism.

**16.7 Whether to build for the long tail at all.** VIDAA, whaleOS, webOS Hub, Xumo,
Titan OS, SmartCast — each is a certification cycle and a QA burden for a small slice.
Regionally, though, some of them are *not* small: ignoring VIDAA in markets where Hisense
is dominant is a real revenue decision.

---
