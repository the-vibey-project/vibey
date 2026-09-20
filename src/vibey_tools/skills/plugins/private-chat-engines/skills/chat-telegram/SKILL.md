---
name: chat-telegram
description: "Use when working with Telegram — MTProto and the cloud-chat architecture, why Secret Chats are 1:1 mobile-only and off by default, the Durov prosecution and the compliance turn, scale and economics, operating communities and channels, and the bot and Mini-App developer ecosystem with its constraints. Companion to the other private-chat-engine skills."
---

# Telegram: The Cloud-Chat Empire, and What \"Private\" Does Not Mean There

> **Part 3 of 6** of the *Private Chat Engines* dossier (plugin
> `private-chat-engines`), covering §1–§7. Sibling skills:
> `chat-orientation-threat-models-and-landscape` (§0–§5 — the three architectural families, threat-model taxonomy, the comparison matrix, the timeline, the five forces),
> `chat-signal` (§1–§6 — the protocol stack, the organisation and its costs, legal posture, operator and developer perspectives, honest weaknesses),
> `chat-matrix-and-element` (§1–§6 — federation, Matrix 2.0, the ecosystem and its funding, the homeserver operator handbook, the developer surface),
> `chat-the-wider-field` (§1–§13 — MLS and Wire, WhatsApp, iMessage PQ3, Threema, Olvid, SimpleX, Session, Nostr, XMPP, Briar, Delta Chat, the dead ones, the policy annex),
> `chat-builder-and-operator-playbooks` (§1–§12 — protocol shape, the crypto checklists, the metadata budget, abuse under E2EE, the unglamorous 80%, ops checklists, incident playbooks).
> Section numbers are **per skill**, not shared across the set: each file is a self-contained
> dossier entry. A reference written as §N → `skill` points at that skill's own §N.
>
> **Currency:** state of research 16 September 2026. §1's architecture is **stable fundamentals**. §2 (the prosecution and compliance turn), §3 (scale and economics) and §4 (geopolitical squeeze) are **dated specifics** and move quickly.

> **⚠️ The most feature-rich platform, the biggest developer ecosystem of the three headline apps, and the most misunderstood on privacy.**
>
> **⚠️ GOTCHA** boxes mark where the common mental model is wrong in ways that get people hurt
> or products mis-designed.
>
> **The three ideas that organize this document:**
> 1. **⚠️ DEFAULT TELEGRAM CHATS ARE NOT END-TO-END ENCRYPTED**
>    **Everything is encrypted in transit and at rest, but Telegram holds the keys. That is precisely what makes multi-device sync, 200,000-member groups, searchable history and channels possible. Treat any claim that Telegram is an E2EE messenger as false.**
> 2. **⚠️ THE FEATURE SET *IS* THE TRUST TRADE**
>    **Every capability people love about Telegram is downstream of the server being able to read content. You cannot keep the features and remove the trust — that is the whole architecture, not an oversight.**
> 3. **⚠️ THE DEVELOPER PLATFORM IS RICH, AND ON A LEASH**
>    **Bots and Mini-Apps are the strongest ecosystem in the field, but you build on somebody else's infrastructure under terms that changed materially after the prosecution. §6 covers the constraints before you commit.**

---

Telegram is simultaneously the most feature-rich messaging platform, the biggest *developer*
platform of the three headline apps, and the most misunderstood on privacy. The one-sentence
mental model: **Telegram is a cloud service with an E2EE sidecar** — its default privacy model is
"trust Telegram," and its 2024–2026 legal history shows exactly what that trust means in practice.

---

## 1. The architecture (fundamentals — stable)

### 1.1 Cloud chats: client↔server encryption, server holds the keys
Default chats, groups and channels are encrypted between client and Telegram's server
(**MTProto 2.0**), and Telegram holds the key material — that is what makes seamless multi-device
sync, server-side search, 200k-member groups and unlimited channels possible. It also means
Telegram can technically read all of it. This is a *product decision*, not an accident.

### 1.2 Secret Chats: the E2EE exception
1:1 only, mobile apps only, device-bound (no sync, no seamless restore), and *not* the default —
and unavailable on desktop/web/third-party clients, which is why almost nobody uses them. **1:1
voice/video calls are E2EE; group voice/video calls are not** (they're server-mediated with
client-server encryption). Any security analysis of "Telegram" that doesn't disaggregate these is
worthless.

Key agreement also **requires both parties to be online**: MTProto's E2E layer has no asynchronous
pre-key bootstrap of the X3DH kind, so a Secret Chat cannot be opened to a device that is simply
switched off. That is a second, quieter reason almost nobody uses them — the feature fails exactly
when mobile messaging normally works.

