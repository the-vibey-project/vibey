---
id: skill-part-1-trademarks-clearance-through-maintenance-ffd27daed5
purpose: part 1 trademarks clearance through maintenance
source: src/vibey_tools/skills/plugins/patents-trademarks-copyrights/skills/ipfile-trademarks/SKILL.md
requires: []
links: []
---

## Part 1: Trademarks (clearance through maintenance)

### 1.1 What federal registration gives you, and what it does not

- A Principal Register certificate is prima facie evidence of the mark's validity, your ownership and your exclusive right to use it for the listed goods or services ([15 USC 1057(b)](https://www.law.cornell.edu/uscode/text/15/1057)).
- The filing date works as "constructive use," a nationwide priority date, but only if the mark ultimately registers ([15 USC 1057(c)](https://www.law.cornell.edu/uscode/text/15/1057)). This is the main reason to file an intent-to-use application early.
- After five years of continuous post-registration use, a Section 15 declaration can make the registration incontestable, with exceptions (a generic mark can never become incontestable) ([15 USC 1065](https://www.law.cornell.edu/uscode/text/15/1065)).
- **State registration is a weak substitute.** South Carolina's Secretary of State registers marks for $15 per class with a five-year term, but only for marks already in use, and the state warns that its registration may be affected by prior users and gives no legal advice ([SC Secretary of State](https://www.sos.sc.gov/index.php/services-and-filings/trademarks); [SC application form, Dec 2025](https://sos.sc.gov/sites/sos/files/Documents/Mail%20In%20Service/Trademarks/TrademarkApplication2025_12.pdf)). A state LLC name filing reserves a business name; it is not trademark protection (general knowledge, not fetched in the notes).
- **Common-law rights** arise from use alone and are local. A clean USPTO search does not clear common-law users, because the statute bars a mark confusingly similar to one "previously used and unabandoned" ([15 USC 1052](https://www.law.cornell.edu/uscode/text/15/1052)).

### 1.2 Pick a name that can be registered

Section 2 of the Lanham Act lists the bars. The ones that matter for software names:

| Refusal | Meaning | Can it be overcome? |
|---|---|---|
| 2(d) likelihood of confusion | Too close to a registered mark or an earlier unabandoned user | Not by showing acquired distinctiveness; arguments, narrowing the identification or a consent agreement are the usual routes (practice, not sourced in the notes) |
| 2(e)(1) merely descriptive | The name describes what the software does | Yes: Section 2(f) acquired distinctiveness (five years of substantially exclusive, continuous use may be accepted as prima facie evidence) |
| 2(e)(4) primarily a surname | Mostly a surname | Yes, via 2(f) |
| Failure to function, generic | The term does not identify a source, or names the category | Generic cannot be registered or become incontestable |

Source: [15 USC 1052](https://www.law.cornell.edu/uscode/text/15/1052). For a developer tool, a coined or arbitrary word is the safest; "Task Runner" invites a descriptiveness refusal (inference in the notes).

### 1.3 Clearance: what to search before you file

1. **USPTO Trademark Search** at tmsearch.uspto.gov replaced TESS; the USPTO recommends signing in with your USPTO.gov account, and publishes a getting-started guide, a field-tag searching guide (including regular expressions) and the ID Manual ([USPTO Trademark Search](https://www.uspto.gov/trademarks/search)).
2. **Run a deliberate variant search** (common practice, not a USPTO rule): exact name, plurals, misspellings, phonetic equivalents (ph/f, k/c), translations, compound-word splits, and coordinated classes (9, 42, 35, 41, 45). Include dead and abandoned records for history.
3. **Search outside the register**: state registries, domain names, GitHub, PyPI and npm, app stores, social handles and an exact-match web search. The register shows only federal filings.
4. **Know the limits.** A knockout search you run yourself is free but is not clearance. Market estimates from one vendor page (June 3, 2026): comprehensive search report $300 to $1,500, attorney analysis $500 to $1,500 ([tmarkmetric](https://tmarkmetric.com/insights/trademark-attorney-cost)).
5. **If two searches both find something close, stop and consult a trademark attorney.** A clearance misjudgment costs far more than the filing fee. An opposition or cancellation costs a median $100,000 all-in in the AIPLA 2025 survey (2024 column), versus a $600-per-class filing fee to start one ([AIPLA 2025 Economic Survey](https://www.aipla.org/docs/default-source/adr-neutrals/aipla-2025_report_protected_updated-address.pdf); fee: [USPTO fee schedule](https://www.uspto.gov/learning-and-resources/fees-and-payment/uspto-fee-schedule)).

### 1.4 Set up your accounts before the filing day

1. Create a USPTO.gov account with multifactor authentication.
2. Complete identity verification (online verification usually takes under 15 minutes; a paper option exists). It is mandatory before you can log in to the trademark systems ([USPTO Apply](https://www.uspto.gov/trademarks/apply)).
3. Remember that **Eastern Time controls**: a filing received by 11:59 p.m. ET gets that day's date, and most filings appear in TSDR in four to five business days ([USPTO Apply](https://www.uspto.gov/trademarks/apply)).
4. **Trademark Center** has been the place to file new applications since January 18, 2025. Remaining TEAS forms are retiring on a rolling basis (the USPTO page, last updated Sept 8, 2026, expects the full transition in spring 2027); extension requests for a Statement of Use can now be filed in Trademark Center, while Statement of Use and Amendment to Allege Use forms were "coming soon" ([Trademark Center updates](https://www.uspto.gov/trademarks/apply/trademark-center-updates-and-training)). Because forms move between systems, start each task from the USPTO Apply page rather than a bookmark.
5. Add @uspto.gov to your safe-senders list. The USPTO says it does not extend deadlines when you fail to receive its emails, and that applicants who authorize email are responsible for checking TSDR ([USPTO check status](https://www.uspto.gov/trademarks/apply/check-status-view-documents)).

*Not verified:* the notes could not capture a screen-by-screen Trademark Center walkthrough, so the field list below follows the rules and fee structure, not observed screens. Confirm field names on the live system.

### 1.5 The application: decisions in the order you will meet them

**Step 1: Who is the applicant?** This is the highest-stakes field.

- A use-based (Section 1(a)) application must be filed by the owner of the mark; an intent-to-use (Section 1(b)) application by the person with a bona fide intent to use it. An application filed in the name of the wrong party is void and cannot be corrected by amendment (the rule is 37 CFR 2.71(d), also discussed at TMEP 803.06 and 1201.02(c); see [TMEP 1201.02(c) via BitLaw](https://www.bitlaw.com/source/tmep/1201-02-c.html)).
- Non-correctable examples listed there: a corporate president filing as an individual, a mark assigned to a new corporation before filing, and parent or subsidiary mix-ups. Correctable: a trade name entered as the applicant, minor clerical errors.
- An intent-to-use application cannot be assigned before use is alleged except to a successor to the business ([15 USC 1060](https://www.law.cornell.edu/uscode/text/15/1060)). So filing in the right name at the start matters more than anything you can fix later.
- **Related-company doctrine:** a parent, subsidiary or licensee relationship can save a filing if the applicant controls the nature and quality of the goods or services (TMEP 1201.03, as summarized in the notes; the paragraph text was not preserved for quotation).
- **Practical rule (inference):** apply in the name of the entity that owns the brand and controls quality. If the founder used the name personally first and the LLC will operate the product, document the transfer (assignment with goodwill) or a written license with quality control before filing.

**Step 2: Basis.**

- **Section 1(a)** if the mark is already in use in commerce. Use in commerce means bona fide use in the ordinary course of trade; for goods, the mark is on the goods or associated displays and the goods are sold or transported in commerce ([USPTO base application requirements](https://www.uspto.gov/trademarks/apply/base-application-requirements)).
- **Free software distribution as use.** The Eleventh Circuit held in *Planetary Motion v. Techsplosion* (2001) that free distribution of GPL-licensed software could be use in commerce sufficient to establish trademark rights ([opinion](https://www.courtlistener.com/opinion/75576/)). The notes flag two caveats: it is a circuit case, and it is an ownership and infringement case, not a registration case; no Federal Circuit or TTAB decision squarely on point was found.
- **Section 1(b)** if you have not yet used the mark. It reserves priority from the filing date but adds a Statement of Use step and fees (Section 1.9).

**Step 3: Mark and drawing.** A standard-character drawing protects the words in any style; a special-form drawing protects a particular stylization (general knowledge, not fetched in the notes). Choose standard characters for the name first.

**Step 4: Identification of goods and services and classes.**

- Choose entries from the **ID Manual** (idm-tmng.uspto.gov). Free-form text triggers a **$200 per class surcharge**, an incomplete application a **$100 per class surcharge**, and each additional 1,000 characters of free-form text **$200** ([USPTO fee schedule](https://www.uspto.gov/learning-and-resources/fees-and-payment/uspto-fee-schedule)).
- Software classification: recorded or downloadable software is **Class 9** and must state function and field of use; hosted, non-downloadable software is a **Class 42** service ([TMEP 1400](https://tmep.uspto.gov/RDMS/TMEP/print?href=TMEP-1400d1e2241.html&version=current); [TMEP 1300](https://tmep.uspto.gov/RDMS/TMEP/print?href=TMEP-1300d1e266.html&version=current)).
- The key question for technology services is whether the specimen shows you performing the service for others, or merely providing software users run themselves ([TMEP 1301.04(h)(iii)](https://tmep.uspto.gov/RDMS/TMEP/print?href=TMEP-1300d1e266.html&version=current)).
- *Illustrative wording pattern only (self-composed; confirm against live ID Manual entries):* Class 9, "Downloadable software for [your function]"; Class 42, "Software as a service (SaaS) services featuring software for [your function]" or "Providing temporary use of on-line non-downloadable software for [your function]." The notes could not retrieve verbatim ID Manual entries for any class.

**Step 5: Specimen (required for a use-based filing).**

| Do | Do not |
|---|---|
| Show the mark as actually used with the goods or services | Submit a mockup, printer's proof, digitally altered image or rendering ([USPTO specimen page](https://www.uspto.gov/trademarks/laws/specimen-refusal-and-how-overcome-refusal)) |
| Include the URL and the date you accessed or printed a webpage | Submit a draft website |
| For downloadable software: a screenshot of the real download or store page showing the mark next to the download or purchase control (inference from the point-of-sale and URL-plus-date rules) | Use a page where the mark does not appear with the goods |
| For SaaS: the live sign-up or login page showing the mark and the service (inference from TMEP 1301.04(h)(iii)) | Submit a "contact us" page alone (vendor guidance, [Trama TM](https://www.tramatm.com/specimen-guide/sector/software)) |

The USPTO states that a "beta" label does not by itself make a software specimen unacceptable, but a beta not in actual use in commerce draws a refusal; that language is from the April 2014 TMEP and should be rechecked ([TMEP 900, Apr 2014 version](https://tmep.uspto.gov/RDMS/TMEP/print?href=TMEP-900d1e636.html&version=Apr2014)). The USPTO has terminated more than 52,000 fraudulently filed applications, many involving fabricated or altered specimens, and runs random and directed audits ([USPTO news release](https://www.uspto.gov/about-us/news-updates/uspto-has-terminated-more-52000-fraudulently-filed-trademark-applications-and); [audit program](https://www.uspto.gov/trademarks/maintain/post-registration-audit-program)).

**Step 6: Sign and pay.** The declaration is signed electronically by the applicant or an authorized signatory (general knowledge). Fees are paid by credit or debit card or a deposit account; the USPTO says it never requires wire transfers, gift cards or cash ([USPTO fee information](https://www.uspto.gov/trademarks/trademark-fee-information)). Filing fees are generally not refunded if the mark is refused ([USPTO 1(a) timeline](https://www.uspto.gov/trademarks/trademark-timelines/section-1a-timeline-application-based-use-commerce)).

### 1.6 What happens after you file

| Stage | Use-based path (1(a)) | Intent-to-use path (1(b)) |
|---|---|---|
| Examination | First action averaged 4.3 months; total pendency 10.4 months (USPTO averages as of Oct 1, 2026) ([USPTO wait times](https://www.uspto.gov/trademarks/application-timeline)) | Same |
| Publication | About one month after approval, in the Official Gazette; 30-day opposition window | Same |
| Next | Registration about 3 months after publication if no opposition | Notice of Allowance about 2 months after publication; Statement of Use or extension due within 6 months |
| Statement of Use | n/a | Up to five 6-month extensions; the rule bars a petition allowing a statement of use more than 36 months after the Notice of Allowance ([37 CFR 2.66](https://www.law.cornell.edu/cfr/text/37/2.66)); registration about 2 months after approval |

Sources: [USPTO 1(a) timeline](https://www.uspto.gov/trademarks/trademark-timelines/section-1a-timeline-application-based-use-commerce); [USPTO 1(b) timeline](https://www.uspto.gov/trademarks/trademark-timelines/section-1b-timeline-application-based-intent-use). Note the 1(a) timeline page itself says about 6 to 9 months to examination, which conflicts with the 4.3-month dashboard average; use the dashboard figure for planning and expect variation. A realistic clean 1(a) end-to-end is about 12 to 14 months (inference in the notes).

### 1.7 Office actions: how to read and answer them

1. **Find it.** Official communications are always in TSDR under the Documents tab ([USPTO scams page](https://www.uspto.gov/trademarks/protect/recognizing-common-scams)).
2. **Mind the clock.** The response period is **three months** from issue (shortened from six months in December 2022, per the Federal Register fee rule), extendable **once** by three months (maximum six months) by paying the extension fee, which must reach the Office by the original deadline. Responses by email or fax receive no filing date; use the USPTO's electronic forms ([37 CFR 2.62](https://www.law.cornell.edu/cfr/text/37/2.62); [Federal Register 89 FR 91062](https://www.federalregister.gov/d/2024-26644)). The extension fee is **$125** per the notes' reading of 37 CFR 2.6 and USPTO guidance; one note says the line was not on the fee-schedule table extracted, so confirm on the live schedule.
3. **Read for the type of refusal and answer each ground.**
   - *Specimen refusals:* the five USPTO categories are that the specimen does not show the mark in the drawing, does not show use with the goods or services, does not show your own use, is not in actual use in commerce, or is not an appropriate type for the goods or services. The cure is a substitute specimen plus a verified statement that it was in use in commerce on or before the relevant date ([USPTO specimen page](https://www.uspto.gov/trademarks/laws/specimen-refusal-and-how-overcome-refusal)).
   - *2(d) and 2(e)(1) refusals:* the notes retrieved no primary source on how to answer these (TMEP 1207, 1209, 1212, 1213 were not fetched). Common responses are arguments, amendments to the identification, disclaimers, a consent agreement, a 2(f) claim or the Supplemental Register, but this is background knowledge, not verified. **This is the point at which a trademark attorney is most worth paying**: substantive responses are a market estimate of $1,000 to $3,000, versus $300 to $600 for procedural ones ([tmarkmetric](https://tmarkmetric.com/insights/trademark-attorney-cost)).
   - No USPTO success rate for any refusal type was found; do not rely on any percentage.
4. **If you miss the deadline**, the application is abandoned. A petition to revive costs **$250** and is due two months after the notice of abandonment issues (or, if you never received it, two months after you learn of it and not later than six months after the records show abandonment). It requires an unintentional-delay statement from someone with first-hand knowledge and the response itself ([37 CFR 2.66](https://www.law.cornell.edu/cfr/text/37/2.66); [USPTO 2025 fee changes](https://www.uspto.gov/trademarks/fees-payment-information/summary-2025-trademark-fee-changes)). The notes found no revival route for a registration canceled or expired for missed maintenance.
5. **After a final action** you may respond, request reconsideration, petition ($400), or appeal to the TTAB ($225 per class) ([USPTO fee schedule](https://www.uspto.gov/learning-and-resources/fees-and-payment/uspto-fee-schedule)).
6. **Third parties can intervene.** A letter of protest costs $150; expungement or reexamination requests cost $400 per class.

### 1.8 Opposition and TTAB (if someone challenges you, or you challenge them)

- Fees per class, electronic: notice of opposition $600, petition to cancel $600, ex parte appeal $225; extensions to oppose are $0 for the first 30 days, $200 for the first 90-day or second 60-day request and $400 for the final 60-day request ([USPTO fee schedule](https://www.uspto.gov/learning-and-resources/fees-and-payment/uspto-fee-schedule)). Appeal brief ($200) and oral hearing ($500) amounts come from the FY2021 fee rule and were not reconfirmed ([USPTO TTAB fees](https://www.uspto.gov/trademarks/laws/updated-trademark-ttab-fees-processes)).
- AIPLA 2025 medians for oppositions or cancellations (2024 column): $5,000 through the petition, $50,000 through discovery, $100,000 all-in; averages (n=52) $8,600, $55,800 and $111,900. These are medians from a members-only report as read in the notes.
- The answer deadline after an opposition is instituted was not verified; the notes believe it to be about 40 days but this is unsourced, so do not rely on it. If you receive a TTAB notice, read the deadline on the notice itself and get counsel.

### 1.9 Intent-to-use cycle and fees

| Item (electronic, per class) | Fee |
|---|---|
| Base application | $350 |
| Statement of Use or Amendment to Allege Use | $150 |
| Request for 6-month extension to file Statement of Use | $125 |
| Petition to revive an application | $250 |
| Letter of protest | $150 |
| Petition to the Director | $400 |

Source for all: [USPTO fee schedule](https://www.uspto.gov/learning-and-resources/fees-and-payment/uspto-fee-schedule) and [2025 fee summary](https://www.uspto.gov/trademarks/fees-payment-information/summary-2025-trademark-fee-changes). An intent-to-use filing costs $350 + $150 = $500 at minimum, and $125 per extension (self-computed).

### 1.10 Maintenance: the calendar you must keep

| Filing | Window | Fee per class | Notes |
|---|---|---|---|
| Section 8 declaration of use | Between the 5th and 6th year after registration | $325 | 6-month grace period with an added $100 per class |
| Section 15 (optional incontestability) | After 5 years of continuous use; can be combined with the year 5 to 6 Section 8 | $250 | Combined 8 + 15 = $575 per class (self-computed) |
| Sections 8 and 9 (renewal) | Between the 9th and 10th year, then every 10 years | $325 + $325 = $650 | 6-month grace with $100 per class |
| Madrid-based registrations (serial numbers starting 79) | Same windows, using Section 71 | $325 | Renew with WIPO |

Sources: [USPTO keeping your registration alive](https://www.uspto.gov/trademarks/maintain/keeping-your-registration-alive); [USPTO post-registration timeline](https://www.uspto.gov/trademarks/trademark-timelines/post-registration-timeline-all-registrations-except-madrid-protocol); [USPTO fee schedule](https://www.uspto.gov/learning-and-resources/fees-and-payment/uspto-fee-schedule). Missing the window means the registration is canceled or deemed expired.

**Audits.** A random audit applies when a timely Section 8 or 71 declaration covers at least one class with four or more goods or services, or at least two classes with two or more. The USPTO asks for proof of use for additional items; the response deadline is the later of six months from the office action or the end of the statutory filing period (grace excluded); deleting goods costs **$250 per class** each time; no response cancels the registration ([audit program](https://www.uspto.gov/trademarks/maintain/post-registration-audit-program)). Keep real specimens for every item you list.

**Expungement and reexamination.** Anyone can ask the USPTO to cancel a registration for goods or services never used (expungement: between years 3 and 10) or not used as of the relevant date (reexamination: first 5 years), $400 per class ([USPTO page](https://www.uspto.gov/trademarks/protect/requesting-expungement-or-reexamination-proceeding)). Do not claim goods you do not use.

### 1.11 Worked example: a software product name owned by an LLC

*Hypothetical, composed for teaching. "ExampleSync" and "Example Labs LLC" are placeholders. Not legal advice.*

**Facts.** Example Labs LLC has a downloadable command-line tool and a hosted dashboard named ExampleSync. The founder first used the name personally in a public repository before forming the LLC. The LLC now publishes releases and runs the dashboard.

1. **Fix title.** The founder signs a short written assignment of the name and its goodwill to the LLC (and, in the same document, the code; Part 4). A trademark assignment can be recorded in the Assignment Center for $40 for the first mark and $25 for each additional ([USPTO fee schedule](https://www.uspto.gov/learning-and-resources/fees-and-payment/uspto-fee-schedule); [Assignment Center](https://assignmentcenter.uspto.gov/)). Recording is not required for validity but gives notice (inference). The LLC is the applicant because it owns and controls the quality of both products.
2. **Search** the register for ExampleSync and variants in Classes 9, 42, 35, 41 and 45; search GitHub, package registries, app stores, domains and the web; consider a paid report if anything is close.
3. **Choose basis.** Downloads are live and the dashboard is live, so both classes can be Section 1(a). If the dashboard were not launched, use 1(b) for Class 42.
4. **Draft the IDs** from the ID Manual (illustrative patterns above), stating the actual function.
5. **Capture specimens** with URL and date visible: the release download page with the mark beside the download control (Class 9) and the live sign-up page with the mark and service (Class 42).
6. **File** in Trademark Center as a standard-character mark in two classes. Fee: 2 x $350 = **$700** (self-computed). Any free-form ID adds $200 per class.
7. **Calendar** (see Part 5): response deadline three months after any office action issues; opposition window after publication; Section 8 between years 5 and 6 after registration.
8. **Add a trademark policy** to the repository saying what forks and integrators may do (Part 4).

### 1.12 Common trademark mistakes

- Filing as the wrong applicant, or as the LLC before the assignment exists (void-application risk).
- Using free-form identifications ($200 per class) or leaving fields incomplete ($100 per class).
- Using a mockup or an undated, URL-less screenshot as a specimen.
- Choosing a descriptive name, or never searching beyond the federal register.
- Ignoring emails and TSDR; the USPTO does not extend deadlines for missed mail.
- Claiming goods or services you do not use, which invites audit, expungement or cancellation.
- Paying a "renewal" or "registration" invoice from a private company (Part 5, scams).

### 1.13 When a trademark attorney is worth paying

- Clearance judgment when search results are close.
- Substantive office actions (2(d) confusion, 2(e)(1) descriptiveness).
- Co-owners, a founder-versus-company title problem, or a prior-employer claim.
- Any opposition or cancellation.

A mechanical filing from the ID Manual in standard characters is reasonable to do yourself. A Stanford study of 5,489,586 applications found that having counsel correlated with better outcomes on office actions and oppositions, but the study is correlational ([Stanford Law abstract](https://law.stanford.edu/publications/do-trademark-lawyers-matter)). Market estimate for a flat-fee single-class filing at a solo or boutique firm: $800 to $2,000 in attorney fees, versus $2,500 to $5,000 or more at large firms ([tmarkmetric](https://tmarkmetric.com/insights/trademark-attorney-cost)). Foreign-domiciled applicants must use a US attorney ([89 FR 91062](https://www.federalregister.gov/d/2024-26644)).

---
