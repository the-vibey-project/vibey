---
id: skill-performance-metrics-b09b968337
purpose: performance metrics
source: src/vibey_tools/skills/plugins/network-engineering/skills/network-fundamentals/SKILL.md
requires: ["skill-cloud-networking-fundamentals-95561870b7"]
links: ["skill-troubleshooting-toolkit-755d8d90b7"]
---

## Performance metrics

- **Bandwidth**: maximum theoretical capacity — the pipe width. 1 Gbps = 1 billion bits/second.
- **Latency**: time for one packet to travel source → destination. Components: propagation delay (speed of light), transmission delay, processing delay, queuing delay. Typical: <1ms LAN, 40-80ms cross-country, 500-700ms geostationary satellite.
- **Throughput**: actual data rate achieved — always ≤ bandwidth.
- **Jitter**: variation in packet delay. Devastating for VoIP (acceptable: <30ms). High bandwidth with high latency means poor interactive responsiveness even if large transfers complete quickly.
