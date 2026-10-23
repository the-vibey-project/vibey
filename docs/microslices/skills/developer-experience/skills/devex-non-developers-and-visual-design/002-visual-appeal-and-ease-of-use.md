---
id: skill-visual-appeal-and-ease-of-use-7b9f5f9d4d
purpose: visual appeal and ease of use
source: src/vibey_tools/skills/plugins/developer-experience/skills/devex-non-developers-and-visual-design/SKILL.md
requires: ["skill-non-developer-paths-the-quickest-route-to-working-code-through-a-ui-298497f89a"]
links: []
---

## Visual appeal and ease of use

**Do looks matter? Yes, with a caveat.** The aesthetic-usability effect (Kurosu and Kashimura, 1995; summarized on [Laws of UX](https://lawsofux.com/aesthetic-usability-effect/)) found that people rate attractive interfaces as easier to use. The caveat is that appeal can mask real problems: users forgive flaws and report fewer of them in testing, so a handsome interface needs behavioral testing, not only opinion surveys. Evidence grade B.

**Design-system hygiene** (from the loaded UI/UX reference, secondary):

- Use three tiers of tokens: primitive values, meaning-based aliases (such as "action primary"), and component tokens. Components should use only the second and third tiers, which is what makes dark mode and rebranding cheap.
- The W3C Design Tokens Community Group published its first stable specification (2025.10) in October 2025. It is a Community Group specification, not a W3C Recommendation, so say "the DTCG spec" rather than "the W3C standard".
- Measure the system by adoption (share of UI built from system components), not by how many components exist.

**Accessibility is both quality and law**

- Build to WCAG 2.2 AA. It is a superset of 2.1 AA, which most laws cite.
- The European Accessibility Act has been enforceable since 28 June 2025 for new products and services, and applies to firms outside the EU that sell to EU consumers.
- The reference quotes WebAIM's 2026 finding of contrast failures on 83.9% of the top million home pages. I did not open the WebAIM report, so treat this number as unverified here.
- Check contrast against WCAG 2 (that is what gets audited). APCA is an optional extra check, mainly for dark mode; it is not a legal standard.

**Material 3 Expressive and Liquid Glass.** Both are current platform looks. Expressive's research claims are Google's own and come to me through the press and a reference (see Android). Liquid Glass has drawn legibility criticism, and translucency lowers text contrast, so test with Reduce Transparency and Increase Contrast on. The practical rule is the same on both: adopt the platform look through standard components and spend custom effort on content, not chrome.

**A short checklist for any surface**

- One primary action per screen, and it looks like one.
- Plain-language labels first, technical terms in tooltips or detail views.
- Empty states that say what to do next.
- Loading, error and offline states designed, not defaulted.
- Light and dark themes both tested.
- Keyboard and screen-reader paths tested, not assumed.
