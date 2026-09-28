---
id: skill-9-encrypted-dns-936017aa21
purpose: 9 encrypted dns
source: src/vibey_tools/skills/plugins/dns-domains-and-naming-systems/skills/dns-attacks-dnssec-encrypted-dns-and-operations/SKILL.md
requires: ["skill-8-dnssec-25e814d0dc"]
links: ["skill-10-modern-extensions-43b4004523"]
---

## §9. ⚠️ Encrypted DNS

```
⚠️ THE PROBLEM  ⚠️ classic DNS is plaintext, so your resolver,
   your ISP and anyone on path sees every name you look up —
   ⚠️ a metadata trove (see a communications reference §24)
⚠️ THE OPTIONS
   ⚠️ DoT (DNS over TLS)  ⚠️ port 853 — ⚠️ distinguishable and
      therefore blockable, which network operators like
   ⚠️ ⚠️ DoH (DNS over HTTPS)  ⚠️ port 443, indistinguishable
      from web traffic — ⚠️ which is precisely why it is
      CONTROVERSIAL. ⚠️ It bypasses network-level filtering,
      including both censorship AND legitimate enterprise
      controls and parental filters
   ⚠️ DoQ over QUIC · ⚠️ ODoH (Oblivious DoH) separates WHO is
      asking from WHAT is asked, using a proxy
⚠️ ⚠️ THE HONEST CRITIQUE OF DoH: IT MOVES TRUST RATHER THAN
   ELIMINATING IT. ⚠️ You stop trusting your ISP and start
   trusting a large DNS provider — ⚠️ and browser-default DoH
   centralizes visibility into a handful of operators, which is
   a real concern regardless of their current behaviour
⚠️ ENCRYPTED CLIENT HELLO (ECH) closes the adjacent leak —
   ⚠️ because encrypting DNS while SNI still reveals the
   hostname in the TLS handshake accomplishes much less than
   people assume
```

---
