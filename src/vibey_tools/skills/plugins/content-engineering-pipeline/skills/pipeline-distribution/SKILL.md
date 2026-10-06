---
name: pipeline-distribution
description: "Use for Phase 14 of the Content Engineering Pipeline: distributing all pipeline outputs across Amazon KDP (Kindle eBook, Paperback, Hardcover), hub-and-spoke digital content, and in-person delivery. Triggers on book publishing, KDP submission, content distribution strategy, Amazon self-publishing, or in-person presentation planning. Also use when asking about the complete pipeline output summary."
---

# Phase 14: Content Distribution
# Content Engineering Pipeline

---

## PHASE 14 ENTRY REQUIREMENTS

Phase 14 is the terminal phase of the content engineering pipeline. It does not begin
until all prior phases are complete and their quality gates have been passed.

The complete pipeline must be confirmed complete before any distribution begins:

```
Phase 1:  Thesis (working claim, target reader, governing postulates)
Phase 2:  Terrain (research, steelmanned opposition, social currency findings)
Phase 3:  Investigation (citation verification, theological integration)
Phase 4:  Assembly (manuscript draft)
Phase 5:  Revision (quality gates, testimony verification)
Phase 6:  Novel Architecture (conversion audit, character designs, setting bible)
Phase 7:  Novel Draft (complete prose manuscript)
Phase 8:  Screenplay Architecture (dramatic spine, beat sheet, visual grammar)
Phase 9:  Screenplay Draft (locked screenplay with scene numbers)
Phase 10: Hub Architecture (extraction point map, visual identity, prompt lexicon)
Phase 11: Hub Draft (completed AI-generated hub film, extraction clips)
Phase 12: Spoke Architecture (five spoke design documents, curiosity cascade)
Phase 13: Spoke Drafts (five spoke assets deployed)
```

Phase 14 distributes what the prior phases have built. Distributing an incomplete
pipeline produces an incomplete result in public, which cannot be undone.

---

## GOVERNING POSTULATES

All distribution decisions are evaluated against the Three Postulates that govern the
entire pipeline: the ones the author stated before Phase 1 — see *Before Phase 1 —
State Your Governing Postulates* in `pipeline-thesis-development`, which also carries
a worked example. The methodology applies equally to any author who brings their own
principles with equal seriousness. The rules this skill applies under the Third
Postulate are the method's **limits on means**: they stand on their own, whatever
words the author's own Third Postulate uses, and that postulate may tighten them but
never loosen them.

The limits on means apply with special force to distribution. No distribution tactic
that requires manufactured urgency, outrage amplification, false social proof,
misrepresented content, or purchased engagement is permitted. The flywheel: right
audience + legitimate means + genuine content + sustained practice = slower but durable
results.

Content engineering generates reach through the quality of the argument, the accuracy
of the research, and the authenticity of the personal voice. Specifically prohibited:
manufactured urgency, emotional manipulation, outrage amplification, false social proof,
misrepresented hub content in spoke hooks, purchased engagement, keyword stuffing to
game Amazon's algorithm, and fabricated testimony. Any tactic that crosses the limits
on means is not a distribution optimization. It is a character contradiction.

---

## CRITICAL PRE-SUBMISSION MANUSCRIPT GATE

This gate is the most important checkpoint in Phase 14. Nothing — not Amazon
submission, not spoke publication, not in-person delivery — proceeds until this gate
is passed. Two steps, both required in sequence.

### Step A: Testimony Replacement

Replace every `[PLACEHOLDER — Category C]` testimony flag in the manuscript with
actual, real, verified personal testimony written by the author from lived experience.
Search the entire manuscript for every instance of `[PLACEHOLDER — Category C]`. This
search must return zero results before submission is permitted.

Why this matters: Testimony is not merely illustrative. In this framework, testimony
is evidence. A fabricated or approximated scene is a lie placed inside an argument
about truth. The limits on means govern here: a work that argues for integrity while
containing invented "personal experience" undermines the argument from the inside. The testimony scenes are the one component of this pipeline that cannot
and must not be AI-generated. They are the author's own witness.

