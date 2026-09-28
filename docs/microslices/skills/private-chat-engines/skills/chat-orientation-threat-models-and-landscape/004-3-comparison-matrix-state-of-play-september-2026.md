---
id: skill-3-comparison-matrix-state-of-play-september-2026-a3e3c8bc93
purpose: 3 comparison matrix state of play september 2026
source: src/vibey_tools/skills/plugins/private-chat-engines/skills/chat-orientation-threat-models-and-landscape/SKILL.md
requires: ["skill-2-threat-model-taxonomy-the-questions-that-decide-everything-418ce14054"]
links: ["skill-4-timeline-how-we-got-to-the-2026-state-of-play-6685bc98f7"]
---

## 3. Comparison matrix (state of play, September 2026)

| | Signal | Telegram | Matrix/Element | Wire | WhatsApp | iMessage | Session | SimpleX | XMPP+OMEMO | Briar | Delta Chat | Threema | Olvid |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Architecture | A | B | C | A | A | A | C | C | C | C | C | A | A |
| Default 1:1 E2EE | ✅ | ❌ (opt-in only) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (mostly) | ✅ | ✅ | ✅ | ✅ |
| Default group E2EE | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Post-quantum (production) | ✅ Triple Ratchet ([Oct 2025](https://signal.org/blog/spqr/)) | ❌ | ❌ (MLS candidate for "Matrix 3.0") | Agility, PQ ciphersuite unverified | ❌ unverified | ✅ PQ3 ([2024](https://security.apple.com/blog/imessage-pq3/)) | Planned (Protocol v2) | ✅ hybrid sntrup761 ([v5.6, Mar 2024](https://simplex.chat/blog/20240314-simplex-chat-v5-6-quantum-resistance-signal-double-ratchet-algorithm/)) | ❌ | ❌ | ❌ | Research w/ IBM ([Feb 2026](https://threema.com/en/blog/quantum-secure-future)) | ❌ |
| Self-hostable | ❌ | ❌ | ✅ | ❌ (on-prem/edge variants for enterprise) | ❌ | ❌ | ✅ (service nodes, 25k SESH stake) | ✅ (relays) | ✅ | n/a (no servers) | ✅ (chatmail relays) | ❌ | ❌ |
| Phone number required | Yes (hidden by default since 2024 usernames) | Yes | No | Email/phone | Yes | Apple ID | No | No | No | No | Email | No | No |
| Open clients | ✅ | ✅ (server closed) | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (AGPL, reproducible) | ✅ |
| Scale | 70–100M MAU (Apr 2025, Whittaker via [SQ Magazine](https://sqmagazine.co.uk/signal-statistics/)) | ~1B MAU (Mar 2025) | ~19.5k federated servers ([TWIM Jul 2026](https://matrix.org/blog/2026/07/03/this-week-in-matrix-2026-07-03/)) | 1,800+ enterprise customers | ~3B MAU (2025) | ~1B+ devices | — (network of ~1.5–2k nodes) | 480k MAU ([Aug 2026](https://simplex.chat/blog/20260819-simplex-chat-crowdfunding.html)) | — | — | — | ~12M+ (est.) | 100k+ claimed |
| Funding model | Donations + new $1.99/mo backup tier | Ads + Premium + TON deals | Membership, donations, Element B2B | Enterprise SaaS | Meta business messaging | Device sales | Token staking + upcoming Pro | Donations + equity crowdfund | Donations/NLnet grants | Donations/grants | Donations/grants | Paid app + Work licences | B2B/B2G licences |
| Current crisis | Deficit; Sweden/EU legal threats | Durov prosecution; Russia squeeze | Foundation finances | — | Russia blocked it outright | — | Survived near-death 2026 | None known | Slow OMEMO 2 rollout | Maintenance mode | Healthy niche | New owner (Comitis, Jan 2026) | None known |

*Empty "scale" cells mean no trustworthy public figure — not zero.*

---
