---
id: skill-8-the-operations-checklist-matrix-flavoured-mostly-transferable-40fbd873bc
purpose: 8 the operations checklist matrix flavoured mostly transferable
source: src/vibey_tools/skills/plugins/private-chat-engines/skills/chat-builder-and-operator-playbooks/SKILL.md
requires: ["skill-7-pick-the-architecture-by-what-you-re-willing-to-be-responsible-for-6a0db3a1e9"]
links: ["skill-9-operating-communities-on-other-people-s-platforms-9db839c422"]
---

## 8. The operations checklist (Matrix-flavoured, mostly transferable)

1. **Identity first**: pick the `server_name` apex and delegate via `.well-known`; never migrate
   it later — design your domain story in the first hour.
2. **Key custody**: signing keys in an offline backup before first boot; documented rotation
   procedure; old keys kept publishable.
3. **Storage doctrine**: media retention lifetimes on day one; remote media cache caps;
   state-compression cron (Synapse); Postgres on SSD with autovacuum tuned for state churn.
4. **Capacity**: 2 vCPU/4 GB = personal; 8/32 + worker split = community; k8s + ESS = institution;
   TURN (coturn) and a LiveKit SFU for calls; measure sync latency, not message-send.
5. **AuthN/AuthZ**: MAS (Matrix 2.0 native OIDC) to your IdP; disable open registration or gate
   it behind invites; room defaults: restricted joins; federation allow-lists where lawful.
6. **Moderation stack**: Draupnir + policy lists + report room; admin runbook for illegal-content
   handling (who can redact/deactivate, evidence preservation, DSA/reporting obligations for EU).
7. **Backups & drills**: DB + media + MAS + keys; quarterly restore drills; E2EE key-recovery
   *user education* (4S recovery keys) — most "we lost everything" tickets are client-side.
8. **Observability**: Prometheus/Grafana on sync times, federation queues, room version drift,
   bridge error rates; paging on Postgres replication lag and disk, not on CPU.
9. **Network hygiene**: TLS everywhere incl. federation (8448), modern ciphers, HSTS; egress
   rules for media repo; abuse@ and postmaster@ actually monitored; uptime SLO you can afford.
10. **Legal hygiene**: register a data-protection contact; write the warrant/LEA request SOP
    before the first one arrives; decide logging TTLs (IPs!) deliberately and publish them.
