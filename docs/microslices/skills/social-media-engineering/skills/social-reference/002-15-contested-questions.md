---
id: skill-15-contested-questions-40bfb9b7ba
purpose: 15 contested questions
source: src/vibey_tools/skills/plugins/social-media-engineering/skills/social-reference/SKILL.md
requires: ["skill-14-anti-patterns-c40c7780f9"]
links: ["skill-16-currency-snapshot-verified-august-2026-c0438f0423"]
---

## §15. Contested Questions

**15.1 Is building on platform APIs ever wise?** *For*: the data and reach exist nowhere
else, and real businesses run on them. *Against*: ⚠️ **the 2023–26 record is unambiguous —
you have no protection and short notice.** **[The defensible position: build on them for
capability, never for your core value proposition, and keep an exit path costed.]**

**15.2 ActivityPub or AT Protocol?** *ActivityPub*: a W3C standard, a real multi-project
ecosystem, Threads participating, genuine server diversity. *ATProto*: better account
portability, algorithmic choice as a primitive, far larger user base, ⚠️ **and a
centralization critique that its own community makes.** **[CONTESTED and unresolved. If
you're building, the honest answer is that you may need both, and bridging is imperfect.]**

**15.3 Should feeds be algorithmic or chronological?** *Algorithmic*: with any real
following count, chronological is unusable, and ranking genuinely surfaces value.
*Chronological*: predictable, uncoupled from engagement optimization, and not
manipulable by the platform. **⚠️ ATProto's answer — make the algorithm a user-selectable,
third-party-buildable component — is the most interesting structural response anyone has
shipped**, and whether it works at scale is still open.

**15.4 Is age verification good policy?** *For*: the harms to minors are documented and
self-declaration demonstrably fails. *Against*: ⚠️ **it requires identifying users, which
is in direct tension with privacy and anonymity, and anonymity protects vulnerable people
too.** **The technical middle ground — zero-knowledge age tokens, OS-level attestation
(§9.3 → `social-moderation-abuse-and-regulation`) — is genuinely promising and not yet deployed at scale.** **[Live, and the
engineering choice materially affects which side you land on.]**

**15.5 Can moderation be solved?** ⚠️ **No, and treating it as a solvable engineering
problem is itself an error.** It's a values problem with an engineering component; every
policy is contested by someone; and **the realistic goal is legitimacy and consistency,
not correctness.**

**15.6 Do developers need a social presence?** §13 → `social-media-analytics-privacy-and-presence`. **[CONTESTED, and I've taken a
position: no, and the alternatives are underrated.]** The counter-case is real —
visibility does generate opportunity, and for people outside traditional networks it can
be genuinely levelling.

---
