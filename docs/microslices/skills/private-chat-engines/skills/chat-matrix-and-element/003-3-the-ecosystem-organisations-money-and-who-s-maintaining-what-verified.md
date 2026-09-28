---
id: skill-3-the-ecosystem-organisations-money-and-who-s-maintaining-what-verified-f8dec783ce
purpose: 3 the ecosystem organisations money and who s maintaining what verified
source: src/vibey_tools/skills/plugins/private-chat-engines/skills/chat-matrix-and-element/SKILL.md
requires: ["skill-2-matrix-2-0-verified-and-where-it-stands-in-sept-2026-84446e49d5"]
links: ["skill-4-operator-handbook-running-a-homeserver-the-perspective-nobody-else-can-offer-79e1cd26f8"]
---

## 3. The ecosystem: organisations, money, and who's maintaining what (verified)

### 3.1 The corporate split
- **Matrix.org Foundation** owns the protocol, spec, and matrix.org homeserver; charity, funded by
  memberships + donations + events + (new in late 2025) **premium accounts on matrix.org**.
- **Element** (formerly New Vector) is the startup founded by Matrix's creators; employs most of
  the core engineering: Synapse, MAS, the Rust/JS SDKs, Element clients, and the matrix.org
  infrastructure itself.
- Per the Foundation's **first public annual report (published March 2026,
  [blog](https://matrix.org/blog/2026/03/annual-report/) ·
  [PDF](https://www.matrix.org/foundation/reports/2025%20Public%20Annual%20Report.pdf))**:
  FY2025 revenue +38%, deficit cut from £910,821 to £310,596; **Automattic's Gold membership alone
  = 50% of revenue**; the report calls the dependence on Element's in-kind donations
  "unsustainable". Earlier milestones: the Feb 2025 ["crossroads" post](https://matrix.org/blog/2025/02/crossroads/)
  ($610K shortfall; public Slack/XMPP/IRC bridges shut), June 2025
  [matrix.org freemium](https://matrix.org/blog/2025/06/funding-homeserver-premium/).

### 3.2 Homeserver implementations
- **Synapse** (Python, increasingly Rust components — client-event serialisation and DB access
  were ported by mid-2026; v1.159-era release candidates marched toward room **v12 as default**):
  the production reference server. Worker-sharded, Postgres-backed, the hardest and most rewarding
  to run at scale.
- **Continuwuity** ([site](https://continuwuity.org/introduction) ·
  [GitHub mirror](https://github.com/continuwuity/continuwuity)): community Rust homeserver,
  forked from the archived **conduwuit**, with weekly-ish releases; easy on modest hardware.
  Fork drama worth knowing: conduwuit's archived README disputes continuwuity's "official
  successor" claim and endorses **Tuwunel** instead — as an operator, evaluate both; migrations
  are conduwuit→continuwuity only (no Synapse/Dendrite path).
- **Dendrite** (Go, second-generation reference) has been in a semi-dormant state since Element
  moved it to the Foundation; do not plan new deployments on it without checking current status.
- Others: Conduit (original Rust project, moribund), Grapevine (stalled).

### 3.3 Clients and bridges
- **Element X** (iOS/Android on matrix-rust-sdk — the strategic client), Element Web/Desktop
  (classic, on matrix-js-sdk), plus the long tail (FluffyChat, Fractal, Cinny, Nheko…).
- Bridges live on the **Application Service API**: the **mautrix** family (Telegram, WhatsApp,
  Signal, Messenger, Slack, Discord…) — Beeper open-sourced its bridge stack; Beeper and Texts
  are now Automattic's (2023–24 acquisitions) — plus hookshot (GitHub/feeds) and matrix-admin
  tooling. Note the Foundation killed the *public* Slack/XMPP/IRC bridges in its 2025 cost cuts;
  self-hosted bridges are unaffected.

### 3.4 The sovereignty wave (verified; the most important customer story in private chat)
- **Germany**: BwMessenger for the Bundeswehr (since Nov 2020, 100k+ active users, BSI-certified
  for VS-NfD) and **BundesMessenger** for the wider public sector (~250,000 users across
  municipalities, agencies, fire services; private federation, BSI-hardened, audited)
  ([Element case study](https://element.io/en/case-studies/bundeswehr) ·
  [Matrix Conf slides Oct 2025](https://2025.matrix.org/slides/slides_9HKYHA.pdf)). Plus
  TI-Messenger for healthcare and openDesk at ZenDiS.
- **France**: Tchap (300k+ public-sector users) and La Suite Numérique, built on Matrix; Olvid
  separately holds the cabinet-level mandate (→ `chat-the-wider-field`).
- **NATO**: NI2CE Messenger (NATO-branded Element fork) via NATO ACT experimentation; **UNICC**
  selected Element (2024); live deployments also credited to US DoD (since 2020), UK MoD, Polish
  and Ukrainian armed forces ([Element's Digital Sovereignty Summit post, Nov 2025](https://element.io/blog/element-at-the-summit-on-european-digital-sovereignty/) ·
  [Computer Weekly, Oct 2025](https://www.computerweekly.com/news/366633894/European-governments-opt-for-open-source-alternatives-to-Big-Tech-encrypted-communications)).
- Catalysts: US sanctions on the ICC, the March 2025 "Signalgate" scandal, and a broad European
  digital-sovereignty push (Merz and Macron keynoted the Berlin summit Element attended).
  France and Germany are even discussing interoperating their national messengers.
- Element's commercial arm is **Element Server Suite (ESS)** — a Kubernetes distribution of the
  stack (Synapse+workers, MAS, Element Web/X, LiveKit, bridges, admin console) with a paid Secure
  tier; Sweden's Försäkringskassan, NATO ACT, UNICC and the EC are credited with
  subscription-based procurement commitments.

---
