---
id: skill-7-guard-selection-and-path-restrictions-588016dc49
purpose: 7 guard selection and path restrictions
source: src/vibey_tools/skills/plugins/tor-and-onion-networks/skills/tor-network-consensus-guards-and-paths/SKILL.md
requires: ["skill-6-the-network-itself-relays-authorities-consensus-weights-444e9d6cf9"]
links: ["skill-where-to-go-next-d4fb69bc1a"]
---

## §7. Guard selection and path restrictions

### §7.1 Why guards exist

The 2013 paper *Users Get Routed* (Johnson et al., CCS 2013) quantified what everyone feared:
if clients rotate first hops randomly, an adversary running a modest fraction of relays
*eventually* becomes the first hop and can run confirmation attacks. The fix — pin a small set
of first hops for **months** — turned a probabilistic certainty into a probabilistic rarity.

Modern rules (proposal 271 and successors): a **sampled guard set**, filtered for
reachability, of which the client uses 2–3 **primary guards**, rotating only on failure or
expiry.

> **⚠️ GOTCHA:** "Get a new identity often" is **not** the same as changing guards, and Tor
> Browser's New Identity keeps your guards *deliberately*. Advice that tells users to churn
> entry nodes for safety inverts the actual security argument — churn is what guards exist to
> prevent.

### §7.2 Path selection restrictions

Circuits are built subject to constraints that any builder must replicate:

- relays in one circuit must not share a **family** or (by default) a **/16**;
- exit policies must permit the destination port;
- consensus weights bias selection toward capacity (and `Guard`/`Exit` fractional weights keep
  exit-scarce bandwidth available for exit use);
- country restrictions only via explicit torrc (`ExitNodes`, `ExcludeNodes`, `GeoIP...`) — and
  these are advisory for privacy, not robust safety properties, since the exit or a router
  downstream sees your traffic anyway.

### §7.3 Happy families (proposal 321; shipped in C tor 0.4.9, 2026)

`MyFamily` mutual cross-listing was error-prone and bloated descriptors (O(family²)
fingerprints). 0.4.9 adds a shared **family key**: relays sign a certificate proving family
membership, collapsing family proof to a single identifier. Tor Project estimates eventual
**~80% microdescriptor size reduction**.

> **⚠️ GOTCHA for relay operators:** until client adoption catches up, you must maintain
> `MyFamily` **in parallel** with the new family key. Dropping `MyFamily` early makes your
> relays look unrelated to older clients, which is exactly the correlation risk families exist
> to prevent. See the [family-ids
> documentation](https://community.torproject.org/relay/setup/post-install/family-ids/).

---
