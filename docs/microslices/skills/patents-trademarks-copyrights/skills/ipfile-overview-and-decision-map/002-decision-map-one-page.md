---
id: skill-decision-map-one-page-39f2864e65
purpose: decision map one page
source: src/vibey_tools/skills/plugins/patents-trademarks-copyrights/skills/ipfile-overview-and-decision-map/SKILL.md
requires: ["skill-executive-summary-fd6c438451"]
links: []
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
