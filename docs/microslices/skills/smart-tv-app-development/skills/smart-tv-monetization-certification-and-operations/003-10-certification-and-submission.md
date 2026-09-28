---
id: skill-10-certification-and-submission-ef44880496
purpose: 10 certification and submission
source: src/vibey_tools/skills/plugins/smart-tv-app-development/skills/smart-tv-monetization-certification-and-operations/SKILL.md
requires: ["skill-9-ctv-advertising-3d5d66ee1f"]
links: ["skill-11-testing-0fb434fb2d"]
---

## §10. Certification and Submission

### 10.1 What certification actually is

**[DURABLE] Every TV platform gates the store with a human-plus-automated review against
a published checklist, and it is stricter than mobile app review.** Rejections are common,
review cycles are measured in **days to weeks**, and a rejection late in a launch plan is
what pushes a Q2 launch to Q4.

**What gets tested, near-universally:**
- **Performance**: launch time, time to first video frame, memory usage, no crashes.
- **Navigation**: focus is never lost, Back always works and is predictable, no dead ends.
- **Playback**: correct trick play, resume, error handling, captions.
- **Deep linking**: content deep links resolve correctly from cold and warm start.
- **Billing**: platform IAP used correctly; no off-platform payment steering where
  prohibited.
- **Content policy**: ratings, parental controls, no prohibited content.
- **Accessibility**: captions honour system settings; screen-reader support where required.
- **Legal**: privacy policy, terms, correct attribution.
- **Branding**: correct use of platform logos and remote-button iconography.

**[PLATFORM] Roku's tooling is unusually explicit**, and worth knowing as the model:
- **Static Analysis** — detects certification issues in your code and **must pass** before
  publication.
- **App Behavior Analysis** — verifies performance and deep-linking criteria (note: it's
  intended for free and ad-based apps, and will report false failures on subscription apps).
- **BrightScript Profiler** — for performance and memory.
- Enrolment in the Roku developer program, developing, and publishing are **free**.
- Roku publishes seasonal certification updates — treat them as a **recurring calendar
  item**, not a one-time read. The Spring 2026 update added the Instant Resume requirement
  (§7.1 → `smart-tv-playback-drm-and-performance`) and made `roAppMemoryMonitor` usage a testing requirement.

**⚠️ Read the certification checklist before you design, not before you submit.** Half its
requirements are architectural (resume, deep linking, memory monitoring, focus behaviour)
and cannot be retrofitted cheaply.

---
