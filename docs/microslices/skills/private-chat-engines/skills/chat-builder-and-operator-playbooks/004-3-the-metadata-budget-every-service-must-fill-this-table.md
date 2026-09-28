---
id: skill-3-the-metadata-budget-every-service-must-fill-this-table-5dc70bdbf5
purpose: 3 the metadata budget every service must fill this table
source: src/vibey_tools/skills/plugins/private-chat-engines/skills/chat-builder-and-operator-playbooks/SKILL.md
requires: ["skill-2-5-the-server-you-have-to-write-anyway-fundamentals-stable-20c7089dc8"]
links: ["skill-4-abuse-trust-and-safety-under-e2ee-the-part-everyone-forgets-to-design-6d5499f734"]
---

## 3. The metadata budget — every service must fill this table

| Datum visible to your server by default | Signal's mitigation | If you can't mitigate it, write it down |
|---|---|---|
| Sender identity on each message | Sealed Sender + delivery tokens | at least encrypt sender outside routing fields |
| Social graph | zero-knowledge groups (zkgroup KVAC credentials), enclave contact discovery (CDSI/PathORAM) | delete-on-delivery policies; retention audits |
| Registration/contact discovery | SGX enclave + ORAM (and its documented enclave-compromise residual risk) | hashing is theatre against nation states; say so |
| Group membership | zkgroup | at least avoid server-readable role metadata |
| Backups | zero-knowledge, unlinked-from-account storage (2025 backups design) | encrypted client-side or *don't offer* backups |
| Push timing/token | content-free pushes; community paths around FCM/APN (Molly+UnifiedPush) | document that Apple/Google see wake-up metadata |
| IPs | call relays; Tor/proxy support | log rotation discipline in writing |
