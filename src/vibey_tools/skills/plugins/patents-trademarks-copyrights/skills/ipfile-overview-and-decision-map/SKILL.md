---
name: ipfile-overview-and-decision-map
description: "Use when deciding what to protect and in what order for a US software product, brand or invention: trademark vs copyright vs patent vs design patent vs trade secret, what each protects and does not, which to file first, government fees and rough total costs, and the nine headline findings (file the name and the code first, treat the patent as a deliberate bet, fix ownership, the publish-before-filing clock, scams, fee-setting caution). Triggers on should I patent my software, trademark vs copyright, how much does it cost to protect my app or brand, what should I file first, USPTO and Copyright Office fees, micro-entity. Start here, then load the Part you need."
---

# US Patents, Trademarks and Copyrights: Filing and Maintenance: Overview and Decision Map

> **Part 1 of 7** of the *US Patents, Trademarks and Copyrights: Filing and Maintenance* reference (plugin `patents-trademarks-copyrights`), covering the executive summary and the one-page decision map (Part 0). Sibling skills: `ipfile-trademarks` (Part 1 (§1.1–§1.13: clearance through maintenance)); `ipfile-copyrights` (Part 2 (§2.1–§2.14: registration portal, deposits, fees, DMCA)); `ipfile-patents` (Part 3 (§3.1–§3.13: documentation, search, provisional, nonprovisional, prosecution, maintenance)); `ipfile-ownership-open-source-and-enforcement` (Part 4 (§4.1–§4.7: ownership, open source, AI-assisted code, trade secrets, international, enforcement, licensing)); `ipfile-budgets-deadlines-scams-and-free-help` (Part 5 (§5.1–§5.5: budget scenarios, a 12-month roadmap, the master deadline table, scam spotting, free and low-cost help)); `ipfile-open-questions-and-glossary` (Part 6 (§6.1–§6.4: unresolved source conflicts, unverified items, what to re-check on filing day) and the glossary).
>
> **Currency:** current as of **October 8, 2026**. Fee schedules, processing times and USPTO or Copyright Office procedures change; every dollar figure carries a source, and the official page to re-check before you pay is named where it matters (`ipfile-open-questions-and-glossary`, §6.4).

> **⚠️ Scope.** General information, **not legal advice**, and it creates no attorney-client relationship. A trademark filed by the wrong owner is void, a missed deadline is expensive to forgive, and publishing code before a patent filing starts a clock: **consult a trademark, copyright or patent attorney or agent before any filing that matters** (each Part says when one is worth paying).

> **The key ideas:**
> 1. **The three rights protect different things, in different offices.** A trademark protects the name and logo, copyright protects the specific code and documentation you wrote (not the idea), a patent protects a claimed technical mechanism that survives examination, and trade secret needs no filing.
> 2. **File the trademark and the copyright first; treat the patent as a deliberate bet.** $350 per class for a federal trademark, $45 or $65 for a copyright registration today, and $65 / $130 / $325 for a provisional patent filing (micro / small / large entity), each sourced in the body.
> 3. **Ownership mistakes and early publication are the expensive silent errors.** Contractor work does not move to an LLC without a signed assignment, and publishing source code before a patent filing starts the one-year US clock (and may end foreign rights).

---

*Currency: current as of October 8, 2026. This is general information, not legal advice, and it does not create an attorney-client relationship. Fee schedules, processing times and USPTO or Copyright Office procedures change; every dollar figure below carries a source, and the official page to re-check before you pay is named where it matters. Anything this research could not verify is listed in Part 6 and is not stated as fact in the body.*

**How to read the labels.** "Verified" means taken from an official page (USPTO, Copyright Office, WIPO, a statute, a court opinion) as read in the research notes. "Self-computed" means arithmetic the notes' authors did from verified numbers. "Market estimate" means law-firm or vendor marketing, a blog or a secondary summary of a survey. "Illustrative" means an example composed by the notes' authors to teach, not an official sample.

