---
id: skill-8-monetization-942c9328b2
purpose: 8 monetization
source: src/vibey_tools/skills/plugins/smart-tv-app-development/skills/smart-tv-monetization-certification-and-operations/SKILL.md
requires: []
links: ["skill-9-ctv-advertising-3d5d66ee1f"]
---

## §8. Monetization

### 8.1 The models

| Model | Notes |
|---|---|
| **SVOD** (subscription) | Platform IAP usually **mandatory** if you sell on-device |
| **TVOD** (rent/buy) | Same |
| **AVOD** (free, ad-supported) | §9 |
| **FAST** (free ad-supported streaming TV — linear-style channels) | Rapidly growing; different content ops |
| **Hybrid** | Ad-supported tier plus premium — now the industry default |
| **Authenticated / TV Everywhere** | MVPD login; device-code pairing (§3.4 → `smart-tv-platforms-and-10-foot-ui`) |

**⚠️ The platform's cut is a business-model input, not a footnote.** Platform billing
(Roku Pay, Google Play Billing, Amazon IAP, Apple IAP) typically takes a revenue share and
usually **owns the customer relationship** — including the subscriber's payment method and
often the churn-save flow. Whether you can sign users up off-platform and merely
*authenticate* them on-device is a per-platform policy question with major economic
consequences. **Ask this before you design the funnel.**

### 8.2 Entitlement

**[DURABLE] Enforce entitlement server-side, always.** The client's job is to present the
right UI; the server's job is to refuse the license (§5 → `smart-tv-playback-drm-and-performance`) for an unentitled user. A client
that decides entitlement locally will be bypassed.

Account linking across platforms is a real design problem: a user who subscribes on Roku,
watches on their phone, and then buys an LG TV expects one account. That requires an
identity system independent of every platform's billing.

---
