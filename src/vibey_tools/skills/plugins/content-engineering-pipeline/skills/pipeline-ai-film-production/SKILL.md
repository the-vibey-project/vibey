---
name: pipeline-ai-film-production
description: "Use for Phases 10–13 of the Content Engineering Pipeline: designing and producing the AI-generated hub film from a locked screenplay (Phase 10-11) and then designing and producing the five-spoke content distribution campaign (Phase 12-13). Triggers on AI video generation, hub-and-spoke content model, transmedia distribution, spoke architecture, TikTok/LinkedIn/email content strategy, or AI film production with Sora/ElevenLabs/Kling."
---

# Phases 10–13: AI Film Production and Spoke Campaign
# Content Engineering Pipeline

---

## OVERVIEW: WHAT THESE FOUR PHASES ACCOMPLISH

Phase 10 (Hub Architecture) → Phase 11 (Hub Draft) → Phase 12 (Spoke Architecture)
→ Phase 13 (Spoke Drafts)

These four phases take the locked Phase 9 screenplay and produce: a complete
AI-generated hub film (Phases 10–11), then a five-platform spoke content campaign
designed to drive discovery of the hub film (Phases 12–13).

The hub film is the third conversion in the pipeline. The first conversion
(Phases 6–7) moved from non-fiction research book to novel. The second
(Phases 8–9) moved from novel to screenplay. This conversion moves from
screenplay to produced film — and it introduces the AI tool stack.

---

## PHASE 10: HUB ARCHITECTURE

### What the Hub Film Is and What It Must Do

The hub film serves two simultaneous functions that its production must honor
simultaneously. As a standalone film, it delivers the controlling idea the
pipeline has been building since Phase 1. As a content architecture anchor,
it is the pillar asset from which the spoke system of Phases 12–13 will extract,
reformat, and distribute across five platforms.

Gary Vaynerchuk's reverse pyramid model requires a pillar content piece dense
enough in extractable material to yield 15 or more derivative pieces. For a hub
film, this means scenes must be designed as modular sequences: self-contained
enough to produce emotional impact without full narrative context, yet specific
enough to drive curiosity toward the complete hub experience. Every significant
scene must be designed with both its in-film function and its out-of-film
extractability in mind simultaneously.

A film that works only as narrative and not as extractable content is not a hub.
A collection of extractable moments that does not cohere as a film is not a hub.

Jonah Berger's research establishes that stories are the optimal sharing vehicle —
"Trojan Horses" carrying information under the guise of narrative — and that
high-arousal emotions, particularly awe, are the single strongest driver of virality.
For awe moments to be extractable as spokes, they must be designed as modular
sequences with both in-film and out-of-film function.

### The AI Tool Stack: Strengths and Failure Modes

The AI tool stack available for hub production includes tools with specific
performance profiles that make each optimal for specific scene types. These are
not interchangeable.

> ⚠️ **Volatile facts (as of September 2026 — verify before relying on it).** Every
> tool name, model version, capability, duration limit, resolution, partnership and
> price in this section is a dated claim about a fast-moving market: Sora 2 (25-second
> clips, up to 4K, native 9:16, synchronized audio, the Disney partnership), ElevenLabs
> (inline emotional tags, Sound Effects v2), Nano Banana 2 (Google Gemini 3.1 Flash
> Image: up to 4K, text rendering, character consistency, $0.039 per image), Kling AI
> 2.0 (120-second single generations), MuseTalk 1.5, Wav2Lip-HQ and Google Veo 3.
> Check each vendor's current documentation and pricing before planning a production
> around it.

**Sora 2** generates clips up to 25 seconds at up to 4K resolution in both 16:9
and native 9:16 formats, with synchronized dialogue, sound effects, and music.
Primary tool for scenes where visual spectacle, environmental atmosphere, or
action is the dominant element. Its Disney partnership production-grade positioning
makes it the highest-quality option for scenes where the visual world carries the
argument. Failure mode: attempting multiple simultaneous choreographic events in
a single generation produces unreliable results. One camera move plus one subject
action per generation maximum.

The image-to-video workflow is the preferred method for every extraction point
scene. Generate the exact frame from Nano Banana 2 first, then animate that
reference frame using Sora 2's image-to-video mode. Text-to-video produces
general results from descriptions; image-to-video produces specific results from
a designed source frame.

