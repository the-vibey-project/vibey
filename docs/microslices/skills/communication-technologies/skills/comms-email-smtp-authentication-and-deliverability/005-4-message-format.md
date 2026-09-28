---
id: skill-4-message-format-978595998d
purpose: 4 message format
source: src/vibey_tools/skills/plugins/communication-technologies/skills/comms-email-smtp-authentication-and-deliverability/SKILL.md
requires: ["skill-3-retrieval-protocols-6a55ccaa33"]
links: ["skill-5-spf-dkim-dmarc-d6bab0af3e"]
---

## §4. Message Format

**⚠️ RFC 5322** defines headers and body; ⚠️ **MIME extends it to attachments, multiple
character sets and multipart bodies — because the original format was US-ASCII text only.**
**⚠️ Multipart/alternative** carries plain text and HTML versions of the same message,
⚠️ **and HTML email is where tracking pixels, remote-image beacons and rendering
inconsistency all live.**
**⚠️ Base64 and quoted-printable** encode binary into the 7-bit-safe channel SMTP assumes —
⚠️ **which is why attachments inflate roughly a third in transit.**
**⚠️ Message-ID, In-Reply-To and References** are what make threading work, ⚠️ **and clients
that ignore them produce the broken threads everyone recognizes.**
**⚠️ Internationalized email (EAI/SMTPUTF8)** allows non-ASCII addresses, ⚠️ **and support
remains patchy — a real equity issue for non-Latin-script users.**

---