### 1.3 MTProto 2.0 and its critics
MTProto is a bespoke protocol (auth-key DH → per-message keys derived from a middle slice of a
SHA-256 of the plaintext, encrypted in an unusual IGE-mode construction, 2.0 fixing the worst
1.0 weaknesses). The landmark academic treatment is Albrecht, Mareková, Paterson & Stepanovs,
*"Four Attacks and a Proof for Telegram"* (IEEE S&P 2022): four practical-to-theoretical attacks
(e.g. order-swapping of messages, implementation-leak timing) — all responsibly disclosed and
fixed — plus a formal proof that MTProto 2.0 meets a *weakened* IND-CCA notion under its
assumptions. The durable lesson is the paper's subtext, not its headline: **rolling your own
protocol buys you a cryptography paper, not better security.** Everyone else standardized on
Signal Protocol/MLS; nobody standardized on MTProto.

### 1.4 Open clients, closed server
Telegram's clients are open source (with reproducible builds worth studying); the **server is
closed-source and proprietary**. You cannot self-host Telegram, and there is no federation.
"Telegram" as infrastructure means Telegram's datacenters under UAE-administered management.

### 1.5 The product machine
Channels (one-to-many, unlimited), groups to 200k members, topics, bots, Mini Apps (in-chat web
apps), Stories, Premium stickers/gifts, TON-based in-app economy — Telegram is closer to
"encrypted-optional WeChat-without-the-store" than to Signal. That breadth is why developers and
operators love it even as privacy professionals warn users off it for sensitive content.

---

## 2. The Durov prosecution and the compliance turn (verified)

- **24 Aug 2024**: Pavel Durov arrested at Le Bourget, Paris; indicted on ~12 counts centred on
  complicity in platform-enabled crime and refusal to cooperate with lawful requests; released on
  €5M bail.
- **Policy shift (Sept 2024)**: Telegram updated its privacy practices to disclose phone numbers
  and IP addresses to authorities on valid legal requests — a genuine break with its "we hand
  over nothing" era.
