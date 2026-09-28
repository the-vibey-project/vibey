---
id: skill-32-quick-reference-fd540a58a0
purpose: 32 quick reference
source: src/vibey_tools/skills/plugins/communication-technologies/skills/comms-reference/SKILL.md
requires: ["skill-31-sources-bd1492832c"]
links: ["skill-33-method-83fec8af7e"]
---

## §32. Quick Reference

### 32.1 Picker
| Question | Where |
|---|---|
| Why does my mail go to spam? | ⚠️ **Authentication, then reputation and complaints** (§5 → `comms-email-smtp-authentication-and-deliverability`, §6 → `comms-email-smtp-authentication-and-deliverability`) |
| Someone is spoofing my domain | ⚠️ **DMARC with reporting. Read before enforcing** (§5 → `comms-email-smtp-authentication-and-deliverability`) |
| Is this messenger actually secure? | ⚠️ **Ask the new-device test** (§23 → `comms-encryption-metadata-interoperability-and-policy`) |
| Is SMS 2FA good enough? | ⚠️ **Better than nothing, worse than TOTP or a key** (§13 → `comms-sms-rcs-signal-protocol-and-messaging-apps`) |
| Why do spam calls look local? | ⚠️ **Neighbour spoofing. Caller ID isn't authenticated** (§12 → `comms-telephony-pstn-ss7-voip-and-caller-id`) |
| Why is my video call bad? | ⚠️ **Latency, jitter, loss — and echo means get a headset** (§10 → `comms-telephony-pstn-ss7-voip-and-caller-id`, §20 → `comms-webrtc-video-conferencing-team-platforms-and-push`) |
| Can my employer read my Slack? | ⚠️ **Yes. It's a product feature** (§21 → `comms-webrtc-video-conferencing-team-platforms-and-push`) |
| Is my group chat end-to-end encrypted? | ⚠️ **Check the platform, and check backups separately** (§23 → `comms-encryption-metadata-interoperability-and-policy`) |
| Does encryption hide who I talk to? | ⚠️ **No. Metadata survives** (§24 → `comms-encryption-metadata-interoperability-and-policy`) |
| Is iPhone-to-Android encrypted now? | ⚠️ **If both carriers support UP 3.0** (§28.1) |
| Are business RCS messages encrypted? | ⚠️ **Transport only, and by design** (§15 → `comms-sms-rcs-signal-protocol-and-messaging-apps`, §28.1) |
| Will my phone work in a power cut? | ⚠️ **Not on all-IP without battery backup** (§27 → `comms-encryption-metadata-interoperability-and-policy`) |

### 32.2 Choosing a channel
- [ ] ⚠️ **What must be confidential — content, or the fact of contact?** (§23 → `comms-encryption-metadata-interoperability-and-policy`, §24 → `comms-encryption-metadata-interoperability-and-policy`)
- [ ] ⚠️ **Who must be able to reach you? Reach vs security is the trade** (§1 → `comms-email-smtp-authentication-and-deliverability`)
- [ ] ⚠️ **Are backups covered, or is the archive the weak point?** (§23 → `comms-encryption-metadata-interoperability-and-policy`)
- [ ] Is the other party's endpoint trustworthy? (§23 → `comms-encryption-metadata-interoperability-and-policy`)
- [ ] ⚠️ **Does the org need search, retention or eDiscovery? Then not E2EE** (§21 → `comms-webrtc-video-conferencing-team-platforms-and-push`)
- [ ] Does it need to work with no internet or no app? (§13 → `comms-sms-rcs-signal-protocol-and-messaging-apps`)
- [ ] ⚠️ **Emergency and accessibility requirements met?** (§27 → `comms-encryption-metadata-interoperability-and-policy`)
- [ ] **If sending bulk email, additionally:**
- [ ] ⚠️ **SPF, DKIM and DMARC aligned; reports monitored** (§5 → `comms-email-smtp-authentication-and-deliverability`)
- [ ] ⚠️ **One-click unsubscribe, and complaint rate watched** (§6 → `comms-email-smtp-authentication-and-deliverability`)
- [ ] Transactional separated from marketing by subdomain (§6 → `comms-email-smtp-authentication-and-deliverability`)

---
