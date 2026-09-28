---
id: skill-13-4a-non-socks-apps-torsocks-and-its-honest-limits-c98f31be5b
purpose: 13 4a non socks apps torsocks and its honest limits
source: src/vibey_tools/skills/plugins/tor-and-onion-networks/skills/tor-building-on-tor-software-patterns/SKILL.md
requires: ["skill-13-4-advertising-the-onion-from-your-clearnet-site-f40ed58b4e"]
links: ["skill-13-4b-arti-as-a-library-and-daemon-9f9196c0d3"]
---

## §13.4a Non-SOCKS apps: torsocks and its honest limits

```
torsocks curl https://check.torproject.org/api/ip
```

torsocks is `LD_PRELOAD` shimming: TCP only, breaks on apps using raw syscalls, no UDP, and it
*silently* does nothing for apps that bypass libc (statically linked Go/Rust binaries).

> **⚠️ GOTCHA — this is the dangerous one.** A statically linked binary under `torsocks`
> connects **directly**, with no error and no warning. Rule of thumb: **torsocks for
> convenience, never for high-stakes assurance.** For assurance, use app-native SOCKS or a
> fail-closed network sandbox (§13.5 → `tor-running-relays-bridges-and-hardware`, §4.3–4.4).
> `proxychains` shares the architecture *and* the caveats, with worse defaults.

---
