---
name: journal-publishability-criteria
description: Use whenever a research paper, article or preprint is being written, revised, reviewed or published, and specifically before every publication of docs/paper.md. Covers what legitimate journals actually gate on, in order of gating — the editor's desk screen (scope, novelty, package problems), what reviewers judge (methodological soundness, claims the evidence can carry, statistical and qualitative reporting), EQUATOR reporting guidelines, the ICMJE authorship criteria, COPE's view of text recycling, the near-universal generative-AI policy (no AI author, disclosure, author responsibility), TOP 2025 transparency standards, how to verify a journal is legitimate, submitting without an institution, and a pre-submission checklist. Triggers on requests to evaluate, review, prepare or submit a paper, to judge publishability, to write a declarations or data-availability section, to disclose AI use, or to check a journal.
---

# Journal Publishability Criteria: What Makes an Article Publishable in a Real Academic Journal

*Research compiled October 6, 2026.* There is no single universal checklist, because each journal sets its own bar. But the research points to a stable set of criteria that nearly every legitimate journal applies, in roughly this order of gating.

## How this repository applies the criteria to its research paper

The criteria below split into two halves, and this repository holds `docs/paper.md` to both of them every time it tries to publish an update.

The **mechanical criteria** are checked by `python scripts/paper_publishability.py check` (thresholds, headings, phrase lists and paths declared in `scripts/paper_publishability.toml`). It runs on every pull request through `tests/meta/test_paper_publishability.py`, and again in `release-surfaces.yml` before the paper is rendered and published, as the `[documentation] paper_gate` declared in `.vibey-gh.toml`; a paper that fails it is not published. The required checks are: a contribution statement in the abstract and the introduction (§1); an abstract within the venue's length (§1); a `## Declarations` section before the references carrying *Data and code availability*, *Use of generative AI*, *Authorship, funding and competing interests* and *Reporting guidelines and registrations* (§4, §5); an AI disclosure that names its tools and says the author remains responsible (§4); no AI tool among the authors in `CITATION.cff`, and a citation title that matches the paper's (§4); references that each carry a year and a locator (§1, the checklist); a named evidence cutoff; no pending markers; no self-promotion in place of a stated contribution (§1); every mention of a preregistration naming where the registration is (§4, §5); and every reported confidence interval carrying both its bounds (§2). An ORCID iD and a DOI or preprint identifier are recommended and reported, never failed.

The **judgment criteria** are a rubric that a reviewer, human or the review lane, applies to any change to `docs/paper.md`, reporting each unmet criterion as a finding: scope and novelty, stated and judged from the abstract, introduction and conclusion alone (§1); methodological soundness (§2); claims the evidence can carry (§2); estimates reported with intervals and null results reported (§2); reproducible methods (§5); and text recycled from the repository's own documentation cited as such (§4). `python scripts/paper_publishability.py report` prints this rubric beside the mechanical rows, and `--json` carries it under `reviewer`. The review lane loads this skill (`writing-craft@vibey-skills` in `[pr_automation] plugins`) so the rubric is in front of it when the diff touches the paper.

Computer-science systems papers run through conference review, not the health-science journal pipeline, so the EQUATOR table below does not apply to this paper; the paper says so in its Declarations under *Reporting guidelines and registrations* rather than claiming a checklist it did not complete.

---

## 1. The Editor's First Screen (Desk Rejection)

Most rejections happen before a reviewer sees the paper, so this is the highest-leverage stage.

- **Scope fit.** The most common reasons for desk rejection are lack of novelty or being out of the journal's scope. In one study of 898 rejected psychiatry manuscripts, 51.8% of desk rejections cited lack of novelty or originality, and 17.4% were attributed to being out of scope.
- **Novelty and contribution.** Repeating a known study in a new geographic location without new insights is labeled "incremental research." Editors may also judge novelty from the abstract, introduction and conclusion alone, so state the contribution explicitly even if the finding is genuinely new.
- **Triage is noisy.** A 2026 study found editors at the same journal agreed on desk rejection decisions for only 43% of manuscripts at the first screening stage. A desk rejection signals poor fit at that moment, not a verdict on the work.
- **Package problems.** These include language quality, missing statements, and high similarity scores. Some sources say a score above roughly 15-20% can trigger rejection, but that is an informal rule of thumb from a vendor blog, not a standard.

## 2. What Reviewers Judge

- **Methodological soundness.** Inappropriate study designs, poor methodological descriptions, poor quality of writing, and weak study rationale were the most common rejection reasons given by both peer reviewers and editorial re-reviewers. In one journal, poor methodology elaboration accounted for 50.7% of post-peer-review rejections.
- **Claims supported by the data.** Reviewers look for conclusions the evidence can carry, a clear knowledge gap, and a rationale for the design.
- **Statistical reporting.**
  - Report the estimate, confidence interval and effect size together.
  - Don't hang conclusions on p < 0.05 alone (ASA 2016 principles).
  - Run an a priori power analysis.
  - Report null results.