The author may write the scene and ask Claude to help integrate it for voice and flow
consistency. The author may not ask Claude to write the scene, insert a generalized
observation in place of a specific scene, or mark the placeholder as resolved without
inserting actual content.

### Step B: Table of Contents Page Number Verification

Every testimony scene inserted in Step A changes the manuscript's page count. A TOC
built before testimony was inserted will contain wrong page numbers. A print book
submitted to KDP with a TOC pointing readers to wrong pages is a quality failure that
generates quality notices, negative reviews, and potential book suppression.

The correct workflow: (B.1) Complete all content. (B.2) Set final formatting — trim
size, margins, fonts, line spacing, image placement all finalized. (B.3) Generate the
PDF. (B.4) Record actual page numbers from the PDF by opening it and reading the
numbers — do not estimate or calculate. (B.5) Update the TOC using actual recorded
numbers. (B.6) Regenerate the final PDF. (B.7) Spot-verify: open the final PDF and
check at least five TOC entries — the first chapter, the last chapter, and three from
the middle.

Standard nonfiction trim: 6"×9". Mirror margins with gutter widths: 24–150 pages
(0.375" inside), 151–300 pages (0.500" inside), 301–500 pages (0.625" inside), 501–700
pages (0.750" inside), 701–828 pages (0.875" inside). Outside margin minimum: 0.25"
(KDP's margin rules as of September 2026 — verify before relying on it).

The Kindle eBook does not have page numbers in its TOC. Kindle TOC requirement is
navigational: every chapter must have a working internal hyperlink in both the visible
HTML TOC page and the embedded navigational TOC. Verify using Kindle Previewer before
submitting the EPUB.

---

## SECTION 1: AMAZON KDP SUBMISSION

> ⚠️ **Volatile facts (as of September 2026 — verify before relying on it).** Every
> KDP rule in this section is Amazon's to change, and several have changed before:
> character and field limits, supported HTML tags, category counts and the share of
> categories without browse pages, accepted file formats and size limits (including the
> MOBI discontinuation date), royalty tiers and price bands, delivery fees, printing-cost
> formulas, spine-width and cover-wrap dimensions, trim sizes and page-count limits,
> KDP Select terms, publishing timelines, the Expanded Distribution royalty, the Hot New
> Releases window and the badge and BSR thresholds — and Bowker's ISBN prices are
> Bowker's. Confirm each against KDP's current help pages, Cover Calculator and pricing
> pages before you submit or price a book.

Phase 14 submits the book in three formats: (1) Kindle eBook — EPUB file; (2) Paperback
— PDF file; (3) Hardcover — PDF file. These are three separate title setups in KDP.
Begin with the Kindle eBook, then Paperback, then Hardcover.

### Metadata Strategy

Metadata drives discoverability for the life of the book.

**Title and subtitle** — Combined cannot exceed 200 characters. The title must match
the cover exactly. For print books, the title cannot be changed after publication
without creating a new edition and losing accumulated reviews.

**Book description** — Up to 4,000 characters including HTML. Supported tags: br, p,
b, em, i, u, h4–h6, ol, ul, li. The first two to three lines display by default before
"Read more" truncation — these lines must arrest attention and state the claim.

**Categories (3 Amazon Store categories):**
- Category 1 (niche / badge target): the most specific subcategory where the book
  genuinely belongs and where the #1 bestselling book has a BSR high enough that
  5–15 daily sales could claim the badge.
- Category 2 (complementary): a different subcategory targeting a related but distinct
  audience angle.
- Category 3 (broader): a slightly wider category that expands algorithmic reach.

Warning: approximately 27% of selectable Amazon categories lack functional browse pages
and cannot deliver badge eligibility. Confirm each category has an active browse page
and #1 Best Seller badge visible before finalizing.

**Keywords (7 fields, 50 characters each):**
Fill all 50 characters in every slot. Use spaces between terms, not commas. Each unique
word needs to appear only once across all seven fields. Do not repeat words already in
the title or subtitle. Prohibited: competitor author names, Amazon program names,
promotional language, time-sensitive terms, subjective claims.

Strategy allocation: Slots 1–3 for specific 5–7-word descriptive phrases matching how
a reader would search; Slots 4–5 for category-specific terminology anchoring the book
in primary and secondary categories; Slots 6–7 for broader niche terms.

**AI content disclosure** — Because Claude has assisted with research and drafting
throughout this pipeline, select the appropriate AI disclosure. Non-disclosure risks
book removal and account suspension, which jeopardizes all three formats simultaneously.

### 1.3 Kindle eBook Submission

Submit EPUB (not MOBI — MOBI support was fully discontinued March 18, 2025; as of
September 2026 — verify before relying on it). Maximum
file size: 650 MB. The EPUB must contain: a visual HTML TOC page with hyperlinked
chapter entries; a navigational TOC embedded in the EPUB metadata; images in RGB
colorspace (not CMYK); no page numbers in headers, footers, or chapter headings; no
hard-coded margins or fixed font sizes.

**Pricing:** The 70% royalty tier requires a price between $2.99 and $9.99. Formula:
Royalty = 0.70 × (List Price − Delivery Fee), where Delivery Fee = $0.15 per MB.
Recommended launch pricing: $4.99–$7.99 depending on comparable titles.

**KDP Select** commits the eBook to 90-day digital exclusivity on Amazon in exchange
for Kindle Unlimited, Kindle Countdown Deal eligibility, and Free Book Promotions.
This decision must be made before the eBook goes live and cannot be changed retroactively.

Publishing timeline: eBook typically live 24–72 hours after submitting a clean EPUB.

### 1.4 Paperback Submission

Interior file must be PDF with all fonts embedded, transparencies and layers flattened,
no crop marks or watermarks, maximum 650 MB, images minimum 300 DPI.

**Paperback cover** — A single full-wrap PDF (back cover + spine + front cover).
Spine width formula: White paper (B&W): page count × 0.002252"; Cream paper (B&W):
page count × 0.0025". Use KDP's Cover Calculator at kdp.amazon.com/cover-calculator to
generate the exact template. Spine text only permitted for books exceeding 79 pages.
KDP automatically places a barcode (2"×1.2") in the lower right of the back cover.

**ISBN decision:** KDP provides a free ISBN that lists the publisher of record as
"Independently published" and is permanently locked to KDP. Purchase from Bowker
($125 for one, $295 for ten, as of September 2026 — verify before relying on it) if a
custom imprint name is desired, IngramSpark
distribution is planned, or bookstore/library placement is a goal. If the free KDP ISBN
is used and the decision is later reversed, the book must be unpublished and relisted
as a new edition, losing all accumulated reviews.

**Royalty (June 2025 tiered structure; as of September 2026 — verify before relying on
it):** Books priced ≥$9.99 earn 60% of list price
minus printing cost. Books priced <$9.99 earn 50% of list price minus printing cost.
Printing cost for B&W regular trim 6"×9" (110+ pages): $1.00 + (page count × $0.012).
Example for 300 pages at $14.99: Royalty = ($14.99 × 0.60) − $4.60 = $4.39.

**Expanded Distribution** — Enables the paperback through Ingram's network to bookstores
and libraries at 40% royalty minus printing cost. Free to enable; worth doing as a
passive channel.

### 1.5 Hardcover Submission

Uses the same interior manuscript PDF as the paperback. Limited to five trim sizes:
5.5"×8.5", 6"×9", 6.14"×9.21", 7"×10", 8.25"×11". Page count limited to 75–550 pages.

**Hardcover cover differs materially from the paperback cover.** Key differences:
wrap (turn-in) of 0.51" on all outer edges; hinge zone of 0.4" on each side of the
spine (no text, no images in this zone); safe zone of 0.635" from the book edge. Use
KDP's Cover Calculator specifying "Hardcover" as the binding type.

**Royalty:** B&W regular trim printing cost: $5.65 + (page count × $0.012). Example for
300 pages at $22.99: Royalty = ($22.99 × 0.60) − $9.25 = $4.54. Standard nonfiction
hardcovers price between $22.99 and $29.99 for books in the 250–350 page range.

### 1.6 Common KDP Rejection Causes

Cover file errors (most common): dimensions not matching the Cover Calculator template;
images below 300 DPI; title on cover not matching metadata exactly; text or critical
elements outside the safe zone. Interior file errors: margins narrower than required
gutter minimums; fonts not embedded; images below 300 DPI; TOC page numbers not matching
actual pages. Metadata errors: keywords repeating title terms; description containing
URLs, email addresses, or review quotes; AI-generated content not disclosed.

### 1.7 KDP Launch Strategy

Amazon's search algorithm rewards sales velocity above all other signals. A concentrated
burst of sales in the first 30 days produces better long-term ranking than the same
number of sales spread over six months.

All three formats receive a 90-day "Hot New Releases" window after publication. The
orange "#1 Best Seller" badge updates hourly. In well-chosen niche subcategories where
the current leader has a BSR of 50,000–80,000, as few as 5–15 daily sales can claim
the badge. This is why category selection is one of the highest-leverage decisions in
the entire launch.

Distribute ARCs (Advance Review Copies) via BookFunnel, StoryOrigin, or NetGalley
3–6 weeks before launch. Target 20–50 ARC readers; expect a 10–25% review conversion
rate. Coordinate ARC readers to post reviews on or near launch day.

---

## SECTION 2: HUB-AND-SPOKE CONTENT DISTRIBUTION

### The Sequencing Principle

The hub publishes before any spoke. No exceptions. A spoke that arrives before the hub
has nowhere to send traffic. The hub's authority depends on being the first and fullest
expression of the argument.

```
Day 1:         Hub publication (YouTube, newsletter, or podcast primary)
Within 72 hrs: Priority 1 spokes (Social Currency findings — maximum discovery)
Week 2:        Priority 2 spokes (Personal testimony — trust deepening)
Weeks 2–3:     Priority 3 spokes (Practical frameworks — engagement audience)
Weeks 2–3:     Priority 4 spokes (Theological integration — deep audience)
Throughout:    Priority 5 spokes (Contrarian claims — X/Twitter, ongoing)
```

### The Four Content Jobs Framework

Every spoke performs one of four jobs:

**Trust Accumulation** — Personal testimony spokes. Vulnerability before expertise.
Placed in Week 2 after the hub has established the argument.

**Social Currency Distribution** — The reader gains something surprising and repeatable
to share. The Social Currency findings from Phase 2 research that passed the
counterintuitive, empirical, concise, and implicative test. Placed within 72 hours
of the hub.

**Community Deepening** — Theological integration and reflective content. Goes to the
deep audience — the people already engaged. Newsletter and LinkedIn primarily. Weeks 2–3.

**Conversion Invitation** — The CTA that names what the hub (or the book) adds beyond
what the spoke delivered. Present in every spoke, but the hub-adjacent spokes in Week 1
carry the heaviest conversion weight.

### Platform-Specific Publication Standards

> ⚠️ **Volatile facts (as of September 2026 — verify before relying on it).** The
> platform mechanics below — LinkedIn's 62-character first line, its suppression of
> links in the post body and the 60-minute engagement window; quote-tweet debate as
> X/Twitter's primary distribution mechanic; Instagram's carousel "re-show" behaviour
> and the save metric as its primary signal — describe ranking algorithms that change
> without notice. Re-check them against current platform documentation and your own
> data.

**LinkedIn** — Line 1: ≤62 characters, counterintuitive claim or gap that stops the
scroll. No external links in the post body — place the hub URL in the first comment.
The 60-minute post-publish engagement window is non-negotiable: respond to every early
comment substantively. This is the highest-leverage activity in the entire digital
distribution phase.

**Short-form video** — Cold open: drop into the finding mid-sentence. Finding delivered
within 10 seconds. Hook-and-loop: the final second echoes or visually callbacks to the
opening to trigger a rewatch. For multilingual distribution: ElevenLabs dubbing after
Spoke 1 goes live.

**X/Twitter thread** — Tweet 1: the counterintuitive conclusion stated upfront. Tweet 8:
specific CTA naming what the hub adds. Contrarian claims are the strongest X/Twitter
content — they generate quote-tweet debate which is the primary distribution mechanic
on that platform.

**Instagram carousel** — Cover slide: hook at the 62-character standard. Slides 2–4
must function as independent re-entry hooks for the Instagram "re-show" mechanic. Final
slide: CTA with specific value proposition. Save metric is the primary performance signal.

**Email newsletter** — Opening: a personal moment from the hub, written more expansively
than the hub's version. Subject line passes the curiosity gap standard: creates a gap
between what the reader knows and what they will know after opening, without clickbait.

### The Over-Delivery Check

Before publishing any spoke, ask: "If a reader engaged only with this spoke, would they
feel they received the hub's full value?" If yes: the spoke over-delivers. Remove the
resolution. Keep the claim, one piece of evidence, and the implication. The proof lives
in the hub. Over-delivery feels generous but seals the hub from the very readers who
would benefit most from it.

### UTM Tracking Convention

All links to the hub or Amazon page from spokes use UTM parameters:
```
utm_source:   platform (linkedin / tiktok / instagram / twitter / newsletter)
utm_medium:   spoke type (post / video / carousel / thread / email)
utm_campaign: project slug
utm_content:  specific spoke identifier (spoke01 / spoke02 etc.)
```

Target: 15:1 content multiplier ratio. One hub generates 15 or more distinct pieces
of spoke content across platforms. Track and log the content multiplier throughout
the distribution window.

---

## SECTION 3: IN-PERSON DELIVERY

In-person delivery happens after hub publication, and preferably after at least the
first round of spoke engagement — so audience members who have encountered the content
online receive a deeper expression, not a first introduction.

In-person delivery is formation, not information. The difference is the presence of
accountability. Information can be received and set aside. Formation requires a
response — a decision, a commitment, an action step with a named follow-up. Every
in-person format in this framework ends with a commitment that can be checked.

### 3.1 Small Group / Discussion

Purpose: bring the hub's argument into relational accountability. The small group is
where Social Currency findings become personal — where "research says X" becomes
"and here is where that is true in my life."

Discussion questions move in sequence: comprehension → application → personal
accountability. Do not reverse the sequence.

Opening question (comprehension): What is the most surprising thing you encountered?
Application questions (2–3): Where do you see this pattern in a relationship you are
currently navigating? What would it look like to apply this framework this week?
Accountability question (1): What is one specific thing you will do differently before
the next meeting? Name it. Write it down. Tell someone in this room.

The action step must be: one thing (not a list); specific enough to be checked by name;
connected directly to the hub's argument; achievable before the next meeting. Vague
action steps ("I will try to be more present") are not action steps.

Follow-up within 48 hours: send hub URL, anchor phrase, and a reminder of individual
action steps. Document any participant responses that indicate high resonance — these
become potential future Social Currency content (with explicit permission).

### 3.2 Keynote / Speaking Engagement

Purpose: deliver the hub's highest-value elements live. A keynote is a live expression
of the hub's argument.

Talk structure:
- Opening (first 90 seconds): The hub's highest Social Currency finding, stated as a
  claim immediately. The finding in the first 90 seconds opens the curiosity gap — the
  rest of the talk fills it. If the speaker loses the room in the first 90 seconds,
  the room does not come back.
- Development (middle): Two to three arguments that earn the opening claim. Personal
  testimony at the moment the research needs it. For works with a values or worldview
  dimension: name the convergence between evidence and foundational framework
  explicitly — not implied, not assumed, not left for the audience to infer.
- Application (final): What the audience should do differently on Tuesday because of
  what they heard today. One specific action. Not a list of five things.
- Close: The anchor sentence, earned by the content of the talk — placed at the end,
  where it is a conclusion, not a promise. Then: where to find the hub, the book, the
  next step. One URL. One QR code. One action.

Distribution at the event: hub URL and Amazon page URL in slides or printed handout;
QR code on the final slide; quote graphic available for attendee sharing.

Post-event follow-up within 48 hours: email to event organizer with hub link; LinkedIn
post reflecting on a conversation that happened at the event (Priority 2 trust
accumulation spoke — authentic, not promotional).

### 3.3 Workshop

Purpose: deliver the hub's content as formation sustained across multiple sessions.
A keynote creates an insight. A workshop creates a practice.

Each session follows the formation sequence: comprehension → application → accountability.
Apply it per session, not just at the end. Every session opens with an accountability
check from the previous session: "What happened with [action step from last session]?"
This question is the difference between a workshop and a lecture series.

The final session ends with the institutional commitment exercise: each participant names
one institution — a marriage, a team, a church, a business relationship — where they
will commit to faithful, consistent, excellent presence for the next twelve months.
They write it. They share it with the group. They take it with them. That is the
workshop's terminal condition.

Post-workshop: email to all participants within 24 hours with hub link and all session
action steps consolidated. 30-day check-in: "How is [named institution] going?" This
check-in is not optional. It is the point — the accountability that converts a workshop
into formation.

---

## SECTION 4: PERFORMANCE REVIEW AND ITERATION

The performance log begins at first hub publication and runs until the distribution
window closes. Key tracking: BSR at 30 days; ARC review conversion rate; hub-driven
traffic from spokes via UTM data; spoke-by-spoke engagement rates and hub conversion
rates; in-person action step adoption and follow-up completion.

Content multiplier final ratio: track total derivative pieces generated ÷ hub = target
15:1 or higher.

UTM data review scheduled at Day 7, Day 14, and Day 30. Synthesis section completed
at close of distribution window. Lessons documented for next project brief.

Maintain a Consistency Ledger across all projects: publicly stated positions, Three
Postulate invocations, anchor phrase deployments, personal testimony scenes used.
This prevents contradicting a prior stated position without acknowledging the change,
and prevents reusing testimony in a context where it does not serve the new argument.

---

## PHASE 14 QUALITY GATES

**Pre-submission gate:** Search for `[PLACEHOLDER — Category C]` returns zero results;
all testimony confirmed as lived personal experience from the author; print TOC page
numbers updated after testimony insertion; print TOC spot-verified against final PDF
(5+ entries); Kindle navigational TOC verified in Kindle Previewer; EPUB validated;
AI content disclosure noted for KDP submission.

**Amazon submission gate:** All three KDP title setups complete; metadata complete with
3 categories and 7 keyword fields (all 50 chars used); cover files generated from KDP
Cover Calculator template (separate templates for paperback and hardcover); all cover
files at minimum 300 DPI, fonts embedded; interior PDF fonts embedded, layers flattened,
no crop marks; margin minimums verified; ISBN decision made; AI content disclosed; royalty
calculation verified; KDP Select decision made before eBook goes live.

**Digital distribution gate:** Hub published before any spoke; Priority 1 spokes
scheduled within 72 hours of hub; UTM parameters applied to all hub links in spokes;
over-delivery check passed for every spoke; 60-minute post-publish engagement window
confirmed for LinkedIn spokes.

**In-person delivery gate:** Materials prepared; discussion questions adapted for the
specific room; action step is specific and checkable before the meeting; follow-up
communications drafted before the event; follow-up sent within 48 hours; workshop
30-day check-in scheduled.

---

## COMPLETE PIPELINE SUMMARY

Phase 14 is the terminal phase. The complete pipeline from Phase 1 to Phase 14:

Phase 1 (Thesis) → Phase 2 (Terrain) → Phase 3 (Investigation) →
Phase 4 (Assembly) → Phase 5 (Revision) → Phase 6 (Novel Architecture) →
Phase 7 (Novel Draft) → Phase 8 (Screenplay Architecture) →
Phase 9 (Screenplay Draft) → Phase 10 (Hub Architecture) →
Phase 11 (Hub Draft) → Phase 12 (Spoke Architecture) →
Phase 13 (Spoke Drafts) → **Phase 14 (Distribution)**

The Phase 1 working claim has been proven through argument in the research book,
proved through narrative in the novel, demonstrated through drama in the screenplay,
made experiential through image and sound in the hub film, distributed through five
platform-native spoke assets to five distinct audience segments, and now formally
published and delivered to the world.

The flywheel turns on trust. It is slower than manufactured reach. It is also durable.
