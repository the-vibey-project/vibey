---
id: skill-phase-10-hub-architecture-4ca884051a
purpose: phase 10 hub architecture
source: src/vibey_tools/skills/plugins/content-engineering-pipeline/skills/pipeline-ai-film-production/SKILL.md
requires: ["skill-overview-what-these-four-phases-accomplish-49c8e87060"]
links: ["skill-phase-11-hub-draft-f32ce24081"]
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