**ElevenLabs** handles every character voice in the film regardless of which
visual tool is used for the footage. Audio consistency standard: using ElevenLabs
for all voice generation means all character voices share the same production
quality register. Supports inline tags for emotional control — [softly], [whispers],
[with restrained contempt], [voice breaking] — derived from the Phase 8 Coppola
five-category analysis. Failure mode: generating dialogue with neutral delivery and
attempting to correct emotional register in post-production. Specify the delivery
in the prompt.

ElevenLabs also handles ambient room tone generation (Sound Effects v2): the
specific acoustic character of each physical space layered under character dialogue.
This is the AI equivalent of Ben Burtt's "worldizing" technique. Prompt for room
tone must name the specific space and its acoustic qualities concretely: not
"interior ambience" but "small kitchen, low ceiling, tile floor, fluorescent hum,
slight refrigerator vibration."

**Nano Banana 2** (Google Gemini 3.1 Flash Image) generates still assets at up to
4K resolution with accurate text rendering and character consistency, at $0.039 per
image. Primary tool for title cards, reference images, atmospheric stills, and any
in-frame visible text. Its text accuracy far exceeds the video generation tools.

**Kling AI 2.0** supports up to 120 seconds of single-generation duration with
strong facial performance quality. Primary tool for scenes where sustained character
presence and emotional expressiveness are the dominant requirements. Its longer
generation window allows full scene coverage without cut-assembly work. For dialogue
scenes, use the video-first then lip-sync workflow: generate character performance
visually using Kling AI, then apply MuseTalk 1.5 or Wav2Lip-HQ to synchronize the
separately-generated ElevenLabs audio to the generated video.

**Google Veo 3** provides the highest quality audio-visual synchronization across the
tool stack. Optimal choice for extraction point scenes where the emotional peak
depends on the specific quality of a character's delivery synchronized precisely with
their visible emotional state — typically the All Is Lost scene, the Break into Three
moment, and the Closing Image.

### Pre-Production Design Work

Two Phase 8 documents feed directly into Phase 10 work:

`08_spine_and_anchors.md` and `08e_visual_grammar.md` contain the visual grammar
designed for each primary location and the compression character designs that defined
each character's visual signature. These become production design specifications: visual
grammar notes are translated from cinematic intention into prompt-engineering language,
and character visual signatures become the reference image descriptions that ensure
consistency across multiple AI generations.

For each primary location, the visual identity specification must name at least one
specified imperfection. Generation tools default to pristine, hyper-detailed, slightly
synthetic aesthetics — every surface looks new, every texture looks described. George
Lucas and art director Roger Christian built Star Wars' visual authority by making
everything worn, used, and imperfect — the "used future" aesthetic — which made a
science fiction world feel inhabited rather than designed. The prompt vocabulary for
any scene that should feel real must include imperfection details explicitly, because
the generation model will not add them unless specified.

The Prompt Lexicon (`10f_prompt_lexicon.md`) is the most important production tool
for Phase 11 consistency. It contains Constant Character Prompts (one verbatim
paragraph per major character) and Constant Style Prompts (one block per primary
location). The discipline it enforces is absolute: no generation prompt is written
from memory. The character description that goes into every prompt is the same text
that went into every prior prompt, copied from the same source. Any variation in
character description language produces variation in generated appearance.

### Phase 10 Production Design Documents

**10_extraction_point_map.md** — The hub film's content architecture blueprint.
Lists every extraction point organized by tier (Tier 1: inciting incident, All Is
Lost, most quotable dialogue, character's defining decision, most visually iconic
sequence; Tier 2: midpoint reversal, key conflict scenes, thematic revelations;
Tier 3: production design details, character introductions, tonal moments). For
each point: page reference, self-contextualizing description, spoke assignments,
9:16 generation flag, curiosity cascade logic (what fragment does this reveal and
what 30–40% does it withhold), and Interest Market Cap framing (high-reach framing
of the curiosity gap rather than clinical framing).

**10b_visual_identity_spec.md** — Full prompt vocabulary for every primary location:
lighting temperature and direction, color palette with specific reference descriptors
(not just "warm" but "amber tungsten warmth, shadows cool blue-grey"), texture and
grain character, camera-to-subject spatial relationship, recurring motif detail stated
in visual terms a generation model will render consistently, and at least one specified
imperfection per location.

