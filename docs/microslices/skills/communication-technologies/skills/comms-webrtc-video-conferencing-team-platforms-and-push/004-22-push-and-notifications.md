---
id: skill-22-push-and-notifications-5819ff9e11
purpose: 22 push and notifications
source: src/vibey_tools/skills/plugins/communication-technologies/skills/comms-webrtc-video-conferencing-team-platforms-and-push/SKILL.md
requires: ["skill-21-team-platforms-bca5806717"]
links: []
---

## §22. Push and Notifications

**⚠️ Mobile push exists because battery does not permit persistent connections per app** —
⚠️ **so one OS-level channel multiplexes for everything.**
**⚠️ APNs and FCM** are that channel, ⚠️ **which means Apple and Google see notification
metadata for essentially every app — ⚠️ and government requests for push notification
records have been documented, which is a §24 → `comms-encryption-metadata-interoperability-and-policy` problem hiding in an engineering decision.**
**⚠️ E2EE apps handle this** by sending a content-free wake-up push and fetching the
message, ⚠️ **so the notification service learns that a message arrived but not what it
says.**
**⚠️ Web push** uses VAPID and encrypted payloads.
**⚠️ The design problem** is notification fatigue — ⚠️ **and the honest observation is that
platforms optimizing for engagement have an incentive that runs directly against the user's
interest here.**

---

# PART V — CROSS-CUTTING
