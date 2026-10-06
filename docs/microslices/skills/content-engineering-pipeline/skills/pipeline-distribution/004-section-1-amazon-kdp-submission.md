---
id: skill-section-1-amazon-kdp-submission-bd9e01aaa7
purpose: section 1 amazon kdp submission
source: src/vibey_tools/skills/plugins/content-engineering-pipeline/skills/pipeline-distribution/SKILL.md
requires: ["skill-critical-pre-submission-manuscript-gate-e960f470ce"]
links: ["skill-section-2-hub-and-spoke-content-distribution-8e6997cd8a"]
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