---

## Executive summary

1. **The three rights protect different things, and they are filed in different offices.** A trademark protects the name and logo that identify your software or service. Copyright protects the specific code, documentation and visuals you wrote, not the underlying idea. A patent protects a claimed technical mechanism, and only if it survives a novelty, obviousness and eligibility examination. Trade secret, which needs no filing, protects non-public know-how.
2. **File the trademark and the copyright first; treat the patent as a deliberate bet.** A federal trademark costs **$350 per class** at the USPTO ([USPTO 2025 fee changes](https://www.uspto.gov/trademarks/fees-payment-information/summary-2025-trademark-fee-changes)). A copyright registration costs **$45 or $65** today (Single or Standard Application), and the Copyright Office has asked Congress to raise these to $55 and $85 ([Copyright Office fees](https://www.copyright.gov/about/fees.html); [proposed schedule](https://www.copyright.gov/rulemaking/feestudy2026/proposed-fee-schedule.pdf)). A provisional patent filing costs **$65 (micro), $130 (small) or $325 (large entity)** ([USPTO fee schedule](https://www.uspto.gov/learning-and-resources/fees-and-payment/uspto-fee-schedule)).
3. **Government fees are small; lawyers and enforcement are where the money goes.** Fully do-it-yourself USPTO fees for one clean micro-entity utility patent are about $723 including a provisional (self-computed). Attorney-drafted patent work is a market estimate of roughly $13,000 to $25,000 or more through a first office action. Patent litigation medians in the secondary-reported AIPLA 2025 survey are $600,000 to $1 million for mid-size cases.
4. **If you publish source code before you file a patent, the clock starts.** The US gives a one-year grace period for your own disclosure ([35 USC 102](https://www.law.cornell.edu/uscode/text/35/102)), but secondary sources say most foreign systems have no such general grace period. A public repository is a printed publication if publicly accessible ([MPEP 2128](https://www.uspto.gov/web/offices/pac/mpep/s2128.html)). File at least a provisional before release if foreign rights matter.
5. **Software patents are possible but narrow.** The USPTO has become friendlier on Section 101 eligibility (the Aug 4, 2025 memo; *Ex parte Desjardins*), while the Federal Circuit remains strict on generic machine-learning and data-processing claims (*Recentive*, *Rensselaer*, *Dental Monitoring*). Claim a concrete technical mechanism and its improvement, not "a computer applying an algorithm."
6. **Ownership mistakes are the most expensive silent errors.** A trademark application filed by the wrong person is void and cannot be fixed by amendment. Copyright and patent rights in contractor work do not move to an LLC without a signed written assignment.
7. **Deadlines that cannot be forgiven cheaply:** 12 months from a provisional (plus a 2-month restoration by petition), 3 months to answer a trademark office action (plus one paid 3-month extension), the trademark Section 8 window in years 5 to 6, patent maintenance at 3.5, 7.5 and 11.5 years, and, for copyright, registration before infringement or within 3 months of first publication to keep statutory damages and attorney's fees available.
8. **Scams are constant and look official.** Real USPTO email ends in @uspto.gov, and "if it's not in TSDR, it's not an official communication" ([USPTO scams page](https://www.uspto.gov/trademarks/protect/recognizing-common-scams)). Real Copyright Office registration happens only through copyright.gov.
9. **Fee-setting caution.** The USPTO's authority to adjust fees under AIA Section 10 was extended only briefly; sources conflict on whether it ends December 11 or 12, 2026. The Copyright Office's proposed new schedule could take effect around mid-November 2026. Check the live fee pages on the day you file.

---

## Decision map (one page)

### Which right protects what

| Right | Protects | Does not protect | File first when | Verified government fee (entry level) | Typical wait | Upkeep |
|---|---|---|---|---|---|---|
| **Trademark (federal)** | Names, logos and slogans used to identify the source of goods or services, in the classes you list | Functions, ideas, the code itself; names that are generic or merely descriptive | You have, or will soon have, a product or project name people will see | $350 per class (ID Manual entries) | First action about 4.3 months; total about 10.4 months (USPTO averages as of Oct 1, 2026) | Sections 8, 15 and 9: years 5 to 6, then every 10 years |
| **Copyright** | Original expression: source code, documentation, screens, art, text | Ideas, algorithms, methods, functions, titles, short phrases | Before public release if possible; always before you need to sue | $45 Single or $65 Standard (pending increase to $55 and $85) | About 4.1 months overall; 3.4 months with no examiner correspondence | None for registration; DMCA agent renewal if you host others' content |
| **Patent (utility)** | A claimed technical invention that is new, non-obvious, eligible and fully described | Ideas as such; abstract ideas; things you did not claim | The invention is genuinely technical and a business case justifies five figures | Provisional $65 / $130 / $325; filing, search and exam $400 / $800 / $2,000 (micro / small / large) | First action about 20.6 months; total about 29 months (USPTO dashboard) | Fees at 3.5, 7.5, 11.5 years |
| **Design patent** | Ornamental appearance of an article (including icons and some interfaces) | Function | You have a distinctive icon or screen design | $260 / $520 / $1,300 at filing, plus issue fee | About 14 months to first action | None |
| **Trade secret** | Non-public information kept under reasonable secrecy measures | Anything you publish; reverse-engineered or independently derived information | Server-side code, models, data, know-how you will not release | No filing | n/a | Ongoing secrecy practices |

Sources for the table: [USPTO fee schedule](https://www.uspto.gov/learning-and-resources/fees-and-payment/uspto-fee-schedule); [Copyright Office fees](https://www.copyright.gov/about/fees.html); [USPTO processing times](https://www.uspto.gov/trademarks/application-timeline); [Copyright Office processing times](https://www.copyright.gov/registration/docs/processing-times-faqs.pdf); [USPTO patents dashboard](https://www.uspto.gov/dashboard/patents/pendency.html); [SC Code Title 39 Ch. 8](https://scstatehouse.gov/code/t39c008.php).

### What to do first (sequence)

1. **Fix ownership.** Put founder-created code, marks and any inventions into the entity that will own them by signed written assignment, and get assignments from every contractor (Part 4).
2. **Decide the patent question before anything is public.** If a patent might ever matter, file a provisional before the first public release of the code or description.
3. **Clear and file the trademark** in the name of the entity that actually controls the goods or services.
4. **Register copyright** for the release you ship (ideally before publication) and again for major later versions.
5. **Add open-source hygiene** (license, headers, DCO or CLA, trademark policy) so that the filings you made have something to stand on.
6. **Calendar every deadline** the day each filing is made (Part 5 has a master table).

### Rough total costs (self-computed from verified fees; market estimates are labeled as such)

| Scenario for one software product | Government fees in year one | Professional fees (market estimate) | Notes |
|---|---|---|---|
| Name and code only, DIY | $350 to $700 trademark (1 to 2 classes) + $65 copyright = **$415 to $765** | $0 | Use ID Manual entries to avoid $100 to $200 per-class surcharges |
| Name, code and provisional, DIY | About **$480 to $830** (micro entity provisional $65 added) | $0 | Micro or small status must be genuinely met |
| Name, code, provisional and nonprovisional, DIY | About **$880 to $1,230** in year one; $258 more at issue (micro) | $0 | Claim drafting is where DIY fails most expensively |
| Hybrid | Same government fees | About $1,300 to $4,500 for a paid trademark clearance report, attorney analysis and a limited provisional review, and far more if counsel drafts the nonprovisional | Self-computed range; see Part 5 |
| Attorney throughout | Same government fees | Roughly $13,000 to $25,000 or more for the patent path alone, plus $800 to $2,000 per trademark class at a boutique firm | Market estimates; see Part 5 |

Full tables with sources are in Part 5.

---
