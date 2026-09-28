---
id: skill-13-4-advertising-the-onion-from-your-clearnet-site-f40ed58b4e
purpose: 13 4 advertising the onion from your clearnet site
source: src/vibey_tools/skills/plugins/tor-and-onion-networks/skills/tor-building-on-tor-software-patterns/SKILL.md
requires: ["skill-13-3-long-lived-onion-services-torrc-e06d718545"]
links: ["skill-13-4a-non-socks-apps-torsocks-and-its-honest-limits-c98f31be5b"]
---

## §13.4 Advertising the onion from your clearnet site

```nginx
# nginx — Tor users get the ".onion available" pill (Tor Browser ≥ 9.5)
add_header Onion-Location http://<your56>.onion$request_uri;

# transparent variant: Tor-capable clients switch to onion silently
add_header Alt-Svc 'h2="<your56>.onion:443"; ma=86400';
```

Serve these over HTTPS from the clearnet origin only (**never** from the onion itself).

---
