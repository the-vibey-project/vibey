---
id: skill-13-4b-arti-as-a-library-and-daemon-9f9196c0d3
purpose: 13 4b arti as a library and daemon
source: src/vibey_tools/skills/plugins/tor-and-onion-networks/skills/tor-building-on-tor-software-patterns/SKILL.md
requires: ["skill-13-4a-non-socks-apps-torsocks-and-its-honest-limits-c98f31be5b"]
links: ["skill-13-4c-developing-against-a-test-network-chutney-51d284581b"]
---

## §13.4b Arti as a library and daemon

Arti (Rust) is the future embedding path: no fork of an external process, memory safety, and —
since 1.8.0 (Dec 2025) — production-grade onion services with native vanguards.

```toml
# ~/.config/arti/arti.toml  (minimal client)
[proxy]
socks_listen = "127.0.0.1:9150"
dns_listen = "127.0.0.1:15354"
```

```rust
// embedding: arti-client = "0..." (API churned through 2.x — pin + read changelog)
use arti_client::{TorClient, TorClientConfig};

let tor = TorClient::create_bootstrapped(TorClientConfig::default()).await?;
let stream = tor.connect(("check.torproject.org", 443)).await?;
```

C-tor → Arti service migration: `arti hsc ctor-migrate` (2.x) ports hidden-service keys. Watch
the `arti hss` tooling and Arti RPC — both are the fast-moving surface in 2026. **onionmasq**
(from the Tor VPN project) gives you a userspace TUN interface over Arti: route whole
applications without them knowing.

---