**10c_character_reference_lib/** — One subfolder per major character containing the
written reference description in prompt-ready language, the voice profile specification,
ElevenLabs parameters, and three to five Nano Banana 2-generated reference images.
Reference images are the Phase 10 most important technical output — they are generated
during Phase 10, not Phase 11, because evaluating their adequacy as consistency anchors
is an architecture decision, not a production decision.

**10d_tool_assignment_map.md** — Every scene with tool assignment, justification based
on the scene's specific requirements, and generation estimate. Also includes the
generation prompt template for each scene (not the final prompt, but the template
establishing what the prompt must contain: character reference, location and visual
identity specification, action description, emotional register, technical requirements).

**10e_technical_specs.md** — All production parameters: 4K resolution (3840×2160),
24fps, ProRes or H.265, separate audio stems for dialogue, sound effects, and music.
Aspect ratio decision (16:9 primary, 9:16 for flagged extraction points). Reformatting
pipeline, caption generation standard (97% minimum), UTM parameter convention.

**10f_prompt_lexicon.md** — Copy-paste production document. Constant Character Prompts
and Constant Style Prompts formatted for copy-paste use during generation sessions.
Kept open during all Phase 11 generation sessions.

### Phase 10 Quality Gate

Phase 10 is complete when: the extraction point map lists a minimum of six primary
extraction points with curiosity cascade logic and Interest Market Cap framing; the
visual identity specification covers every primary location including specified
imperfections; the character reference library has a complete entry with generated
reference images for every major character; the tool assignment map covers every scene;
the technical specifications sheet is complete; the Prompt Lexicon is assembled and
verified against reference images; and the Hub Fidelity standard has been applied to
every extraction point.

---

## PHASE 11: HUB DRAFT

### Production Sequence

Produce in this order:

1. Phase 10 gate confirmation — all five architecture documents complete, character
   reference images approved, extraction point map finalized.
2. Opening Image and Closing Image — produced first, at full visual identity
   specification, 4K in both 16:9 and 9:16 formats. The Opening Image generation
   is the quality control test for the entire visual identity system. If it does not
   accurately reflect the visual identity specification, revise the specification
   before proceeding.
3. All Is Lost scene — produced second, using Veo 3 or Kling AI. Generate
   ElevenLabs audio for every character line before generating visuals, since vocal
   delivery quality of the rupture scene is the emotional reference against which
   every other performance in the film will be measured.
4. Extraction point scenes — produced third, in screenplay order. These are the
   content architecture nodes around which the entire spoke system will be built.
5. Connective scenes — produced fourth, in screenplay order. Primarily dialogue-driven.
   Introduce deliberate micro-level sentiment variation within warmth scenes — research
   confirms content with greater period-to-period shifts in emotional tone engages
   audiences significantly more than content with a consistent register.

> ⚠️ **Volatile facts (as of September 2026 — verify before relying on it).** The
> tools named in this sequence and the assembly pass below — Veo 3, Kling AI,
> ElevenLabs, DaVinci Resolve, Adobe Premiere Pro, CapCut, the Film Look Creator
> treatment, and OpusClip's ClipAnything with its 0–99 Virality Score — change
> features between releases.

Assembly uses DaVinci Resolve, Adobe Premiere Pro, or CapCut. Apply the Film Look
Creator treatment uniformly across all assembled footage before export — consistent
grain, halation, and bloom applied to unify segments generated by different tools.
Export at 4K 16:9 in ProRes or H.265 with separate audio stems.

After master export, run the extraction pass using OpusClip's ClipAnything AI to
auto-detect 10–25 high-engagement moments. Critical caveat: the Virality Score
(0–99) is an unreliable ranking signal. Use it as a first-pass filter only. Evaluate
every generated clip against the Phase 10 extraction point map independently of its
score. A clip that corresponds to a Tier 1 extraction point belongs in the spoke
system regardless of how OpusClip scored it.

### Phase 11 Quality Standards

**The Dual Function Test** — Watch the complete assembled hub film twice. First
viewing: does the film deliver the controlling idea through earned emotional
experience? Second viewing: are the extraction point scenes genuinely self-
contextualizing — would a viewer encountering them without the full film feel genuine
curiosity rather than confusion? Both tests must pass.

**The Visual Consistency Test** — Watch with attention exclusively to visual
consistency: does each character maintain the same visual identity across all
generated sequences? Does the lighting temperature hold within the range specified?
Does the color palette remain coherent across scenes generated by different tools?

**The Relational Science Authenticity Test** — Does the AI-generated performance
in each dialogue scene accurately render the attachment operating system behavior
designed in Phase 6? Does the All Is Lost scene's contempt read as cold and
dismissive rather than as generic anger? Does the autistic character's masking
appear as a constant background visual cost rather than only at the dramatic
unmasking moment?

**The Hub Fidelity Test** — Preview three extraction point scenes in isolation
and evaluate whether they accurately represent the hub film's actual emotional
register, thematic content, and moral complexity. A preview that makes the film
appear more simply resolved than it is fails. The emotion the spoke will promise
must be the emotion the hub delivers.

The editorial principle governing all selection decisions: choose emotional truth
over continuity. As Thelma Schoonmaker articulated it: "The priority is absolutely
on the best take for performance." Performance is what the audience experiences;
continuity is what they notice only when it breaks significantly.

---

## PHASE 12: SPOKE ARCHITECTURE

### The Five-Spoke System and Behavioral Modes

The five spokes are not independent campaigns. They are five angles of a single
curiosity cascade: each spoke reveals a different fragment of what the hub contains,
no single spoke provides a complete picture, and all five create distinct curiosity
gaps that only the hub can resolve.

Henry Jenkins' transmedia storytelling framework governs the architecture: "integral
elements of a fiction get dispersed systematically across multiple delivery channels
for the purpose of creating a unified and coordinated entertainment experience."

> See also: `writing-craft:narrative-structure`, which covers transmedia narrative
> frameworks on their own terms.

The five spokes and the three behavioral modes they reach:

**Spoke 1: Short-form video (TikTok + Instagram Reels + YouTube Shorts simultaneously)**
Reaches passive discovery — audiences who have not sought out the hub and encounter
the spoke while scrolling. Widest reach, lowest context.

**Spoke 2: LinkedIn post and carousel**
Reaches intellectual engagement — professional and faith-adjacent audiences who
respond to ideas and arguments, and share content to signal cultural and professional
positioning (the A24 Social Currency principle in the professional context).

**Spoke 3: X/Twitter thread**
Reaches intellectual engagement — the culturally literate segment whose engagement
is driven by ideas, arguments, and behind-the-scenes creative reasoning.

**Spoke 4: Instagram carousel**
Reaches depth audiences — visually engaged people who will spend extended time with
the material, save it for re-reading or re-viewing, and represent the highest-
probability path to hub consumption.

**Spoke 5: Email newsletter**
Reaches depth audiences — people who have already opted into an ongoing creative
relationship and who represent the highest conversion probability.

### The Curiosity Cascade Architecture

George Loewenstein's information gap theory governs every extraction point decision:
the spoke reveals 60–70 percent of the context and withholds the critical 30–40,
and that withheld portion is something the audience genuinely wants to know.

The test that distinguishes legitimate curiosity gap from clickbait: does the emotion
deepen with more context (legitimate) or collapse with more context (clickbait)?

Three cascade rules all five spoke design documents must comply with:

1. No two spokes reveal the same fragment. If two spokes draw from the same
   extraction point, an audience member who encounters both receives no additional
   information from the second spoke.

2. The five spokes are sequenced so each increases the depth of engagement required.
   Short-form video asks for 30 seconds; LinkedIn asks for 3–5 minutes; X/Twitter
   asks for 8 tweets and consideration of a response; Instagram carousel asks for
   10 slides and a save; email newsletter asks for 400–600 words plus an audiogram.
   This depth gradient is the funnel architecture.

3. The five spokes collectively span the hub film's emotional range. Two spokes
   (short-form video and X/Twitter) assigned high-arousal extraction points; two
   spokes (Instagram carousel and LinkedIn carousel) represent visual and intellectual
   depth; email newsletter represents personal and relational intimacy.

### The 90-Day Campaign Sequence

The three-act structure of the screenplay maps onto the awareness-engagement-conversion
funnel:

Act 1 material — character introductions, world-building, inciting incident teasers —
maps to awareness-stage spokes in the pre-release phase. Act 2 material — conflict
escalation, midpoint reversals, character decision moments — maps to engagement-stage
spokes in the launch phase, when the hub is available. Act 3 material — carefully
spoiler-gated climactic sequences, thematic resolution — maps to conversion-stage
spokes in the sustained phase.

During the pre-release phase, maintain 3–5 posts per week with an 80/20 content
ratio: 80 percent value or entertainment content, 20 percent promotional. The
governing philosophy: New Line's LOTR campaign stated it explicitly — "Not until
the movie comes out do we want to ask the audience for anything. Until then, it's
all about giving things to them."

### The Five Individual Spoke Architectures

> ⚠️ **Volatile facts (as of September 2026 — verify before relying on it).** The
> platform mechanics and performance figures in this section describe ranking
> algorithms and benchmarks that change without notice: TikTok's weighting of
> completion and rewatch rate and the 21–34-second window; LinkedIn's suppression of
> links in the post body, its 150-character mobile truncation and the 3–5× carousel
> figure; X/Twitter's suppression of early links and the 3× thread figure; Instagram's
> 1080×1350 format, its re-showing of carousels from Slides 2–4 and the 10%-versus-7%
> engagement figures; and the up-to-300% email click-through figure. Re-check them
> against each platform's current documentation and your own data before relying on
> them.

**Spoke 1: Short-form video (21–34 seconds)**
Hook-body-gap architecture: 3-second scroll-stop hook, 20–28 seconds building
toward maximum tension without resolution, end card directing to hub. Maximum
effective duration 21–34 seconds for TikTok completion rate optimization.
Consider the hook-and-loop technique: show a specific visual detail or character
reaction in the first 2–3 seconds without context, then reveal what produced that
moment, exploiting TikTok's heavy weighting of rewatch rate.

**Spoke 2: LinkedIn post and carousel**
Two-part design: text post (8–12 lines, first 150 characters as the mobile truncation
hook), plus 7–10 slide carousel uploaded as PDF. LinkedIn's algorithm suppresses reach
for posts with external links in the body — place the UTM-tagged hub link in the
first comment. Carousels earn 3–5 times more engagement than standard posts.

**Spoke 3: X/Twitter thread**
4–8 tweets following the argument-plus-mystery architecture: Tweet 1 is the most
genuinely surprising or arguable claim in the thread; Tweets 2–5 develop creative
reasoning; Tweet 6 introduces the unexpected real-world connection to the relational
science research (where secular research independently arrives at territory the
work's foundational argument already mapped);
Tweet 7 is a quote graphic or screenplay page image; Tweet 8 is the CTA with hub link.
External links in Tweet 8 only — platform algorithms suppress reach when links appear
early. Thread format generates 3 times more engagement than single tweets.

**Spoke 4: Instagram carousel**
8–12 slides at 1080×1350 pixels (portrait). Slide 1 is the hook; Slides 2–7 tell a
visual story building toward maximum tension without resolution; final slide is full-
frame CTA. Instagram may re-show a carousel starting from Slides 2–4 — design each
of the first four slides with dual function: as a body slide within the narrative arc,
and as a potential re-entry hook for a viewer encountering it mid-carousel. Screenshot
legibility test: every slide must be readable at phone-screen dimensions without zooming.
Carousels earn 10% average engagement rate versus 7% for single images.

**Spoke 5: Email newsletter**
400–600 words, "Writer's Room" model. Opens with a personal creative anecdote about
producing a specific scene (author-written, not AI-generated). Includes an embedded
audiogram: 5–15 second ElevenLabs clip of the character delivering the key dialogue
line from the extraction point, formatted as a static waveform visualization. Video
and audio in email increases click-through rates by up to 300 percent — the audiogram
is the spoke's primary conversion mechanism. Subject line formats that outperform
generic announcements: personal admission, specific detail whose significance is
unexplained, before-and-after without the resolution.

### Phase 12 Quality Gate

All five spoke design documents complete with all six sections each: extraction point
assignment with curiosity cascade logic; content job assignment (Trust Accumulation,
Social Currency Distribution, Community Deepening, or Conversion Invitation); platform
mechanics specification; content structure outline; tone and Hub Fidelity specification;
UTM and measurement specification. No two spokes assigned the same primary content job.
Curiosity cascade compliance check complete. Hub Fidelity standard applied to every spoke.

---

## PHASE 13: SPOKE DRAFTS

### Production Principles Across All Five Spokes

The Hub Fidelity standard is enforced at the line level. Every piece of copy reviewed
before publication must be read against the hub film's actual content: does this copy
accurately represent what the hub contains, or has it drifted toward a more dramatic,
simpler, or more emotionally resolved version than the film actually tells?

The earned emotion test has six dimensions: does the emotion deepen with more context
(earned) or collapse with it (manufactured)? Does it grow more powerful on revisit or
become annoying? Does it produce "I need to see this film" or "that was misleading"?
Does the full film exceed what the spoke promises? Is the sharing motive "this moved
me" or "can you believe this"? Does the spoke's emotional register match the film's?

The curiosity gap placement is verified against the Phase 12 design documents. The
60-to-40 rule must be operative in the final produced asset, not just in the design
document's intention. Read or watch every finalized spoke as an audience member who
has never seen the hub and ask: do I have a genuine information gap?

### Diagnostic Framework for Underperforming Spokes

The CTR-AVD-AVP diagnostic hierarchy governs revision logic:

- Low CTR = problem is the hook (first three seconds not producing scroll-stop)
- Strong CTR but low AVD/AVP = problem is the body (over-delivering early)
- Strong CTR and AVD/AVP but low conversion = problem is the CTA or curiosity gap
  (gap partially closed by the spoke itself, making the hub feel optional)

These are three different problems with three different solutions. Treating them
interchangeably produces revisions that fix the wrong thing.

### Batch Copy Generation for Iterative Variants

For the sustained phase of the campaign (weeks 2–12), upload the complete Phase 9
screenplay to Grok (2 million token context window, real-time X data access; as of
September 2026 — verify before relying on it) and run
a single batch prompt session generating: 15 TikTok hook variants under 10 words each;
5 LinkedIn opening lines under 140 characters; 3 X/Twitter thread structures around
different thematic angles; 2 newsletter story angles not yet used; caption concepts for
the next Instagram carousel iteration. The screenplay's full narrative context means
Grok can identify tone-consistent variations that might not surface when working from
a single extracted scene.

### The Multilingual Multiplier

ElevenLabs' AI dubbing capability covers 29+ languages with speaker detection and
voice preservation (as of September 2026 — verify before relying on it). A finalized Spoke 1 video can be dubbed into Spanish, Portuguese,
French, Korean, and Arabic, each producing a new spoke targeting a new audience segment.
Activate during the sustained phase, after English-language spokes have established
performance baselines. Prioritize Spoke 1 for multilingual production first — it is
the widest-reach spoke and benefits most from language-native algorithm distribution.

### Phase 13 Quality Standards

**The Cascade Integrity Test** — Read or watch all five spokes in sequence, as an
audience member who has encountered all five without seeing the hub. Does the cumulative
effect produce a genuine desire to watch the complete hub film, or does it produce the
feeling that enough context has been given that the hub is optional? If the cumulative
spoke experience makes the hub feel optional, the cascade has over-revealed.

**The Platform-Native Test** — Evaluate each spoke against the primary audience of
its platform as if encountered in the feed of that platform, not in the context of the
campaign. Would a TikTok user who has never heard of this project stop scrolling?

**The Hub Fidelity Final Check** — After all five spokes are finalized but before any
is deployed, watch the hub film one final time, then read and view all five spokes in
sequence. Does each spoke accurately represent the film you just watched?

---

## YOUR GOVERNING POSTULATES

The postulates that govern this pipeline are the ones the author stated
before Phase 1 — see *Before Phase 1 — State Your Governing Postulates* in
`pipeline-thesis-development`, which also carries a worked example. The
rules this skill applies under the Third Postulate are the method's
**limits on means**: they stand on their own, whatever words the author's
own Third Postulate uses, and that postulate may tighten them but never
loosen them.

The limits on means have a specific application to the hub-and-spoke architecture.
A spoke that makes the hub appear to be something it is not — more dramatic, more
resolved, more unambiguous than the film actually is — violates the limits on means
regardless of how well it performs. The Hub Fidelity standard is the operational
enforcement of this rule. Every spoke must treat the audience member as a person
to be genuinely served rather than as a conversion event to be triggered. The curiosity
gap is legitimate when it reflects genuine content the hub contains. Manufactured urgency,
outrage amplification, false social proof, and misrepresented content are prohibited.

---

## COMPLETE PIPELINE CONTEXT

These four phases sit within the fourteen-phase Content Engineering Pipeline:

Phase 1 (Thesis) → Phase 2 (Terrain) → Phase 3 (Investigation) →
Phase 4 (Assembly) → Phase 5 (Revision) → Phase 6 (Novel Architecture) →
Phase 7 (Novel Draft) → Phase 8 (Screenplay Architecture) →
Phase 9 (Screenplay Draft) → **Phase 10 (Hub Architecture)** →
**Phase 11 (Hub Draft)** → **Phase 12 (Spoke Architecture)** →
**Phase 13 (Spoke Drafts)** → Phase 14 (Distribution)
