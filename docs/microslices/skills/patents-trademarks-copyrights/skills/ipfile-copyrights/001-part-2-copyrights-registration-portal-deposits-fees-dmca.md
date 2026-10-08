---
id: skill-part-2-copyrights-registration-portal-deposits-fees-dmca-2f2e5d3cfe
purpose: part 2 copyrights registration portal deposits fees dmca
source: src/vibey_tools/skills/plugins/patents-trademarks-copyrights/skills/ipfile-copyrights/SKILL.md
requires: []
links: []
---

## Part 2: Copyrights (Registration Portal, deposits, fees, DMCA)

### 2.1 What you already have, and what registration adds

- Copyright attaches automatically when an original, human-authored work is fixed in a tangible form. Notice is optional for works published on or after March 1, 1989 ([Circular 1](https://www.copyright.gov/circs/circ01.pdf)).
- It does not extend to "any idea, procedure, process, system, method of operation, concept, principle, or discovery" ([17 USC 102(b)](https://www.law.cornell.edu/uscode/text/17/102)). For software, registration covers expression (the code, and screen displays if the same owner holds both), not algorithms, functions or system design ([Circular 61](https://www.copyright.gov/circs/circ61.pdf)).
- The "poor man's copyright" (mailing yourself a copy) is not a substitute for registration, according to the Copyright Office FAQ ([general FAQ](https://www.copyright.gov/help/faq/faq-general.html)).
- **Registration is a precondition to suing** for a US work: a copyright owner may sue when the Office registers (or refuses) the claim, not merely when an application is filed (*Fourth Estate v. Wall-Street.com*, 2019; [Justia](https://supreme.justia.com/cases/federal/us/586/17-571/); [17 USC 411](https://www.law.cornell.edu/uscode/text/17/411)).
- **Timing controls remedies.** No statutory damages or attorney's fees for infringement of an unpublished work that began before registration, or for infringement that began after first publication and before registration, unless registration is made within three months after first publication ([17 USC 412](https://www.law.cornell.edu/uscode/text/17/412)). Statutory damages run $750 to $30,000 per work, up to $150,000 if willful ([17 USC 504](https://www.law.cornell.edu/uscode/text/17/504)). A certificate made within five years of first publication is prima facie evidence of validity ([17 USC 410](https://www.law.cornell.edu/uscode/text/17/410)).
- The **effective date of registration (EDR)** is the day the application, fee and deposit are all received in acceptable form, not the day of examination ([17 USC 410(d)](https://www.law.cornell.edu/uscode/text/17/410)).

### 2.2 Choose the right application

| Application | Use when | Fee now | Proposed |
|---|---|---|---|
| **Single Application** | One work, one individual author who is also the sole claimant, not made for hire, not a joint work; electronic only | $45 | $55 |
| **Standard Application** | Everything else: an organization as author or claimant, work made for hire, joint works, derivative versions | $65 | $85 |
| Paper | Rarely worthwhile; slower | $125 | $185 |
| Group options (below) | Specific eligible groupings | See 2.7 | See 2.7 |

Sources: [Circular 11](https://www.copyright.gov/circs/circ11.pdf); [Federal Register 2018-27823](https://www.federalregister.gov/documents/2018/12/27/2018-27823/streamlining-the-single-application-and-clarifying-eligibility-requirements); [Copyright Office fees](https://www.copyright.gov/about/fees.html); [proposed schedule](https://www.copyright.gov/rulemaking/feestudy2026/proposed-fee-schedule.pdf). Misusing the Single Application can bring delay, an extra fee and a later EDR; you can switch to Standard any time before paying ([eCO help](https://www.copyright.gov/eco/help-change.html)). **An LLC-owned codebase almost always needs the Standard Application**, because the claimant is an organization or the work is made for hire.

### 2.3 The Registration Portal and eCO, screen by screen

Start at the Registration Portal at copyright.gov/registration (the real site; see scam warnings in Part 5), which links to the eCO login. Categories there include Literary Works, Other Digital Content (computer programs, databases, websites), Performing Arts, Visual Arts and others ([Registration Portal](https://www.copyright.gov/registration/)). The Office's FAQ suggests the system now uses Login.gov, but the notes could not retrieve the account-creation details. The tutorial PDF is dated (it mentions Windows 7), so rely on it for the order of screens, not for browser advice.

**Overall flow: three steps.** (1) Complete the application, (2) pay, (3) send the work (upload or shipping slip) ([eCO Standard tutorial](https://copyright.gov/eco/eco-tutorial-standard.pdf)).

| # | Screen | What to enter | Notes |
|---|---|---|---|
| 1 | Log in, then "Register a New Claim" | Answer three yes/no questions that route you to Single or Standard | You can change before payment |
| 2 | **Type of Work** | For code, choose **Literary Work** (the list includes computer programs and databases) | Cannot be changed once selected; a wrong choice means starting over ([help](https://www.copyright.gov/eco/help-type.html)) |
| 3 | **Titles** | "Title of work being registered"; optional previous title, larger-work title, series | Use the exact product and version name ([help](https://www.copyright.gov/eco/help-title.html)) |
| 4 | **Publication / Completion** | Year of completion for the version being submitted; publication status; date and nation of first publication | Unpublished works need only the year; see 2.4 |
| 5 | **Authors** | "Add Me" or "New"; citizenship or domicile; individual or **organization** name; "Author Created" boxes | For a work made for hire the employer or commissioning party is the author; an LLC goes in the Organization field ([help](https://www.copyright.gov/eco/help-author.html)) |
| 6 | **Claimants** | The author may always be a claimant; a non-author must own all rights and give a transfer statement: "By written agreement," "By inheritance" or "Other" | An individual author plus an LLC claimant needs "By written agreement" ([help](https://www.copyright.gov/eco/help-claimant.html)) |
| 7 | **Limitation of Claim** | Material Excluded and New Material Included boxes, an "Other" text field, previous registration number ("pending" allowed) | See 2.5 |
| 8 | Rights and Permissions (optional) | Contact for licensing | The email you enter becomes public record ([eCO FAQ](https://www.copyright.gov/eco/faq.html)) |
| 9 | **Correspondent**, Mail Certificate | Person who answers examiner questions; where to mail the certificate | Use a monitored address |
| 10 | Special Handling (optional) | Compelling reason | $800 per claim; see 2.9 |
| 11 | **Certification** | Check the box and type the certifier's name | |
| 12 | Review, optional template, **Pay** | Pay.gov by card, ACH or Copyright Office deposit account; no Pay.gov account is needed | Payment is required before the upload prompt; templates are not available for the Single Application |
| 13 | **Submit Your Work** | Upload the deposit (up to 500 MB per file) or print a shipping slip | Confirm all files are sent or processing cannot start |

Screens 8, 9 and 11 are known mainly from the tutorial; the help pages for rights, correspondent and certification returned 404 in the notes, so confirm wording live. The Office's help line in the tutorial is 877-476-0778 and copyinfo@loc.gov.

### 2.4 Is your software "published"? (It changes the form and the remedies)

- **Publication** means distribution of copies to the public by sale or other transfer of ownership, or an offer to a group for further distribution. Public performance or display alone is not publication ([eCO publication help](https://www.copyright.gov/eco/help-publication.html)). The applicant decides whether the work is published.
- For software, general distribution of the program code by purchase or license, on media or by download, makes it published even if only object code was distributed (Compendium of Copyright Office Practices, Third Edition, 721.9(E)).
- Online: owner-authorized retainable copies make a work published. A download is publication (a "download now" button for software counts); streaming-only is unpublished; an explicit prohibition on downloading may be treated as unpublished; unauthorized posting does not publish; an online ad offering to sell an app is not publication ([Compendium ch. 1000](https://www.copyright.gov/comp3/chap1000/ch1000-websites.pdf); [ch. 700](https://www.copyright.gov/comp3/chap700/ch700-literary-works.pdf)).
- **Inference, flagged in the notes:** a public repository under an open-source license that permits copying and distribution arguably is published; a private or streaming-only service is unpublished. No source states current Office practice for a public GitHub repository. The safest sequence for pre-release code is to register as unpublished before release. For borderline cases, a one-hour consult with counsel is worth it. A good-faith mistake about publication status does not necessarily defeat a registration later (*Unicolors v. H&M*, 2022; [Justia](https://supreme.justia.com/cases/federal/us/595/20-915/)), but that is not a license to be careless.

### 2.5 Limitation of Claim for software, versions and AI-assisted code

- Each version with new authorship is a separate work needing its own application, fee and deposit; unpublished versions may use the group option for unpublished works. A registration of a derivative version covers only new material and excludes previously published or registered code, public-domain code and third-party code ([Circular 61](https://www.copyright.gov/circs/circ61.pdf)).
- Acceptable terms in the claim fields include "computer program," "source code," "software update(s)" and "revision of [x]" (Compendium 721.9(H)). Worked Compendium examples show excluding earlier published versions and third-party modules. The "Note to Copyright Office" field is where you explain version numbers and notice dates.
- **Open-source and third-party code** you did not write must be excluded in Material Excluded.
- **AI-assisted code.** Human authorship is required: the D.C. Circuit affirmed in *Thaler v. Perlmutter* (2025), and the Supreme Court denied review on March 2, 2026 ([Mayer Brown](https://www.mayerbrown.com/en/insights/publications/2026/03/supreme-court-denies-review-in-ai-authorship-case)). The Office's Part 2 report says prompts alone do not give users enough control to be authors, while a human's own expression, creative selection and arrangement, and creative modifications are protectable ([Part 2 report](https://www.copyright.gov/ai/Copyright-and-Artificial-Intelligence-Part-2-Copyrightability-Report.pdf)). The Office's guidance (Federal Register 2023-05321) says to disclose AI-generated content that is more than de minimis, use the Standard Application, describe only the human contribution in "Author Created," and describe the AI-generated content in Material Excluded ([Federal Register](https://www.federalregister.gov/documents/2023/03/16/2023-05321/copyright-registration-guidance-works-containing-material-generated-by-artificial-intelligence)). A pending application with a wrong disclosure is fixed through the Public Information Office; a registered one through supplementary registration. A knowingly inaccurate application can be disregarded by a court under Section 411(b).
- *Illustrative wording, not official:* Material Excluded, "AI-generated code"; New Material Included, "human-authored code, selection, arrangement and modification." No official sample for software was found. Keep prompts, version-control history and manual edits; the "Single Piece of American Cheese" registration succeeded on process evidence, though it was fact-specific ([Fennemore](https://www.fennemorelaw.com/a-single-slice-of-legal-history-what-the-cheese-copyright-means-for-ai-and-ip-law/)).

### 2.6 Deposits for software (Circular 61)

| Situation | What to deposit |
|---|---|
| Standard, no trade secrets | First 25 and last 25 pages of source code of the exact version registered (including the notice page if any); if no clear beginning or end, 50 representative pages; if the program is 50 pages or fewer, all of it |
| Trade secrets in the code: option A | First 10 and last 10 pages, nothing blocked out |
| Option B | First 25 and last 25 pages with trade-secret portions blocked out, if the blocked part is under 50% of the deposit |
| Option C | First 25 and last 25 pages of object code plus 10 or more consecutive pages of source, nothing blocked |
| Option D | Whole program under 50 pages, blocked if under 50% |
| Option E | No clear beginning or end: 20 to 50 representative pages |
| Object code only | Allowed under the **Rule of Doubt** with a written statement that it contains copyrightable authorship |
| HTML | Not a computer program, but human-written HTML can be a literary work; submit the full code |

Source: [Circular 61](https://www.copyright.gov/circs/circ61.pdf). You must state in writing that the code contains trade secrets to use the redaction options, and the Office strictly enforces redaction rules and refuses nonconforming deposits. Scripted languages such as JavaScript count as source code. Documentation and screen displays can be registered with the program if the same owner holds both (and, if published, they were published as a unit). Identifying material is available for some programs (Compendium 1509.1(F)). Electronic upload is allowed for unpublished works and works published only electronically; otherwise choose mail, which prints a shipping slip ([eCO deposit help](https://www.copyright.gov/eco/help-deposit.html)).

**Mandatory deposit is separate.** Section 407 requires two copies of the best edition within three months of US publication of works published in physical form, whether or not you register ([Circular 7D](https://www.copyright.gov/circs/circ07d.pdf)). Works available only online are generally not subject to it ([Circular 66](https://www.copyright.gov/circs/circ66.pdf)). The Section 407 receipt fee is $30, unchanged in the proposal.

### 2.7 Group options (cheaper per work when you qualify)

| Option | Eligibility (summary) | Fee now | Proposed |
|---|---|---|---|
| GRUW | Up to 10 unpublished works, same author(s), same claimant | $85 | $130 |
| GRPPH / GRUPH | Up to 750 published or unpublished photographs, same author and claimant | $55 | $85 |
| GR2D | Up to 20 two-dimensional artworks, one calendar year | $85 | $130 |
| GRTX | Up to 50 short online literary works (50 to 17,500 words); excludes computer programs | $65 | $130 |
| GRCP | Contributions to periodicals, same individual | $85 | $130 |
| GRAM | Album musical works, or album sound recordings and associated works | $65 | $85 / $130 |
| GRSE, GRNP, GRNL | Serial issues, newspapers, newsletters | $35 per issue / $95 / $95 | $50 / $130 / $130 |
| GRNW | News website updates | $95 | $275 (the appendix still shows $350; see Part 6) |
| Databases | Non-photographic updates / photographic | $500 / $250 | $700 / $700 |

Sources: [Copyright Office fees](https://www.copyright.gov/about/fees.html); [proposed schedule](https://www.copyright.gov/rulemaking/feestudy2026/proposed-fee-schedule.pdf); [GRUW page](https://www.copyright.gov/gruw/); [Circular 67](https://www.copyright.gov/circs/circ67.pdf); [Circular 58](https://copyright.gov/circs/circ58.pdf). Eligibility summaries came partly from a summarizer of 37 CFR 202.4; verify counts and conditions on the official page before relying on them. **There is no group option for published software.** A developer with several published releases files separate Standard applications (inference from the absence of such an option in the sources). Several unpublished programs or versions by the same author can use GRUW: $85 for up to 10 versus $65 each.

### 2.8 Fees now versus the pending proposal

- **Current** (the fee page shows no effective date and no pending-change banner): Single $45, Standard $65, paper $125, supplementary registration $100, special handling $800 for a claim and $550 for recordation, DMCA agent designation or amendment $6, first appeal $350, second appeal $700, recordation $95 electronic base ([Copyright Office fees](https://www.copyright.gov/about/fees.html)).
- **Proposed** (Appendix C): Single $55, Standard $85, paper $185, supplementary $85, special handling $1,100, recordation base $215, DMCA agent $25, first appeal $535, second appeal $1,200 ([proposed schedule](https://www.copyright.gov/rulemaking/feestudy2026/proposed-fee-schedule.pdf)).
- **Timing.** The Office submitted the schedule to Congress on July 14, 2026 ([NewsNet 1090](https://www.copyright.gov/newsnet/2026/1090.html)). Under 17 USC 708(b) the Register may implement it 120 days after submission unless Congress disapproves by law. July 14 plus 120 days is about November 11, 2026 (self-computed). The Office says it seeks to implement in the fall of 2026, and trade press says mid-November ([Hypebot](https://www.hypebot.com/2-months-left-before-u-s-copyright-fees-jump-dramatically/)). **No final notice with an exact effective date was found as of October 8, 2026.** Practically: if you are ready, file before mid-November; the fee that applies on the boundary date depends on the Office's stated effective date, which was not found.
- The Office also opened a separate inquiry on alternative fee structures tied to a new registration system (Docket 2026-3), so more change is possible ([Federal Register 2026-05886](https://www.govinfo.gov/content/pkg/FR-2026-03-26/pdf/2026-05886.pdf)).

### 2.9 After you submit

- **Processing.** For cases closed April 1 to September 30, 2026: overall average 4.1 months. Online application plus upload (86% of filings) averaged 3.4 months with no correspondence and 5.3 with it; online application with a mailed deposit (13%) 4.5 and 6.2; paper (1%) 5.0 and 7.5. About 28% of claims needed correspondence ([processing times](https://www.copyright.gov/registration/docs/processing-times-faqs.pdf)).
- **The 45-day rule.** Respond fully to an examiner's email within 45 days of the date it was sent. If you do not, the case is closed, the fee is nonrefundable and re-applying creates a new EDR. The email includes a thread ID to quote in your reply. Official examiner emails come from cop-ad@loc.gov, an @loc.gov address, while scam alerts advise looking for @copyright.gov, so check both ([Jeon v. Anderson attachment](https://www.copyright.gov/rulings-filings/411/jeon-v-anderson-no-8-17-cv-01709-jvs-jde.pdf); [Copyright Office FAQ](https://www.copyright.gov/help/faq/faq-coronavirus.html), which is COVID-era and may be dated). Add the sender to your allow list.
- **Certificate and catalog.** A mailed certificate and an entry in the online public catalog follow approval; refusals are by email with reasons (17 USC 410(b)).
- **Refusal and reconsideration** (Circular 20; 37 CFR 202.5): a first request, in writing with the fee, within three months of the refusal date ($350); a second request, reviewed by a Review Board, within three months of the first decision ($700). Content must include the label "FIRST RECONSIDERATION" or "SECOND RECONSIDERATION," the case number and correspondence ID, claimant, title and reasons; the Office replies within four months, and late submissions foreclose the second request. Whether requests can be submitted online was not confirmed ([Circular 20](https://copyright.gov/circs/circ20.pdf); [Compendium ch. 1700](https://www.copyright.gov/comp3/chap1700/ch1700-administrative-appeals.pdf)). A refused applicant can still sue under Section 411(a) with notice to the Register.
- **Supplementary registration** ($100 now, $85 proposed) corrects or amplifies an existing registration; it does not replace it ([Circular 8](https://www.copyright.gov/circs/circ08.pdf)).
- **Special handling** ($800 now, proposed $1,100) is available only for pending or prospective litigation, customs matters, or contract or publishing deadlines. The target is five working days without a guarantee. A vague worry about infringement probably does not qualify (inference) ([Circular 10](https://www.copyright.gov/circs/circ10.pdf)).

### 2.10 DMCA: takedowns, counter-notices and the designated agent

**If you are sending a takedown notice** (Section 512(c)(3)): it needs a signature; identification of the work; identification of the infringing material with enough detail to locate it; your contact information; a good-faith belief statement; and a statement of accuracy and, under penalty of perjury, authority to act ([17 USC 512](https://www.law.cornell.edu/uscode/text/17/512)). You must consider fair use first (*Lenz v. Universal Music*, 9th Cir., amended opinion March 17, 2016; [opinion](https://cdn.ca9.uscourts.gov/datastore/opinions/2016/03/17/13-16106.pdf)), and a knowing material misrepresentation exposes you to damages, costs and fees under Section 512(f). Registration is not required to send a notice (only to sue; inference).

**GitHub's process:** submit through github.com/contact/dmca or by email to copyright@github.com. For a claim on code carrying an open-source license, a copyright notice alone does not mean infringement. The repository owner typically gets about one business day to fix specified content (not applied when the whole repository is claimed); silence for two weeks is treated as implied retraction; a posted counter-notice triggers a wait of 10 to 14 days, after which the content is restored unless the claimant files suit ([GitHub guide](https://docs.github.com/en/site-policy/content-removal-policies/guide-to-submitting-a-dmca-takedown-notice); [GitHub DMCA policy](https://docs.github.com/en/site-policy/content-removal-policies/dmca-takedown-policy)). The statute says 10 to 14 business days; GitHub's page says "days."

**If your own repository is hit:** a counter-notice requires a statement that you read GitHub's guide, identification of the removed content, your contact details, a good-faith statement under penalty of perjury that the removal was a mistake, consent to the federal district court where you live (or the Northern District of California if abroad) and acceptance of service, and a signature ([GitHub counter-notice guide](https://docs.github.com/en/site-policy/content-removal-policies/guide-to-submitting-a-dmca-counter-notice)). Signing consents to jurisdiction; consider counsel before doing it.

**If you host others' content** (a platform, a forum, a plugin marketplace), the Section 512(c) safe harbor requires a designated agent filed with the Copyright Office, online only, kept current ([DMCA directory](https://www.copyright.gov/dmca-directory/)). The fee is $6 now and $25 proposed. The directory FAQ in the notes says the designation expires after three years unless amended or resubmitted ([DMCA directory FAQ](https://www.copyright.gov/dmca-directory/faq.html)), but the later gap note flagged the renewal rule as not re-verified, so confirm on the page.

### 2.11 Copyright Claims Board (CCB)

A voluntary, no-lawyer-needed forum. Damages are capped at $30,000 in total, with a $5,000 smaller-claims track; statutory damages up to $15,000 per work; a registration or pending application is needed; the time limit is three years; both sides must agree and the respondent has 60 days to opt out ([CCB FAQ](https://ccb.gov/faq/); [CCB opt-out](https://ccb.gov/respondent/opt-out/)). Fee: $40 at filing and $60 within 14 days of the CCB's order once the case becomes active, $100 total ([Federal Register 2022-06264](https://www.federalregister.gov/documents/2022/03/25/2022-06264/copyright-claims-board-initiating-of-proceedings-and-related-procedures)). Whether the 2026 proposal changes CCB fees was not stated.

### 2.12 Worked example: registering a software release

*Illustrative, not official.* Example Labs LLC wants to register ExampleSync 1.0 before the repository goes public.

1. **Confirm authorship and title.** Employee-written code is a work made for hire owned by the LLC. Founder code written before the LLC existed is the founder's until assigned in writing. Contractor code is the contractor's until assigned in writing, because commissioned software rarely falls in the nine statutory work-for-hire categories ([17 USC 101](https://www.law.cornell.edu/uscode/text/17/101); [17 USC 204](https://www.law.cornell.edu/uscode/text/17/204); *CCNV v. Reid*, [Justia](https://supreme.justia.com/cases/federal/us/490/730/)).
2. **Choose the application.** Standard ($65 now, $85 if the proposal takes effect), because the LLC is the claimant.
3. **Fill the screens.** Type of Work: Literary Work. Title: ExampleSync 1.0. Publication: year of completion; unpublished (registering before release). Author: Example Labs LLC, work made for hire (Organization field). Claimant: Example Labs LLC. If any code came from the founder or a contractor by assignment, add the transfer statement "By written agreement." Limitation of Claim: Material Excluded for third-party and open-source dependencies and any AI-generated code; New Material Included for the human-authored code, selection and arrangement. Note to Copyright Office: version number and date range.
4. **Pay.** Pay.gov by card.
5. **Prepare the deposit.** Export the first 25 and last 25 pages of the exact source version as one PDF. If the code contains genuine trade secrets, state that in writing and use one of the redaction options in 2.6 (for example, first 25 and last 25 pages with trade-secret portions blocked if under 50%). Upload under 500 MB and confirm the files are sent.
6. **Expect** a 3.4-month average with no examiner correspondence (5.3 months with it), and answer any email within 45 days.
7. **Version two.** When 1.1 adds substantial new code, file a new application covering only the new material; if the earlier version was unpublished and more are pending, GRUW covers up to 10 for $85.
8. **Optional:** record the founder-to-LLC assignment with the Copyright Office ($95 electronic base now, $215 proposed) to gain legal advantages in priority disputes; recording is optional (Circular 1).

### 2.13 Common copyright mistakes

- Using the Single Application for an LLC or work-for-hire case.
- Publishing first, then registering after the three-month window, and losing statutory damages and fees against an early infringer.
- Letting the contractor-ownership gap persist; the LLC claims what it does not own.
- Omitting third-party or AI-generated code from the exclusion, or depositing the wrong pages or an unredacted trade secret.
- Missing the 45-day correspondence window because the email went to spam.
- Treating the lookalike "registration" sites as the Office (Part 5).

### 2.14 When a copyright attorney is worth paying

For ownership chains (founder, contractors, an old employer), AI-disclosure wording, trade-secret redaction decisions, refusals and reconsideration, and anything headed toward litigation. No sourced attorney price for registration was found, so none is quoted here.

---