- **Qualitative rigor.** Use a codebook, intercoder reliability checks (e.g., Cohen's kappa) and a documented analytic method (e.g., thematic analysis, grounded theory).

## 3. Reporting Guidelines

For health and many social-science journals, completing the right checklist is effectively mandatory.

| Study type | Guideline |
|---|---|
| Randomized controlled trial | CONSORT |
| Observational (cohort, case-control, cross-sectional) | STROBE |
| Systematic review / meta-analysis | PRISMA 2020 (27 items) |
| Scoping review | PRISMA-ScR |
| Diagnostic accuracy | STARD |
| Qualitative research | SRQR / COREQ |
| Preclinical animal studies | ARRIVE |
| Trial protocols | SPIRIT |
| Prediction models | TRIPOD |

- The **EQUATOR Network** (equator-network.org) maintains the library, covering 500+ guidelines.
- Most journals ask authors to submit the completed checklist alongside the manuscript.
- If a study fits more than one type, use all relevant guidelines.

## 4. Ethics and Integrity (Non-Negotiable Gates)

### Authorship (ICMJE)

Authorship requires **all four** criteria:

1. Substantial contributions to conception or design, or acquisition, analysis or interpretation of data; **and**
2. Drafting the work or revising it critically for important intellectual content; **and**
3. Final approval of the version published; **and**
4. Agreement to be accountable for all aspects of the work.

Anyone who doesn't meet all four belongs in the acknowledgments. Funding acquisition, general supervision, and writing or technical help alone do not warrant authorship. ICMJE published a new edition in January 2026, which moved artificial intelligence into a standalone Section V and added a provision on authors' access to the underlying data.

### Originality and Text Recycling (COPE)

- COPE treats duplicate publication and plagiarism seriously, but overlap is judged by degree. A few recycled sentences are not the same as many repeated paragraphs.
- Recycled methods text is more acceptable than recycled discussion text.
- Short recycled passages in the introduction or methods are generally fine as long as the original work is explicitly cited.
- Duplication of data is likely to always be considered serious.

### Other Required Items

- **Ethics approval:** IRB or ethics committee approval *before* data collection for human and animal studies, with documentation.
- **Conflict-of-interest and funding statements.**
- **Trial registration** where applicable.
- **ORCID iD:** many journals strongly recommend one for all authors.

### Generative AI

The policy landscape is close to universal:

- **No AI tool can be listed as an author.** AI cannot take responsibility for the work, assert conflicts of interest, or manage copyright and license agreements.
- **Disclosure is required.** ICMJE requires journals to ask authors whether they used AI-assisted technologies. Authors should state which tool was used and how. Placement of the disclosure varies by publisher (Methods section, acknowledgments, or a dedicated section).
- **Authors remain fully responsible** for all content, including AI-produced parts, and for verifying AI output and citations.
- **Reviewers generally may not upload manuscripts to AI tools**, because that breaches confidentiality.

## 5. Transparency and Open Science

**TOP 2025** (the updated Transparency and Openness Promotion Guidelines) took effect in 2025.

- It reorganizes the standards into **Research Practices, Verification Practices, and Verification Studies**, with the aim of improving the verifiability of empirical claims.
- At the basic level, authors state whether or not data, materials, code and a reporting guideline are available or used, and if so where.
- Some journals go further. OBHDP, for example, requires all data and analysis code in a trusted repository, follows APA reporting standards, and requires a Research Transparency Statement.
- TOP 2025 dropped the single term "preregistration" in favor of separate outputs (registrations, study protocols, analysis plans, code, materials), with timing described relative to key study activities.
- The preregistration debate is still live, so treat it as a journal-by-journal requirement.

## 6. Choosing a Legitimate Journal

You can meet every criterion above and still lose the paper's value by choosing the wrong outlet.

**Red flags for predatory outlets:**
- Unsolicited invitation emails
- Opaque or hidden fees
- Fabricated or unverifiable editorial boards
- Fake or self-made impact factors (e.g., a "Global Impact Factor")
- False claims of Scopus, Web of Science or PubMed indexing
- Names deliberately similar to established journals
- No verifiable physical address

**Verification steps:**
1. Run the journal through **Think.Check.Submit** (thinkchecksubmit.org).
2. Check **DOAJ**, **Scopus Sources**, and the **Web of Science Master Journal List** directly, not via logos on the journal's own site.
3. Check **COPE** and **OASPA** membership directly.
4. Check the editorial board's actual affiliations.
5. Read several recent articles for quality.

**Caveats:**
- Indexing alone isn't proof. Some predatory journals have a real impact factor and have made it into Web of Science or Scopus, so check several signals together.
- A legitimate but relatively new journal may not yet meet some criteria simply because it lacks a track record.
- Beall's List is archived and not considered a reliable current tool. Cabells is a paid alternative.

## 7. If You're Submitting Without an Institution

- Independent researchers' papers may get more careful scrutiny, because misconduct is harder to investigate without institutional support. They are otherwise not valued less.
- Credibility signals carry more weight: ORCID, transparent data and code in third-party repositories, a clear funding and conflict statement, and pre-submission feedback from colleagues.
- Some journals accept "Independent Researcher" as an affiliation, but this varies. Check the author guidelines first.

---

## Pre-Submission Checklist

- [ ] Target journal's aims, scope and recent issues match the paper
- [ ] One-sentence contribution statement appears in the abstract and introduction
- [ ] Design fits the research question; methods are described reproducibly
- [ ] Matching EQUATOR reporting checklist completed
- [ ] Ethics approval, funding and COI statements in place
- [ ] All authors meet all four ICMJE criteria; contributions documented
- [ ] AI use disclosed; every AI-assisted claim and citation verified
- [ ] Data, code and materials availability statements included
- [ ] Similarity check run; overlap with your own prior work is cited
- [ ] Journal verified as legitimate (DOAJ / Scopus / WoS / COPE / Think.Check.Submit)
- [ ] Reference style matches the journal's house style
- [ ] Cover letter states the novelty and fit

---

## Caveats on These Sources

- Several secondary sources are explainer or vendor sites (e.g., casrai.org guides, manuscript-service blogs), not primary standards. The **primary sources** are ICMJE, COPE, EQUATOR, TOP and the individual journals' policies.
- Rejection statistics come from single-journal studies (largely one psychiatry journal), so treat them as indicative, not universal.
- Humanities, law, mathematics and computer science have different norms. For example, CS often runs through conference review, and humanities weight argument and archival grounding more than checklists. This document does not cover field-specific criteria in depth.
- **The journal's own author guidelines override everything above.**

---

## Sources

**Authorship and ICMJE**
- ICMJE Recommendations: https://www.icmje.org/icmje-recommendations.pdf
- CASRAI ICMJE authorship criteria: https://www.casrai.org/guides/icmje-authorship-criteria
- Clinical Journal of Oncology Nursing (April 2026), "Beyond Checking a Box: Authorship": https://www.ons.org/pubs/article/87501/preview-download

**Desk rejection and reviewer criteria**
- Content analysis of rejection reports, Indian Journal of Psychological Medicine: https://pmc.ncbi.nlm.nih.gov/articles/PMC9022928
- SAJS editors' tips on avoiding rejection: https://www.scielo.org.za/pdf/sajs/v121n9-10/13.pdf
- CASRAI desk rejection guide: https://casrai.org/guides/desk-rejection
- Journal Metrics 2026 desk rejection guide: https://www.journalmetrics.org/blog/desk-rejection-medical-journals-2026-guide
- Manusights, why manuscripts get rejected: https://manusights.com/blog/why-manuscripts-get-rejected

**Reporting guidelines**
- EQUATOR Network: https://www.equator-network.org
- CASRAI EQUATOR routing guide: https://www.casrai.org/guides/equator-network-reporting-guidelines
- Manusights reporting guidelines overview: https://manusights.com/resources/reporting-guidelines

**COPE and text recycling**
- CASRAI COPE guidelines explained: https://casrai.org/guides/cope-guidelines-explained
- COPE European Seminar notes on text recycling: https://libraryblogs.is.ed.ac.uk/openscholarship/2019/09/
- FAPESP Pesquisa, "Dealing with self-plagiarism": https://revistapesquisa.fapesp.br/en/dealing-self-plagiarism/

**Generative AI policy**
- CASRAI ICMJE generative AI policy: https://casrai.org/dictionary/term/icmje-generative-ai-policy
- CASRAI publisher policy landscape: https://casrai.org/guides/ai-in-manuscripts-publisher-policy-landscape
- COPE position on authorship and AI tools: https://publicationethics.org/guidance/cope-position/authorship-and-ai-tools

**Open science and TOP 2025**
- Center for Open Science, TOP 2025 announcement: https://www.cos.io/blog/new-preprint-introduces-major-update-to-the-top-guidelines
- Grant et al. (2026), *Research Integrity and Peer Review* 11:40: https://doi.org/10.1186/s41073-026-00223-0
- AMPPS article on TOP 2025 terminology: https://www.psychologicalscience.org/journals/ampps/25152459251375445/

**Predatory journals**
- CASRAI guide: https://www.casrai.org/guides/how-to-identify-predatory-journals-and-publishers
- Think.Check.Submit: https://thinkchecksubmit.org/journals/
- DOAJ: https://doaj.org/
- Nature Research Academies, "How not to fall for a predatory journal": https://blogs.nature.com/indigenus/2018/10/publishing-tips-how-not-to-fall-for-a-predatory-journal.html

**Independent researchers**
- Editage, "Would my being an independent researcher diminish the value of my work?": https://www.editage.com/insights/would-my-being-an-independent-researcher-diminish-the-value-of-my-work

**Background reference**
- Research methodology reference skill (IMRaD structure, statistical standards, open science, peer review response strategy)
