---
id: skill-13-4c-developing-against-a-test-network-chutney-51d284581b
purpose: 13 4c developing against a test network chutney
source: src/vibey_tools/skills/plugins/tor-and-onion-networks/skills/tor-building-on-tor-software-patterns/SKILL.md
requires: ["skill-13-4b-arti-as-a-library-and-daemon-9f9196c0d3"]
links: ["skill-13-6-building-your-own-private-network-3d617c4fc3"]
---

## §13.4c Developing against a test network: chutney

**Never integration-test against the production network.** Chutney runs a private mini-Tor on
localhost:

```bash
git clone https://gitlab.torproject.org/tpo/core/chutney.git
cd chutney
./chutney configure networks/basic
./chutney start    networks/basic
./chutney verify   networks/basic
./chutney status   networks/basic   # shows per-node SOCKS/Control ports to point tests at
```

---
