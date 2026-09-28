---
id: skill-overriding-ai-prose-defaults-e0871599e3
purpose: overriding ai prose defaults
source: src/vibey_tools/skills/plugins/writing-craft/skills/prose-mechanics/SKILL.md
requires: ["skill-how-ai-prose-fails-peer-reviewed-evidence-50f1140960"]
links: ["skill-voice-what-it-is-mechanically-5fbe565aaa"]
---

## Overriding AI prose defaults

### Specificity over abstraction

AI prose defaults to abstraction because abstraction has higher conditional probability over a wide range of contexts.

**Diagnostic**: ask of every sentence, "Who is doing what to whom?" Replace nominalizations with verbs. Replace abstract subjects with concrete agents.

**The Nabokov directive**: "Caress the detail, the divine detail." The writer is responsible not for the category (*tree*) but for the species (*linden*) and the particular tree.

### Vary sentence length deliberately

Count sentence lengths in a paragraph. If clustered around 15-20 words, force variation:
- Write one sentence under 8 words
- Write one sentence over 30 words
- Vary opening constructions: not always the subject

### Style-specific prompting

Different styles need different directives:

**For plain style**: "Write in declarative sentences. Use coordinating conjunctions, not subordinating ones. Use Anglo-Saxon vocabulary. Do not hedge."

**For periodic style**: "Construct one long sentence in which the main clause does not arrive until the end, with three subordinate qualifying clauses preceding it."

**For Hemingway**: "Omit what you know but the reader should feel. No adverbs. Concrete nouns only. Short declarative sentences joined by and."

**For KJV / biblical**: "Use polysyndeton (repeated 'and'). Use parallel clauses in synonymous or antithetical form. Use monosyllabic Anglo-Saxon vocabulary. Include at least one vocative apostrophe or behold marker."

**For Bacon / Senecan curt**: "Open with an asyndetic tricolon. State the main point first, then expand. Each sentence should be quotable in isolation. No hedging."

**For Augustan balance**: "Build each sentence on two matched members with a semicolon as fulcrum. Use Latinate diction but keep the grammar transparent."

**The most reliable prompt structure for stylistic precision**: named style target + representative example + explicit defaults to avoid + positive directive. A prompt that names a style without an example produces a stereotype. A prompt that gives an example without constraints produces drift.

### The few-shot example principle

"Write like Joan Didion" produces an LLM's stereotype of Didion. "Continue this Didion paragraph in her voice" produces something closer to her actual cadence. **Supply the example, not just the label.**

### Edit for the tells

When reviewing AI-assisted prose, scan specifically for:
- *delve, tapestry, navigate, comprehensive, nuanced, crucial, underscore, multifaceted, showcasing*
- Every em dash — is it earning its place?
- Every "ultimately," "in conclusion," "it is worth noting that," "it is important to consider"
- Every sentence that starts with "It is..." or "There is/are..."
- Every paragraph that follows the same intro → body → conclusion pattern

**The test**: if a paragraph contains no proper nouns, no numbers, no specific verbs of action, no sensory detail, and no first-person commitment, the paragraph is doing no informational work.
