---
name: ipfile-patents
description: "Use when deciding whether and how to patent a US invention, especially software or AI: what a patent actually requires, the Section 101 eligibility reality check, the disclosure trap of publishing code before filing, documenting the invention and searching prior art, entity status and the fees that depend on it, the full fee tables, the provisional application step by step, drafting and filing a nonprovisional in Patent Center, prosecution and office actions, issue, maintenance and marking, design patents for icons and interfaces, a worked example, and when a patent attorney or agent is worth paying. Triggers on file a provisional patent, software patent eligibility, Alice, micro entity, Patent Center, office action, maintenance fees, design patent."
---

# US Patents, Trademarks and Copyrights: Filing and Maintenance: Part 3: Patents

> **Part 4 of 7** of the *US Patents, Trademarks and Copyrights: Filing and Maintenance* reference (plugin `patents-trademarks-copyrights`), covering Part 3 (§3.1–§3.13: documentation, search, provisional, nonprovisional, prosecution, maintenance). Sibling skills: `ipfile-overview-and-decision-map` (the executive summary and the one-page decision map (Part 0)); `ipfile-trademarks` (Part 1 (§1.1–§1.13: clearance through maintenance)); `ipfile-copyrights` (Part 2 (§2.1–§2.14: registration portal, deposits, fees, DMCA)); `ipfile-ownership-open-source-and-enforcement` (Part 4 (§4.1–§4.7: ownership, open source, AI-assisted code, trade secrets, international, enforcement, licensing)); `ipfile-budgets-deadlines-scams-and-free-help` (Part 5 (§5.1–§5.5: budget scenarios, a 12-month roadmap, the master deadline table, scam spotting, free and low-cost help)); `ipfile-open-questions-and-glossary` (Part 6 (§6.1–§6.4: unresolved source conflicts, unverified items, what to re-check on filing day) and the glossary).
>
> **Currency:** current as of **October 8, 2026**. Fee schedules, processing times and USPTO or Copyright Office procedures change; every dollar figure carries a source, and the official page to re-check before you pay is named where it matters (`ipfile-open-questions-and-glossary`, §6.4).

> **⚠️ Scope.** General information, **not legal advice**, and it creates no attorney-client relationship. A trademark filed by the wrong owner is void, a missed deadline is expensive to forgive, and publishing code before a patent filing starts a clock: **consult a trademark, copyright or patent attorney or agent before any filing that matters** (each Part says when one is worth paying).

> **The key ideas:**
> 1. **If you publish source code before you file a patent, the clock starts.** The US allows a one-year grace period for your own disclosure; most foreign systems have no general grace period, so file at least a provisional before release if foreign rights matter.
> 2. **Software patents are possible but narrow:** claim a concrete technical mechanism and its improvement, not a computer applying an algorithm (the Federal Circuit remains strict on generic machine-learning and data-processing claims).
> 3. **Government fees are small; lawyers are where the money goes:** about $723 in USPTO fees for one clean micro-entity utility patent including a provisional (self-computed), versus a market estimate of roughly $13,000 to $25,000 or more attorney-drafted through a first office action.

---

## Part 3: Patents (documentation, search, provisional, nonprovisional, prosecution, maintenance)

### 3.1 What a patent actually requires

