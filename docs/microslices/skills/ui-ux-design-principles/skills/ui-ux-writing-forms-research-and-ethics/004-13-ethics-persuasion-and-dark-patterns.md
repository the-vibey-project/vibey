---
id: skill-13-ethics-persuasion-and-dark-patterns-7be0195082
purpose: 13 ethics persuasion and dark patterns
source: src/vibey_tools/skills/plugins/ui-ux-design-principles/skills/ui-ux-writing-forms-research-and-ethics/SKILL.md
requires: ["skill-12-research-and-evaluation-59954690dd"]
links: ["skill-14-ai-era-interfaces-0724d40f99"]
---

## §13. Ethics, Persuasion, and Dark Patterns

### 13.1 The line

**[DURABLE] The test is whose interest the design decision serves when the user's and the
business's diverge.** Persuasion that helps a user do what they already wanted is design.
Design that exploits a cognitive bias to produce a choice the user would not otherwise make
is a dark pattern — and increasingly, a legal violation.

### 13.2 The catalogue

| Pattern | Mechanism | Regulatory exposure |
|---|---|---|
| **Roach motel** (easy in, hard out) | Asymmetric effort | FTC: Epic $245M; Amazon $2.5B settlement (which surfaced internal emails on deliberately confusing cancellation) |
| **Sneak into basket / drip pricing** | Late disclosure | UCPD, FTC |
| **Confirmshaming** ("No thanks, I hate saving money") | Social/emotional pressure | DFA target |
| **Preselected options / pre-ticked boxes** | Default exploitation | GDPR consent invalidity |
| **Asymmetric consent** (bright "Accept all", buried "Reject") | Choice architecture | **CNIL fined Google €150M and Microsoft €60M** on exactly this; TikTok €345M (Irish DPC) for public-by-default; Amazon €746M |
| **False urgency / fake scarcity** ("1 room left!") | Manufactured pressure | UCPD; DFA named target |
| **Disguised ads** | Misrepresentation | FTC endorsement rules |
| **Nagging** | Repetition until compliance | |
| **Obstruction / privacy zuckering** | Friction as a weapon | CPRA: "dark patterns are about effect, not intent" |
| **Infinite scroll + autoplay + variable rewards** | Attention capture | DFA "addictive design" target |

### 13.3 The regulatory picture (2026)

- **EU DSA Article 25** already prohibits online-platform interfaces that "deceive,
  manipulate or otherwise materially distort" users' ability to make free and informed
  decisions. **DMA** carries fines up to 6% of global revenue for consent manipulation.
- **EDPB Guidelines 03/2022** define six GDPR dark-pattern categories: *overloading,
  skipping, stirring, obstructing, fickle, left in the dark*. Useful as a design checklist,
  not just a legal one.
- **Consumer Rights Directive amendments** ban dark patterns in distance financial-services
  interfaces — transposed by 19 December 2025, **applicable from 19 June 2026**.
- **EU Digital Fairness Act** — confirmed in the Commission's 2030 Consumer Agenda (adopted
  19 November 2025); **proposal expected late 2026**, targeting dark patterns, addictive
  design, influencer marketing, and personalization. Adoption realistically 2027+, entry
  into force 2028–2030. **Not law yet — do not describe it as such.**
- **US FTC** is actively enforcing under Section 5, including **naming individual executives
  as defendants**. Its 2024 study of 642 sites/apps found **76% used at least one possible
  deceptive pattern** and ~67% used multiple. The Commission's 2022 EU study found **97% of
  the most popular EU-used sites and apps** deployed at least one.
- **California CPRA** treats dark patterns as consent-invalidating, with the CPPA's standard
  being **symmetry**: the privacy-protective option must be *as easy* as the less protective
  one.

### 13.4 The design checklist

- [ ] Cancelling is as easy as subscribing (same channel, same number of steps).
- [ ] The privacy-protective choice is as prominent and as few clicks as the permissive one.
- [ ] No pre-ticked consent boxes; consent is a positive, unambiguous act.
- [ ] Total price, including all fees, disclosed before the user invests effort.
- [ ] Urgency and scarcity claims are literally true and verifiable.
- [ ] Decline options are neutrally worded — no shaming.
- [ ] Defaults chosen for the user's benefit, and you can say why.
- [ ] Ads and sponsored content are unmistakably labeled.
- [ ] Consent flows are documented and evidenced.
- [ ] No design element manipulates children or exploits known vulnerabilities.

**[UNIVERSAL] "It wasn't intentional" is not a defense** — the CPPA's stated position is
that dark patterns are about *effect*, not intent. An A/B test that increased conversion by
making the reject button harder to find has produced a violation regardless of what anyone
meant.

---
