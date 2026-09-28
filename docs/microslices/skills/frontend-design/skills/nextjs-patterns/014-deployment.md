---
id: skill-deployment-d1209b2eda
purpose: deployment
source: src/vibey_tools/skills/plugins/frontend-design/skills/nextjs-patterns/SKILL.md
requires: ["skill-security-b1e2d1e835"]
links: ["skill-anti-patterns-e78c541806"]
---

## Deployment

### Vercel vs. Self-Hosting

| Factor                  | Vercel                                    | Self-hosted (Docker/K8s)                  |
|-------------------------|-------------------------------------------|-------------------------------------------|
| Setup                   | Zero-config                               | You own CI/CD, cache warming, health probes |
| ISR                     | Distributed automatically                 | Cache lives in `.next/cache`, not durable without custom cache handler |
| Image optimization      | Automatic                                 | Requires `sharp` installed                |
| Version skew protection | Built-in                                  | Manual                                    |
| Cost                    | Significant above ~10M requests/month     | Predictable                               |

### Self-Hosting Configuration

```dockerfile
# output: 'standalone' traces exact deps into a minimal Node server
# Copy public/ and .next/static separately
```

Critical self-hosting checklist:
- Disable reverse-proxy buffering for streaming: `proxy_buffering off`, `X-Accel-Buffering no`, HTTP/1.1
- `NEXT_PUBLIC_` vars are build-time — need rebuild or separate images per environment
- Set `NEXT_SERVER_ACTIONS_ENCRYPTION_KEY` for multi-instance consistency
- Separate liveness/readiness probes (DB failures → affect readiness, not liveness)

### Output Modes

- `output: 'standalone'` — minimal Node server (~200MB image vs 1GB+); required for clean Docker/K8s
- `output: 'export'` — fully static (replaces old `next export`)

---