A US utility patent needs an invention that is eligible subject matter, new ([35 USC 102](https://www.law.cornell.edu/uscode/text/35/102)), non-obvious ([35 USC 103](https://www.law.cornell.edu/uscode/text/35/103)), and described well enough to enable and support the claims, with claims that are definite ([35 USC 112](https://www.law.cornell.edu/uscode/text/35/112)). The claims, not the description or the idea, define what you own. The term is generally 20 years from the earliest nonprovisional filing date ([35 USC 154](https://www.law.cornell.edu/uscode/text/35/154)). A provisional is never examined and never becomes a patent; it only holds a priority date for 12 months.

### 3.2 Software and AI: the Section 101 reality check

1. **The test.** Claims directed to an abstract idea (mathematical concepts, methods of organizing human activity, mental processes) are ineligible unless they add something "significantly more" (*Alice*). Practical drafting lesson from the notes: claim a specific technical mechanism and the improvement it produces, not "apply an algorithm on a generic computer."
2. **USPTO posture is friendlier than the courts.** The August 4, 2025 memo from the Deputy Commissioner for Patents (Kim) told examiners to be more careful about rejecting under mental-process and similar grounds. The Appeals Review Panel decision *Ex parte Desjardins* was designated precedential on November 4, 2025 for a machine-learning training improvement ([Marshall IP summary](https://www.marshallip.com/insights/how-to-navigate-ai-related-patent-applications-after-ex-parte-desjardins/); [Dykema](https://www.dykema.com/news-insights/ai-and-software-patents-in-2025-new-leadership-and-101-eligibility-guidance.html)). A September 29, 2026 memo updates best practices for Rule 132 subject-matter-eligibility declarations (SMEDs) ([Crowell summary](https://www.crowell.com/en/insights/client-alerts/uspto-issues-updated-best-practices-memorandum-on-subject-matter-eligibility-declarations-smeds-under-rule-132)).
3. **The Federal Circuit stays strict.** Opinions reported in the notes: *Recentive Analytics v. Fox* (April 18, 2025; applying generic machine learning to a new data environment is ineligible; [opinion](https://www.cafc.uscourts.gov/opinions-orders/23-2437.OPINION.4-18-2025_2500790.pdf)); *Rensselaer Polytechnic* (2026) and *Dental Monitoring* (2026) in the same line; and a February 24, 2026 affirmance of ineligibility in an AI patent dispute with Amazon ([IPWatchdog](https://ipwatchdog.com/2026/02/24/federal-circuit-affirms-section-101-ineligibility-ai-patent-win-amazon/)). Earlier cases the notes cite on the claim-scope side include *Columbia v. Gen Digital*, *Contour v. GoPro* and *Arendi*. The notes characterize all of these as holdings of the reported opinions; read the opinions before relying on any of them.
4. **An allowed patent can still lose in court.** USPTO examination is a first look, and a court or the PTAB applies eligibility with a harsher eye. That asymmetry belongs in any decision to spend money.
5. **AI inventorship.** The USPTO rescinded its February 2024 AI-assisted inventorship guidance and replaced it with revised guidance in November 2025 (90 FR 54636; [Federal Register 2025-21457](https://www.federalregister.gov/documents/2025/11/28/2025-21457/revised-inventorship-guidance-for-ai-assisted-inventions)). Only natural persons can be inventors; the notes describe the replacement as applying the ordinary conception standard to the human's contribution. If AI materially shaped your invention, record which human conceived each claimed element.

### 3.3 The disclosure trap: publishing code before filing

- In the US you have a one-year grace period after your own public disclosure to file ([35 USC 102(b)](https://www.law.cornell.edu/uscode/text/35/102)). A publicly accessible repository, a conference talk, a blog post or a package-registry upload can all be prior art against you, and the notes treat a public repository as a printed publication if accessible ([MPEP 2128](https://www.uspto.gov/web/offices/pac/mpep/s2128.html)).
- Many foreign systems (the notes cite the European Patent Convention generally) apply absolute novelty with at most narrow exceptions, so a public release before filing can end foreign rights immediately. Confirm the specifics for any country you care about (see 4.7).
- The practical rule: if foreign protection could matter, file at least a provisional **before** the first public commit, README or talk. If US-only, you still start a one-year clock, and the wording of the first public description will be used against your claims.
- Open-source release is usually irreversible. A permissive license on code that implements your claimed invention can also grant patent rights (Apache 2.0, GPLv3 and MPL contain express patent grants; MIT and BSD have none, though implied-license arguments exist). See Part 4.

### 3.4 Document the invention and search

**Idea documentation (free, 1 to 3 hours).** A dated, signed inventor's notebook or document, kept in version control or witnessed, covering: the problem; the prior approaches and why they fail; the specific mechanism; at least two alternative embodiments; the measurable benefit; first date of conception; first date of any public use, offer for sale or disclosure (this triggers the one-year bar). The US is first-inventor-to-file, so notebooks mainly help show derivation and conception for inventorship, not "who invented first."

**Search tools and process.**

| Tool | What it covers | Notes |
|---|---|---|
| [Patent Public Search](https://ppubs.uspto.gov/pubwebapp/) | US grants and published applications, full text | Sign-in will be required starting November 7, 2026, per the notes' recent-changes file; confirm on the live site |
| Google Patents | Worldwide full text | Free, easy keyword start |
| [Espacenet](https://www.epo.org/learning/materials/inventors-handbook/novelty/espacenet.html) | EPO worldwide database | Useful for foreign art and families |
| [CPC](https://www.cooperativepatentclassification.org/) | Classification scheme | Find the class, then page through the neighbors |
| Patent and Trademark Resource Centers | Trained librarians | Clemson (R.M. Cooper Library) and SC State serve South Carolina; see Part 5 |

Search both patents and non-patent literature (papers, documentation, source repositories, product pages). A professional search commonly runs $2,000 to $5,000 (market estimate from a patent-firm blog, [Arapack](https://arapackelaw.com/patents/professional-patent-search/)); it is the most useful money to spend before a nonprovisional because it can save you the filing. A search is not a freedom-to-operate opinion; an FTO opinion answers whether you infringe someone else, usually costs more, and the notes give vendor ranges only ([Finnegan](https://www.finnegan.com/en/insights/articles/when-is-a-freedom-to-operate-opinion-cost-effective.html)).

**Go/no-go checklist before spending money on a nonprovisional.**
1. Does a concrete technical mechanism, not just a business idea, exist?
2. Did a good-faith search turn up nothing that discloses all your elements?
3. Can you state a claim that survives the Section 101 test in 3.2?
4. Would you notice and enforce an infringer (see 4.8)? Litigation is out of reach for most small inventors.
5. Does the invention matter to a customer, investor or acquirer who values patents?
6. If the answer is "defensive only," weigh a defensive publication or an open-source patent pledge (Part 4) against $13,000 or more of prosecution.

### 3.5 Entity status and the fees that depend on it

- **Large entity** is the default. **Small entity** (fewer than 500 employees, no obligation to license to a large entity, same for each inventor) cuts most fees 60%. **Micro entity** cuts them 80% and requires either the gross-income test or the institution-of-higher-education test, plus a limit on prior nonprovisional applications named (37 CFR 1.29; [1.27](https://www.law.cornell.edu/cfr/text/37/1.27); [1.29](https://www.law.cornell.edu/cfr/text/37/1.29)). The USPTO's micro-entity income limit is $262,380, effective September 15, 2026; this figure came from a summarizer and should be confirmed on the live page. The micro-entity form is SB/15A.
- **An LLC you control is evaluated with its owners.** Anyone to whom you have assigned or are obliged to assign rights, or licensed rights, is counted; a license to a large entity can destroy small-entity status.
- **A false claim of status can render the patent unenforceable**, so fix mistakes promptly with the deficiency payment procedure rather than ignoring them (37 CFR 1.28; flagged in the notes as a risk to confirm with counsel).

### 3.6 Fee tables (verified from the USPTO schedule as read in the notes; large / small / micro)

Fee schedule to re-check before paying: [USPTO fee schedule](https://www.uspto.gov/learning-and-resources/fees-and-payment/uspto-fee-schedule). The Financial Manager for paying is at [fees.uspto.gov/FinancialManager](https://fees.uspto.gov/FinancialManager).

| Item | Large | Small | Micro |
|---|---|---|---|
| Provisional filing | $325 | $130 | $65 |
| Utility basic filing | $350 | $140 | $70 |
| Search | $770 | $308 | $154 |
| Examination | $880 | $352 | $176 |
| **Filing + search + exam total** | **$2,000** | **$800** | **$400** |
| Issue fee | $1,290 | $516 | $258 |
| Request for continued examination (first) | $1,500 | $600 | $300 |
| RCE (second and later) | $2,860 | $1,144 | $572 |
| Track One prioritized exam (cap 20,000/yr) | $4,515 | $1,806 | $903 |
| Notice of appeal / appeal forwarding | $905 | $362 | $181 |
| Terminal disclaimer | $183 | | |
| Certificate of correction | $172 | | |
| Non-DOCX filing surcharge | $430 | $172 | $86 |
| Maintenance, 3.5 years | $2,150 | $860 | $430 |
| Maintenance, 7.5 years | $4,040 | $1,616 | $808 |
| Maintenance, 11.5 years | $8,280 | $3,312 | $1,656 |
| Maintenance late surcharge (6-month grace) | $540 | $216 | $108 |
| Petition to revive: unintentional delay | $2,260 | $904 | $452 |
| Petition to revive (higher tier) | $3,000 | $1,200 | $600 |
| PCT transmittal | $285 | $114 | $57 |
| PCT international search fee (USPTO as ISA) | $2,400 | $960 | $480 |

Notes: the extension-of-time fees for responding after the shortened statutory period range from $235 to $3,395 for a large entity (per month of extension). Excess-claim fees (more than 3 independent or 20 total) and continuation surcharges apply; the notes did not list the exact excess-claim amounts, so check the schedule. The small-entity filing total is $800 on the live page; a different secondary source showed $730 and is discounted (Part 6).

### 3.7 Provisional application, step by step

1. **Decide the goal.** A provisional buys 12 months of "patent pending" and a priority date. It must be an enabling disclosure of everything you will later claim; a thin one gives you nothing.
2. **Write the disclosure.** No formal claims are needed, no oath, no IDS. Include: field and problem; detailed description of the mechanism with at least one end-to-end example; diagrams; alternatives and variations; data or results; and a few draft "I claim" paragraphs for your own discipline. Code listings can be attached but cannot replace the explanation.
3. **Prepare the cover sheet.** Use form PTO/SB/16 or an Application Data Sheet (ADS). Name every inventor; mailing addresses are required.
4. **File in Patent Center** as a provisional, upload as DOCX where possible (non-DOCX filings carry a surcharge), pay $65/$130/$325.
5. **Calendar the deadlines.** The nonprovisional (and any PCT or foreign application claiming priority) must be filed within 12 months. A restoration petition can extend to 14 months only for unintentional delay Priority under the Paris Convention is also 12 months for patents.
6. **Do not publish new material** in the interim without a second provisional.
7. **Foreign filing license.** Filing a US application grants a license to file abroad after six months or earlier on the filing receipt; the notes cite 35 USC 184 and 185 and 37 CFR 5.11 but did not verify the procedure, so confirm before filing abroad ([5.11](https://www.law.cornell.edu/cfr/text/37/5.11)).

### 3.8 Nonprovisional (utility) application: drafting and filing in Patent Center

**Parts of the application**: title; cross-reference to the provisional; background; summary; brief description of drawings; detailed description; claims; abstract; drawings ([37 CFR 1.77](https://www.law.cornell.edu/cfr/text/37/1.77) specification order; [1.52](https://www.law.cornell.edu/cfr/text/37/1.52) formatting; [1.72](https://www.law.cornell.edu/cfr/text/37/1.72) title and abstract; [1.84](https://www.law.cornell.edu/cfr/text/37/1.84) drawings). The abstract is limited to 150 words.

**Claim drafting rules the notes emphasize.**
- Every claim term needs support in the specification (written description, enablement, [35 USC 112(a)](https://www.law.cornell.edu/uscode/text/35/112)). New matter cannot be added later ([35 USC 132](https://www.law.cornell.edu/uscode/text/35/132)).
- Claims must be definite (112(b)). Functional "module" and "means" language can trigger Section 112(f) treatment (*Williamson v. Citrix*; [MPEP 2181](https://www.uspto.gov/web/offices/pac/mpep/s2181.html)), which limits the claim to the corresponding structure in the specification, which for software means an algorithm.
- Draft one independent method claim, one system claim and one computer-readable-medium claim within the base fee limits of 3 independent and 20 total claims.
- Put detail into dependent claims so a fall-back exists when an independent claim is rejected.

**Patent Center steps (sequence reconstructed from guidance; the exact screens were not walked in the notes, so treat as unverified).**
1. Sign in to Patent Center with a USPTO.gov account; since September 11, 2025 identity verification through ID.me is mandatory for filers, and a paper alternative (form PTO-2042A) can take up to 10 business days.
2. Start a new submission; choose utility, provisional or other type.
3. Upload the specification, claims, abstract and drawings as DOCX where possible; PDF is allowed with the surcharge. Limits: 25 MB for a PDF, 10 MB for a DOCX, 50 MB for a zip.
4. Complete the web ADS (inventors, applicant, correspondence, priority claims, entity status).
5. Add forms: micro-entity certification (SB/15A) if applicable; IDS if you know of relevant art; declaration (the oath may be deferred until the issue fee if the ADS is complete).
6. Pay fees through the shopping cart; the Financial Manager lets you pay by card, deposit account or EFT.
7. Submit, then download the filing receipt and confirm the application number, filing date and entity status.

**Information Disclosure Statement.** You owe the USPTO any information material to patentability that you know about (37 CFR 1.56). File an IDS ([1.97](https://www.law.cornell.edu/cfr/text/37/1.97)) within the time windows to avoid fees; the notes did not detail the fee tiers.

**Accelerated paths.** Track One ($4,515/$1,806/$903) is a paid prioritized-examination track capped at 20,000 per year, with the cap raised as the older Accelerated Examination program ended (secondary reporting; [MedPath](https://trial.medpath.com/news/uspto-expands-fast-track-patent-program-to-20000-applications-annually-as-accelerated-examination-program-ends)). The After-Final Consideration Pilot 2.0 ended December 14, 2024.

### 3.9 After filing: prosecution and office actions

**Pendency.** On the USPTO dashboard, average first-action pendency was about 20.6 months and total pendency about 29.0 months; a secondary source gave 22.6 months for first action in FY2025. The unexamined backlog was 756,110 at September 29, 2026 ([USPTO patents dashboard](https://www.uspto.gov/dashboard/patents/pendency.html)). Publication occurs at 18 months from the earliest priority date unless you file a nonpublication request when you are not filing abroad.

**How an office action cycle works.**
1. The examiner issues a non-final action with rejections (101, 102, 103, 112) and objections. The response period is normally 3 months, extendable up to 6 months with fees (37 CFR 1.136; the notes flagged details here as not fully verified).
2. You respond with amendments (37 CFR 1.121 formats the amendments; [1.111](https://www.law.cornell.edu/cfr/text/37/1.111) governs the reply) and arguments. Consider an examiner interview, which often resolves issues faster than writing.
3. If the next action is final, options are: file an after-final response, file an RCE ($1,500/$600/$300 first), appeal ($905/$362/$181 at notice of appeal; [37 CFR 41.31](https://www.law.cornell.edu/cfr/text/37/41.31), [41.37](https://www.law.cornell.edu/cfr/text/37/41.37)), or abandon.
4. If allowed, pay the issue fee ($1,290/$516/$258) by the deadline; a continuation filed before issue keeps a family alive.
5. Typical patent costs through allowance are in the budgets in Part 5. The notes pass along market estimates only.

**Typical mistakes at this stage.** Treating the first rejection as final; narrowing claims without recording why; ignoring a rejection under 101 until the end; missing an IDS duty after learning of new art; paying a maintenance fee with the wrong entity status.

### 3.10 Issue, maintenance and marking

- Maintenance fees are due 3.5, 7.5 and 11.5 years after grant; each has a 6-month grace period with a surcharge ($540/$216/$108). Missing it entirely makes the patent expire; reinstatement requires a petition to revive ($2,260/$904/$452 for unintentional delay).
- Mark products "Patent" or "Pat." with the number, or virtual marking via a webpage, to preserve damages ([35 USC 287](https://www.law.cornell.edu/uscode/text/35/287)). False marking is penalized ([35 USC 292](https://www.law.cornell.edu/uscode/text/35/292)). Use "patent pending" only while an application is pending.
- Record assignments with the USPTO Assignment Center ([assignmentcenter.uspto.gov](https://assignmentcenter.uspto.gov/)); an unrecorded assignment can lose to a later purchaser ([35 USC 261](https://www.law.cornell.edu/uscode/text/35/261)).

### 3.11 Design patents (icons, UI, product shapes)

- Fees at filing (basic filing, search, exam combined) are $260 (micro), $520 (small), $1,300 (large), with the issue fee the same amounts, per the notes. Term is 15 years from grant ([35 USC 173](https://www.law.cornell.edu/uscode/text/35/173)), with no maintenance fees.
- Protects ornamental appearance only. The USPTO's March 2026 guidance expanded protection for computer-generated interfaces and icons ([Morgan Lewis](https://www.morganlewis.com/pubs/2026/03/uspto-expands-design-patent-protection-for-computer-generated-interfaces-and-icons)). The Federal Circuit's *LKQ v. GM* (en banc, 2024) changed the obviousness test and the USPTO followed with guidance ([Akin Gump](https://www.akingump.com/en/insights/blogs/ip-newsflash/federal-circuit-overrules-rosen-durling-test-for-design-patent-obviousness-uspto-follows-quickly-with-guidance)).
- The expedited "Rocket Docket" for designs was eliminated ([Federal Register 2025-15497](https://www.federalregister.gov/documents/2025/08/14/2025-15497/eliminating-expedited-examination-of-design-applications)); first-action pendency is about 14 months ([NatLawReview](https://natlawreview.com/article/uspto-reports-faster-design-patent-examinations-what-it-means-seasonal-consumer)).
- Hague system: a design application abroad uses WIPO; the notes give a basic fee of CHF 397 and a USPTO transmittal fee of $130. Confirm on WIPO's current table.
- Design patents are narrow: they stop close copies, not a competing implementation. They fit a distinctive logo-like icon or an interface treatment for a product with real design value, not most developer tools.

### 3.12 Worked example (illustrative, self-composed)

*Illustrative: the claim set below was composed by the notes' authors to show structure. It is not an official sample, it is not a patent of any real party, and it has not been searched for novelty.*

**Scenario.** Example Labs LLC has built "ExampleSync", a streaming data deduplication feature. The technical idea: bound memory use for deduplicating records in an unbounded stream by hashing a normalized subset of fields and checking a rotating probabilistic filter.

1. Founders sign invention assignments to the LLC (Part 4). The LLC holds all rights.
2. Record the invention notebook: problem (duplicate records cost compute), prior approaches (exact hash sets that grow without limit), mechanism (field-specific normalization, fixed-length digest, probabilistic membership structure, rotation), results (memory is capped regardless of record count).
3. Search Google Patents and Espacenet with CPC classes for data deduplication and stream processing; also search papers and open-source repositories. Decide whether claims are novel enough.
4. File a **provisional before** publishing the repo: cost $65 micro / $130 small. Include the described mechanism, alternatives (counting filters, cuckoo filters), configuration options and test results.
5. Within 12 months, file the nonprovisional with a claim set like the following.

> **Claim 1.** A computer-implemented method comprising: receiving a record comprising a plurality of fields; generating a normalized record by applying a field-specific normalization to a selected subset of the plurality of fields; computing a fixed-length digest of the normalized record; querying a probabilistic membership structure held in memory with the digest; when the query indicates the digest is absent, inserting the digest into the probabilistic membership structure and forwarding the record to a downstream consumer; and when the query indicates the digest is present, suppressing the record, whereby memory used for the deduplicating is bounded by a size of the probabilistic membership structure rather than a number of records.
>
> **Claim 2.** The method of claim 1, wherein the selected subset is determined by a configuration identifying fields of a schema.
>
> **Claim 3.** The method of claim 1, wherein the probabilistic membership structure is a Bloom filter that is rotated after a predetermined time window.
>
> **Claim 4.** A system comprising one or more processors and memory storing instructions that, when executed, cause the one or more processors to perform the steps of claim 1.
>
> **Claim 5.** One or more non-transitory computer-readable media storing instructions that, when executed, cause one or more processors to perform the steps of claim 1.

*Drafting notes from the source (also illustrative):* the preamble uses "comprising"; the claims avoid "module" and "means" to stay out of Section 112(f); the set stays within 3 independent and 20 total claims; the specification must support every term, including "selected subset," "field-specific normalization" and "rotated." The "whereby" clause ties the claim to a technical improvement, which is what the Section 101 analysis rewards, though no claim wording guarantees eligibility. Claims 4 and 5 as written refer back to claim 1; a drafter must check that dependent-style references comply with fee counting rules for independent claims.

6. **Expected path.** File with SB/15A (micro) if eligible. Budget for at least one non-final office action, plausibly a Section 101 and 103 rejection, and respond with an interview. A request for a Rule 132 declaration (SME) can help on eligibility. Budget separately for an attorney if the claims matter commercially.

### 3.13 When a patent attorney or agent is worth paying

A registered practitioner (attorney or agent) is the one place the notes consistently advise paying. Verify registration on the USPTO OED roster ([OED practitioner search](https://oedci.uspto.gov/OEDCI/practitionerSearchEntry)). Pay for: the claim drafting (where DIY fails most expensively), the prior-art opinion, any decision about publishing before filing, responses to Section 101 rejections, and anything involving foreign filing. DIY is realistic for a provisional if you write an enabling disclosure; it is much riskier for the nonprovisional. A pro se applicant should call the Pro Se Assistance Program (Part 5).

---
