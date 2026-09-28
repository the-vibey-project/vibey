---
id: skill-1-the-architecture-fundamentals-stable-39bb4ac43b
purpose: 1 the architecture fundamentals stable
source: src/vibey_tools/skills/plugins/private-chat-engines/skills/chat-telegram/SKILL.md
requires: []
links: ["skill-2-the-durov-prosecution-and-the-compliance-turn-verified-6541fdef7e"]
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
