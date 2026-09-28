---
id: skill-19-sources-and-method-32ce3c3d80
purpose: 19 sources and method
source: src/vibey_tools/skills/plugins/social-media-engineering/skills/social-reference/SKILL.md
requires: ["skill-18-quick-reference-21cc860d43"]
links: []
---

## §19. Sources and Method

**Method.** Narrative review, deliberately covering both readings of the title — **the
engineering of social systems (§1–§12 → `social-platform-apis-and-open-protocols`, `social-feed-graph-ranking-and-notifications`, `social-moderation-abuse-and-regulation`, `social-media-analytics-privacy-and-presence`) and the developer's own presence (§13 → `social-media-analytics-privacy-and-presence`)** — weighted
toward the former, since that's where the transferable technical content is. **§3–§8 → `social-feed-graph-ranking-and-notifications`, `social-moderation-abuse-and-regulation`, §10 → `social-media-analytics-privacy-and-presence`,
§11 → `social-media-analytics-privacy-and-presence` and §12 → `social-media-analytics-privacy-and-presence` rest on long-stable distributed-systems and trust-and-safety practice** and on
the platform engineering literature rather than on anything searched; the fan-out trade-off,
the moderation pipeline, and the adversarial dynamics have been consistently described for
a decade. **§1 → `social-platform-apis-and-open-protocols`, §2 → `social-platform-apis-and-open-protocols` and §9 → `social-moderation-abuse-and-regulation` move fast** and were verified in **August 2026** with three
targeted searches; every claim there is flagged **[VERSIONED]** with a decay rating in §16.

**Search log** (August 2026): X and Reddit API pricing and access terms · Bluesky/AT
Protocol and Mastodon/ActivityPub state and interoperability · DSA, Online Safety Act and
age-verification enforcement.

**Primary and near-primary sources consulted (selected):**
- **API pricing**: multiple independent 2026 breakdowns of X's pay-per-use model,
  cross-checked against each other for the per-resource rates, the 2M cap, and the April
  2026 endpoint withdrawals; contemporaneous reporting (via TechCrunch) of Christian
  Selig's Apollo/Reddit figures; Reddit's own $0.24/1K announcement as widely reported
- **Protocols**: **Bluesky's own atproto GitHub discussion** on ActivityPub
  interoperability (including Evan Prodromou's position and Bluesky's response); **the
  EFF's** 2026 guidance on bridging for the practical seams; **Nieman Lab** and
  **TechCrunch** on Fediverse adoption trends and Bridgy Fed/A New Social
- **Regulation**: **the European Commission's DSA pages** and enforcement announcements;
  **Future of Privacy Forum** on the Commission's age-verification approach and the Meta
  preliminary finding; multiple 2026 compliance guides for the Ofcom-accepted methods and
  the Reddit ICO fine; **Yoti** and **Inside Privacy** for the DSA obligation set

**Confidence statement.** **High confidence** in §3–§8 → `social-feed-graph-ranking-and-notifications`, `social-moderation-abuse-and-regulation`, §10 → `social-media-analytics-privacy-and-presence`, §11 → `social-media-analytics-privacy-and-presence`, §12 → `social-media-analytics-privacy-and-presence` and §14 — these are
architectural patterns and adversarial dynamics, consistently described across the platform
engineering and trust-and-safety literature. **High confidence in the protocol
architecture** in §2 → `social-platform-apis-and-open-protocols`, which comes substantially from Bluesky's own documentation and the
W3C spec, and in the interoperability position, which is stated directly by the projects
themselves.

⚠️ **Lower confidence, deliberately, on the API pricing in §1.2 → `social-platform-apis-and-open-protocols`.** **Almost every source
for these figures is a company selling an alternative to the official API**, which is a
clear incentive to present official pricing unfavourably. I cross-checked the rates across
several such sources and they agree closely — but ⚠️ **the framing is not disinterested,
X has changed this pricing repeatedly (including twice in 2026 alone), and you should
verify at developer.x.com before budgeting anything.** ⚠️ **Similarly, several age-assurance
sources are vendors selling verification services**, which is an incentive to present the
regulatory obligation as broader and more urgent than it is; **I have relied on the
Commission's and Ofcom's own positions for the substance and used vendor material only for
corroborating detail.** The **fine and enforcement facts** (Reddit's £14.5M, the Meta and
TikTok preliminary findings) are reported consistently across independent sources but
**I read reporting, not the decisions themselves.** **§9 → `social-moderation-abuse-and-regulation` is not legal advice**, the
regulatory position differs by jurisdiction and surface, and §15 is opinion labelled as
such — including §15.6, where I have taken a position that reasonable people dispute.
