---
id: skill-2-threat-model-taxonomy-the-questions-that-decide-everything-418ce14054
purpose: 2 threat model taxonomy the questions that decide everything
source: src/vibey_tools/skills/plugins/private-chat-engines/skills/chat-orientation-threat-models-and-landscape/SKILL.md
requires: ["skill-1-the-three-architectural-families-fe4009a21b"]
links: ["skill-3-comparison-matrix-state-of-play-september-2026-a3e3c8bc93"]
---

## 2. Threat-model taxonomy (the questions that decide everything)

### 2.0 First: "encrypted" is four different claims

Before the taxonomy below is any use, be precise about *which layer* is encrypted. Marketing
routinely conflates these four, and they are not degrees of the same thing:

| Claim | What it protects | Who can read content |
|---|---|---|
| **Transport encryption (TLS)** | the wire between client and server | the provider reads everything; protects against eavesdroppers on the network path only |
| **Encryption at rest** | stored data on disks | the provider holds the keys and can read content; protects against stolen physical disks only |
| **End-to-end encryption (E2EE)** | content across the entire path | only the endpoints — the provider cannot read content, but sees metadata |
| **E2EE with verified keys** | content **plus** identity assurance | only the endpoints, *and* you have verified the other party's key is theirs rather than one the server substituted |

> **⚠️ THE PRACTICAL TEST**
> **Can the provider show you your old messages on a new device with only a password? If yes, it is
> not end-to-end encrypted — or the backup isn't.** One question, and it cuts through every
> marketing claim. Telegram cloud chats fail it (→ `chat-telegram` §1.1); WhatsApp fails it unless
> E2EE backup is switched on; iMessage passes only with Advanced Data Protection; Signal passes,
> and its 2025 opt-in Secure Backups are zero-knowledge so it still passes (→ `chat-signal` §1.9).

And E2EE — even with verified keys — does not protect **metadata** (item 2 below), **the
endpoints** (a compromised phone defeats it completely; this is what commercial spyware buys),
**backups** (the most common real-world content leak), **the other party** (screenshot, forward, or
simply be untrustworthy), or **key distribution** where the provider supplies the public keys.

### 2.1 The seven axes

Before comparing apps, be precise about *private from whom, of what, against which attack*:

1. **Content privacy** — can the server read messages? (E2EE answers this; Telegram's default
   does not. Apple's taxonomy calls E2EE-without-PQ "Level 1" and grades up to "Level 3" for
   PQ-secured establishment *and* ongoing rekeying — see [Apple's PQ3 announcement, Feb 2024](https://security.apple.com/blog/imessage-pq3).)
2. **Metadata privacy** — can the server build the social graph? (Sealed Sender, zero-knowledge
   groups, identifier-free designs, onion routing all attack this. Nothing in mass deployment
   fully solves it.)
3. **Endpoint privacy** — is the phone the weakness? (Signalgate, forensic extraction, screen
   capture, iCloud-style backups, push-notification subpoenas. Most real-world failures are here.)
4. **Traffic privacy** — can the *network* observer see you use it? (Censorship resistance:
   TLS proxies, domain fronting, pluggable transports, or just being too popular to block.)
5. **Harvest-now-decrypt-later** — will today's ciphertext be readable in the cryptographically
   relevant quantum future? (The 2024–2026 post-quantum race — Signal, iMessage, SimpleX are in
   production; Threema in partnership; most others not started.)
6. **Compelled-access privacy** — how much does the operator even *have* when a subpoena or
   security order lands? (Signal's canonical answer: two timestamps. Telegram's post-2024 answer:
   considerably more. Sweden and the EU are currently legislating precisely this axis.)
7. **Organisational security** — can a staffer invite the wrong person to a classified group?
   (They can. E2EE does not fix identity confusion or admin error — the "Signalgate" lesson of
   March 2025.)

A useful rule: **apps solve 1–2 well, fight over 3–5, and get regulated over 6–7.**

> **⚠️ THE LEGAL ASYMMETRY IS WHY METADATA IS THE DESIGN DRIVER, NOT A NICE-TO-HAVE**
> Metadata alone yields relationships and their strength, sleep and work patterns, location history,
> health and legal circumstances (from who you called), religious and political affiliation, and the
> change points in a life — structured, machine-analysable at scale, and readable without reading
> anything. **In many jurisdictions it also receives markedly weaker legal protection than content,
> obtainable on a lower standard.** The most revealing category is the least protected. For
> high-risk users you reduce metadata because of legal process, not because of technical attacks —
> and the only defence that never fails is **not having the data**, which is why axis 6 above is the
> one that decides procurement (→ `chat-builder-and-operator-playbooks` §3 for the budget table).

---