- **Fulfilled US data requests jumped from 14 (Jan–Sep 2024) to ~900 across that year** per
  investor-material reporting summarised by [Axis Intelligence's 2026 Telegram statistics](https://axis-intelligence.com/telegram-statistics/).
- **Case status (Sept 2026)**: still under investigation, no trial date; Paris prosecutor (May
  2026) confirmed Durov "remains under judicial control" ([Izvestia EN, 17 May 2026](https://en.iz.ru/en/2098745/2026-05-17/prosecutor-spoke-about-continuation-investigation-against-durov-france));
  a **fourth** questioning round in July 2026 ([CoinEdition](https://coinedition.com/telegram-founder-pavel-durov-questioned-for-fourth-time-in-ongoing-french-criminal-probe/),
  [Pravda EN](https://news-pravda.com/world/2026/07/09/2431059.html)); travel restrictions were
  progressively lifted and **removed entirely in November 2025**; the defence filed a QPC
  constitutional challenge and a CJEU referral arguing the charges collide with the DSA's hosting
  liability shield ([Kohen Avocats analysis, Sept 2026](https://kohenavocats.com/en/durov-telegram-france-two-years-prosecution-complicity-host-shield/)).
  A Jan 2026 Cour de cassation ruling on the "active role" test may decide how much of the case
  survives.
- **Collateral pressure**: Australia eSafety sued over terrorism-content removal (2026); **Russia
  opened its own criminal case and put Durov on a wanted list (July 2026)** over alleged Ukrainian
  recruitment via Telegram ([Carnegie Endowment, Sept 2026](https://carnegieendowment.org/russia-eurasia/politika/2026/09/russia-durov-tech-prosecution)) —
  Durov is now squeezed by *both* sides of that war.

**Operator takeaway**: since late 2024 Telegram is a cooperative data holder for phone
number/IP/subscriber metadata, and its public channels/groups are effectively surveilled space.
Treat Telegram accordingly — a *content-public, metadata-cooperative* service with excellent UX.

---

## 3. Scale and economics (verified, with the usual caveat)

⚠️ Telegram publishes no audited financials; figures come from investor materials reported by the
FT and statistics roundups — management-disclosure grade, not audited grade.

- **~1 billion MAU** (Durov, March 2025; up from 950M Jul 2024), ~.5B DAU; India largest market,
  Russia deepest penetration ([Axis Intelligence](https://axis-intelligence.com/telegram-statistics/),
  [DataRefs](https://www.datarefs.com/statistics/social-media/telegram-users/)).
- **FY2024: $1.4B revenue, first-ever profit ~$540M** ([TechCrunch, Dec 2024](https://techcrunch.com/2024/12/23/pavel-durov-says-telegram-is-now-profitable/),
  [Economic Times](https://economictimes.indiatimes.com/tech/technology/under-pressure-telegram-pulls-off-an-elusive-milestone-a-profit/articleshow/116667724.cms)).
- **H1 2025: $870M revenue but −$222M loss** — driven by a write-down of Toncoin holdings
  (price fell ~70%), which erased ~$400M operating profit ([Axis Intelligence](https://axis-intelligence.com/telegram-statistics/)).
- Monetization mix (H1 2025): TON ecosystem/exclusivity ~$300M, Premium $223M (+88% YoY),
  ads $125M, Stars/mini-app store purchases ~$13–15M/month. **Premium: 15M subscribers (May
  2025)** — only ~1.5% of the base pays.
- IPO ambitions persist ($1.7B 2025 bond round with BlackRock/Mubadala) but legal exposure and
  ~$500M of bonds frozen in Russia complicate timing.

**Why this matters for privacy people**: Telegram's revenue engine (TON deals, ads, mini-app
economy) rewards *more visibility*, not less. The incentives point away from E2EE-by-default.

---

## 4. Geopolitical squeeze (verified)

- **August 2025**: Roskomnadzor restricted voice calls on WhatsApp *and* Telegram
  ([AP](https://apnews.com/article/russia-internet-messenger-whatsapp-telegram-crackdown-2a89703deb1094af1b0206161efe2050)).
- **February 2026**: Russia **fully blocked WhatsApp** and slowed Telegram to a crawl while
  delisting 13 major foreign domains from its national DNS
  ([Reuters, 12 Feb 2026](https://www.reuters.com/technology/russia-blocks-metas-whatsapp-messaging-service-ft-reports-2026-02-12/),
  [BBC](https://www.bbc.com/news/articles/clygd10pg5lo)), pushing the state-backed **MAX**
  super-app (pre-installed on all devices sold in Russia since 1 Sep 2025; ~30M claimed users;
  critics note it lacks E2EE) ([RFE/RL](https://www.rferl.org/a/russia-internet-technology-regulation-censorship-circumvention-vpn-app/33676178.html),
  [BBC](https://www.bbc.com/news/articles/ce9rj2145jgo)).
- The irony worth teaching: *Telegram's* Russian situation (throttled, pressured, CEO wanted)
  stems partly from refusing domestic data localisation — the same posture France is prosecuting
  him for under-serving. Private-chat operators live between mutually hostile regulators.

---

## 5. Operator perspective: operating *on* Telegram

You can't operate Telegram, but an enormous amount of organisational life runs on it. The real
operator skills:

1. **Community operations at scale.** Groups with 200k members, channels with millions of
   subscribers, topics to keep them navigable, slow mode, join-by-approval, admin permissions,
   anti-spam bots (the ecosystem standard is third-party moderation bots with API-level ban
   tooling). Moderation here is *visible and enforceable* precisely because content is not E2EE —
   a feature for public squares, a bug for private circles.
2. **Compliance surface.** Since Sept 2024's policy change, expect data requests and content
   takedowns to be honoured; expect channel bans in regulated categories; Durov's prosecution
   means *you* may be asked for data about *your* community. Plan disclosure accordingly.
3. **Resilience planning.** Russia's throttling playbook (partial call blocks → DNS delisting)
   is the template for national pressure. Telegram's built-in MTProto proxies/VPN tolerance help,
   but don't build single-channel dependence for populations a state may switch off.
4. **Brand/identity ops.** Fragmented identity (usernames, channels, bots) invites impersonation;
   verify channels, guard admin accounts (2FA, separate payment identity), assume screenshots —
   nothing on Telegram is deniable-or-private in the Signal sense.

---

## 6. Developer perspective: the richest ecosystem, with a leash

### 6.1 Three distinct APIs — don't confuse them
- **Bot API** (HTTPS, hosted by Telegram): bots receive/send without a phone number or a Telegram
  account of their own. The SDK ecosystem is deep: aiogram (Python), Telegraf/grammY (JS/TS),
  python-telegram-bot, and dozens more.
- **Mini Apps** (Telegram Web Apps): full web apps embedded in-chat (init-data signature
  verification server-side — never trust client data), with payments via Telegram Stars and deep
  links. Docs evolve fast: Bot API **9.0 (Apr 2025)** added Device/SecureStorage; **9.5–9.6
  (Mar–Apr 2026)** added things like `requestChat` — see
  [core.telegram.org/bots/webapps](https://core.telegram.org/bots/webapps).
- **MTProto "Telegram API"** (the real client API): full account automation, via **TDLib** or
  community libs (Telethon/Pyrogram — Python; gramjs — JS; mtcute; etc.). Powerful, but
  rate-limited and ToS-policed; mass automation is how accounts get banned.

### 6.2 The TON exclusivity (verified)
Since **January 2025**, anything blockchain-adjacent in a Mini App must run **exclusively on
TON** (TON Connect SDK only; multi-chain apps had to migrate by 21 Feb 2025). Official:
[Telegram Blockchain Guidelines](https://core.telegram.org/bots/blockchain-guidelines); defence
and controversy: [Cointelegraph, Feb 2025](https://cointelegraph.com/news/telegram-ton-exclusive-web3-blockchain).
Translation for developers: Telegram gives you 1B users and a built-in wallet economy, and takes
in exchange chain lock-in and policy risk. Bots *without* Mini Apps are exempt.

### 6.3 Monetization paths
Paid bots/services (Stars, external payment providers for physical goods), channel ads revenue
share for large channels, Premium-restricted features economy, TON mini-app commerce, sponsored
posts. Telegram is the only platform in this dossier where a solo developer can plausibly make a
living *inside* the messenger.

### 6.4 Security engineering caveats for bot devs
Everything a bot sees is known to Telegram's servers; Mini App init data must be verified against
the bot token HMAC; user phone numbers shared with bots only via explicit consent buttons; and
remember group "privacy mode" — bots only see @-mentions unless admins grant message access.

---

## 7. Honest verdict

- For *sensitive confidentiality*: Telegram is not the tool — cloud chats are the default, Secret
  Chats are a footnote, and the company now demonstrably cooperates with authorities on metadata
  and identity.
- For *reach, community, and commerce*: it is arguably the best messaging platform on earth,
  now profitable at billion-user scale, with a developer economy nobody else comes close to.
- The interesting question for 2026–2027 is whether France's prosecution and Russia's squeeze
  force Telegram further toward *being* a regulated platform (Durov's lawyers' DSA-shield QPC is
  the tell) — at which point its rebel-brand privacy story is fully vestigial.

---

## Sources (this file)

- MTProto paper: Albrecht, Mareková, Paterson, Stepanovs, *Four Attacks and a Proof for Telegram*
  (IEEE S&P 2022) — fundamentals, stable.
- Durov case: [Izvestia EN (17 May 2026)](https://en.iz.ru/en/2098745/2026-05-17/prosecutor-spoke-about-continuation-investigation-against-durov-france) ·
  [CoinEdition (9 Jul 2026)](https://coinedition.com/telegram-founder-pavel-durov-questioned-for-fourth-time-in-ongoing-french-criminal-probe/) ·
  [Pravda EN (9 Jul 2026)](https://news-pravda.com/world/2026/07/09/2431059.html) ·
  [Kohen Avocats (Sept 2026)](https://kohenavocats.com/en/durov-telegram-france-two-years-prosecution-complicity-host-shield/) ·
  [Carnegie Endowment (Sept 2026)](https://carnegieendowment.org/russia-eurasia/politika/2026/09/russia-durov-tech-prosecution)
- Economics: [TechCrunch (23 Dec 2024)](https://techcrunch.com/2024/12/23/pavel-durov-says-telegram-is-now-profitable/) ·
  [Economic Times](https://economictimes.indiatimes.com/tech/technology/under-pressure-telegram-pulls-off-an-elusive-milestone-a-profit/articleshow/116667724.cms) ·
  [Axis Intelligence Telegram statistics 2026](https://axis-intelligence.com/telegram-statistics/) ·
  [DataRefs](https://www.datarefs.com/statistics/social-media/telegram-users/) ·
  [DroidCrunch](https://droidcrunch.com/telegram-statistics/) — all based on unaudited investor materials; treat as management disclosure.
- Russia: [AP (Aug 2025)](https://apnews.com/article/russia-internet-messenger-whatsapp-telegram-crackdown-2a89703deb1094af1b0206161efe2050) ·
  [Reuters (12 Feb 2026)](https://www.reuters.com/technology/russia-blocks-metas-whatsapp-messaging-service-ft-reports-2026-02-12/) ·
  [BBC: WhatsApp block](https://www.bbc.com/news/articles/clygd10pg5lo) ·
  [BBC: MAX super-app](https://www.bbc.com/news/articles/ce9rj2145jgo) ·
  [RFE/RL](https://www.rferl.org/a/russia-internet-technology-regulation-censorship-circumvention-vpn-app/33676178.html)
- Developer platform: [Mini Apps docs](https://core.telegram.org/bots/webapps) ·
  [Blockchain Guidelines](https://core.telegram.org/bots/blockchain-guidelines) ·
  [Cointelegraph on TON exclusivity (Feb 2025)](https://cointelegraph.com/news/telegram-ton-exclusive-web3-blockchain) ·
  [ton.org mini-app guide](https://ton.org/en/how-to-create-your-telegram-mini-apps)
