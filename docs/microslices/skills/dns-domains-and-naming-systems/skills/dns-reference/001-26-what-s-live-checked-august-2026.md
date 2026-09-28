---
id: skill-26-what-s-live-checked-august-2026-88298d680c
purpose: 26 what s live checked august 2026
source: src/vibey_tools/skills/plugins/dns-domains-and-naming-systems/skills/dns-reference/SKILL.md
requires: []
links: ["skill-27-misconceptions-e3974e3337"]
---

## §26. What's Live — checked August 2026

### 26.1 ⚠️ ICANN's first new gTLD round since 2012 has closed — 1,600+ applications
**⚠️ §14 → `dns-icann-tlds-registries-and-registration`'s namespace expanding for the second time — and the application window has now
closed.**

- **⚠️ THE DATES.** ⚠️ **ICANN's New gTLD Program: 2026 Round application window opened on
  30 April 2026 and closed on 12 August 2026, with ICANN's own announcement reporting more
  than 1,600 primary applications received, over 1,100 of which also requested a replacement
  string.** ⚠️ **ICANN expects to publish the list of applications that passed the
  Administrative Check ("Reveal Day") roughly nine weeks after close, with the specific
  timeline due in mid-September 2026.** ⚠️ **ICANN's framing is that for the first time in
  over a decade, organizations can apply to operate their own top-level domain.**
- **⚠️ THE PRECEDENT.** ⚠️ **The 2012 round drew nearly 2,000 applications and resulted in
  more than 1,200 new gTLDs — brands like .microsoft and .sky, places like .africa and
  .berlin, and generic terms like .bank and .eco.**
- **⚠️ THE COSTS AND TIMELINE ARE THE PART PEOPLE UNDERESTIMATE.** ⚠️ **Reporting puts the
  evaluation fee at US$227,000 per application, and applicants must partner with a
  pre-approved Registry Service Provider from ICANN's evaluated list — a requirement that is
  new relative to 2012.** ⚠️ **One registrar's analysis expects a minimum of two years before
  the first TLDs launch, taking it to roughly Q2 2028, with the full programme running
  through 2030 depending on application volume.**
- **⚠️ A NOTABLE POLICY CHANGE**: ⚠️ **the ICANN Board decided in January 2024 that CLOSED
  GENERICS — a single registrant holding a generic term like .book exclusively — will not be
  permitted in this round unless a framework is developed to assess their public-interest
  compatibility.**

> **⚠️ GOTCHA — for anyone who is not applying, the relevant consequence is defensive.**
> ⚠️ **Legal commentary notes the round presents an opportunity for brand owners and a risk
> if third parties apply for strings implicating existing trademark rights — and that
> expanding the namespace opens new space for infringement and abuse.**
> ⚠️ **The rights-protection mechanisms of §18 → `dns-whois-disputes-domain-security-and-aftermarket` — Trademark Clearinghouse, Sunrise, Claims —
> are the practical response, and they require you to have registered marks in the
> Clearinghouse BEFORE the new TLDs launch.**
> **⚠️ Note also ICANN's own status reporting was candid: the programme was in "yellow"
> status in February 2026 due to risk around systems and security testing and a
> behind-schedule operating model — which is the sort of self-assessment worth taking
> seriously.**

**⚠️ Sourcing note: the dates, fee structure and policy positions come from ICANN's own
announcement, Applicant Guidebook and status documents, plus law-firm client alerts —
which agree.**

### 26.2 ⚠️ Blockchain naming retreated, and the challenger applied to join
**⚠️ §24 → `dns-blockchain-naming-alternatives-assessed`'s assessment resolving — and the specific form the resolution took is genuinely
striking.**

- **⚠️ THE ADMISSION.** ⚠️ **In March 2026 Unstoppable Domains' CEO publicly characterized
  blockchain names as part of the 2021 "crypto craze" that "did not cross the chasm into
  mainstream usage."** ⚠️ **Reporting states that traditional DNS then accounted for more
  than 90% of Unstoppable's business — from a company that had raised roughly $70 million
  and sold over four million blockchain names.**
- **⚠️ HANDSHAKE.** ⚠️ **Namecheap exited Handshake TLD support; the Namebase exchange
  closed after a migration; reporting puts the HNS token down 99% and describes the project
  as in decline since 2022.**
- **⚠️ THE DIAGNOSED CAUSE IS EXACTLY §24 → `dns-blockchain-naming-alternatives-assessed`'s.** ⚠️ **One analysis states it plainly:
  mainstream browsers never added native blockchain domain resolution, so typing a name into
  Chrome, Safari, Firefox or Edge requires an extension.** ⚠️ **Another puts it as the
  chicken-and-egg of every alt-root: if people cannot visit your site you will not build on
  it, and if nobody builds on it browsers will not resolve it.**
- **⚠️ AND HERE IS THE REMARKABLE PART: ENS APPLIED FOR `.ens` THROUGH ICANN'S 2026 ROUND**
  (§26.1). ⚠️ **The system built to route around ICANN applied to ICANN.** ⚠️ **Reporting
  also indicates Brave and Unstoppable intend a joint application to make `.brave` an
  official brand gTLD.**
- **⚠️ ENS ALSO SIMPLIFIED ARCHITECTURALLY**: ⚠️ **in February 2026 it reportedly cancelled
  its planned Namechain Layer 2 and committed to deploying ENSv2 on Ethereum mainnet,
  because Ethereum gas limit increases had cut registration costs by roughly 99% and removed
  the justification for a dedicated rollup.**

> **⚠️ GOTCHA — ENS's own argument against rival namespaces is §21 → `dns-blockchain-naming-alternatives-assessed`'s collision problem,
> stated by an interested party but correct on the merits.** ⚠️ **ENS's blog notes that
> issuing a top-level extension not anchored to the global DNS root creates collision risk:
> if a blockchain service issues `.wallet` and ICANN later delegates `.wallet`, two
> authorities claim the same string — and in a browser, DNS resolves according to the ICANN
> root.**
> ⚠️ **With more than 1,600 applications now filed in the 2026 round, that is not hypothetical —
> and it is why ENS's DNSSEC-import path (§22 → `dns-blockchain-naming-alternatives-assessed`), which uses a name you already own rather
> than inventing an extension, is the architecturally sound answer.**

**⚠️ What survives, and it is real**: ⚠️ **the wallet-address use case.** ⚠️ **Analysis
consistently identifies replacing hex addresses with readable names as the highest-adoption
and genuinely valuable function, with one 2026 assessment recommending traditional DNS for
any public website because "Web3 resolution barriers are too high," and ENS for crypto
identity — describing that as the single best use case.**
**⚠️ Sourcing caution: much of this comes from domain-industry press and crypto media, both
with positions.** ⚠️ **But the direction is corroborated by the strongest possible evidence —
the participants' own actions and admissions: a CEO conceding the category did not cross
over, a major registrar exiting, and the flagship project applying to the incumbent
authority it was built to bypass.**

---
