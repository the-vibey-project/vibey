---
id: skill-12-caller-id-spoofing-and-robocalls-85e85678f3
purpose: 12 caller id spoofing and robocalls
source: src/vibey_tools/skills/plugins/communication-technologies/skills/comms-telephony-pstn-ss7-voip-and-caller-id/SKILL.md
requires: ["skill-11-volte-and-vonr-9d55e4d667"]
links: []
---

## §12. ⚠️ Caller ID, Spoofing and Robocalls

**⚠️ Caller ID was never authenticated** — ⚠️ **the calling number is asserted by the
originating network and, with SIP trunking, is trivially set by the caller.**
**⚠️ NEIGHBOUR SPOOFING** — ⚠️ **forging a number matching the recipient's prefix — exploits
this, and it is why answer rates for unknown numbers collapsed.**
**⚠️ STIR/SHAKEN** is the response: ⚠️ **the originating carrier cryptographically signs the
calling number with an attestation level (A: we know the caller and their right to the
number; B: we know the customer but not the number; C: we just passed it on), and the
terminating carrier verifies** (see a cryptography reference on certificate chains).
> **⚠️ GOTCHA — STIR/SHAKEN authenticates the CARRIER'S ASSERTION, not the caller's
> honesty.** ⚠️ **An A-level attestation means a carrier vouched for the number, not that the
> call is legitimate.** **⚠️ It also only works on IP-connected legs, so calls transiting
> older segments lose the signature — which is exactly §1 → `comms-email-smtp-authentication-and-deliverability`'s weakest-participant problem.**

**⚠️ It has helped and not solved**: ⚠️ **enforcement, traceback and gateway-provider
obligations do more of the work than the cryptography does.**
**⚠️ Branded calling** and RCS-verified sender identity (§15 → `comms-sms-rcs-signal-protocol-and-messaging-apps`) are the commercial responses to
the trust collapse.

---

# PART III — MESSAGING
