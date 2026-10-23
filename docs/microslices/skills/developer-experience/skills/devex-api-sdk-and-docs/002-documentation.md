---
id: skill-documentation-64c297e083
purpose: documentation
source: src/vibey_tools/skills/plugins/developer-experience/skills/devex-api-sdk-and-docs/SKILL.md
requires: ["skill-api-and-sdk-design-cf8d7a15ef"]
links: []
---

## Documentation

Split docs by the reader's need, lead with something that runs, and keep examples tested.

| Type | Reader's question | Rule |
| --- | --- | --- |
| Tutorial | "Teach me" | One guided path to a working result in minutes; no choices |
| How-to guide | "Help me do X" | Steps for one goal; assumes basic knowledge |
| Reference | "What exactly is X?" | Complete, accurate, generated from code where possible |
| Explanation | "Why is it this way?" | Background and trade-offs; no steps |

This is the Diátaxis model. I read it only through secondary sources (the diataxis.fr site could not be fetched), and its value rests on practitioner adoption rather than controlled studies.

- **README first screen:** what it is, one install command, one runnable example, where to go next.
- **Executable docs:** run code samples in CI (doctests, or snippet tests) so examples never rot.
- **Style:** second person, active voice, present tense, one idea per sentence, descriptive link text (Google's developer documentation style guide is the usual reference).
- **Search and navigation:** every page answers one question, has a stable URL and links to the next step.
- **Versioning:** docs match the released version, with a clear switcher.
- **Feedback:** a visible "was this useful" control and an edit link that goes straight to a pull request.
- **Copy-paste friendly:** commands without prompt characters, and sample output shown separately.
