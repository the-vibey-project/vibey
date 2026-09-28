---
id: skill-8-typescript-next-js-b-porting-the-patterns-to-typescript-2ee86b186b
purpose: 8 typescript next js b porting the patterns to typescript
source: src/vibey_tools/skills/plugins/vibey-bootstrap/skills/vibey-bootstrap-typescript/SKILL.md
requires: ["skill-7-typescript-next-js-a-http-client-integration-2452dfb35c"]
links: ["skill-9-appendices-9b27bb150b"]
---

## 8. TypeScript/Next.js — B: porting the patterns to TypeScript

These are **equivalent reimplementations**, not bindings — drop them into a Next.js
app that has no Python backend. They mirror the Python semantics closely; the token
helper in 8.6 is deliberately **wire-compatible** with the Python side.

### 8.1 Structured JSON logging (mirrors `JsonLogFormatter`)

```ts
// lib/logger.ts
const SECRET_KEYS = new Set(["authorization","api_key","apikey","password","token",
  "secret","client_secret","connection_string"]);

function maskSecrets(o: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(o)) out[k] = SECRET_KEYS.has(k.toLowerCase()) && v ? "***" : v;
  return out;
}

export function log(level: "INFO"|"WARNING"|"ERROR"|"DEBUG",
                    logger: string, message: string, extra: Record<string, unknown> = {}) {
  const line = { timestamp: new Date().toISOString(), level, logger, message, ...maskSecrets(extra) };
  (level === "ERROR" ? console.error : console.log)(JSON.stringify(line));
}
```

### 8.2 Correlation context (mirrors `correlation_scope` via `AsyncLocalStorage`)

```ts
// lib/correlation.ts
import { AsyncLocalStorage } from "node:async_hooks";
import { randomUUID } from "node:crypto";

type Ctx = Record<string, string>;
const als = new AsyncLocalStorage<Ctx>();

export function correlationScope<T>(fn: () => T, fields: Ctx = {}): T {
  const ctx: Ctx = { correlation_id: fields.correlation_id ?? randomUUID().replace(/-/g, "").slice(0, 12), ...fields };
  return als.run(ctx, fn);
}
export const getCorrelationId = () => als.getStore()?.correlation_id;
export const getContext = () => als.getStore() ?? {};
```

### 8.3 Masking helpers (mirror `mask_*`)

```ts
export const maskApiKey = (s?: string) => (!s || s.length < 4 ? "***" : `***${s.slice(-4)}`);
export const maskBearer = (t?: string) => (t?.startsWith("Bearer") ? "Bearer ***" : "***");
export const maskEmail = (e?: string) => {
  if (!e || !e.includes("@")) return "***";
  const [local, domain] = e.split("@");
  return `***${local.slice(-2)}@${domain}`;
};
```

### 8.4 In-memory counters (mirror `bump_counter` / `counter_snapshot`)

```ts
const counters = new Map<string, number>();
export const bumpCounter = (name: string, n = 1) => counters.set(name, (counters.get(name) ?? 0) + n);
export const counterSnapshot = () => Object.fromEntries(counters);
```

### 8.5 Token bucket (mirrors `ratelimit.TokenBucket` + presets)

```ts
// lib/token-bucket.ts
export class TokenBucket {
  private tokens: number; private last = performance.now() / 1000;
  constructor(private budget: number, private refillPerSecond: number) { this.tokens = budget; }
  consume(n = 1): boolean {
    const now = performance.now() / 1000;
    this.tokens = Math.min(this.budget, this.tokens + (now - this.last) * this.refillPerSecond);
    this.last = now;
    if (this.tokens >= n) { this.tokens -= n; return true; }
    return false;
  }
}
export const webhookBucket = () => new TokenBucket(240, 4);   // 240 burst, 4/s
export const adminBucket   = () => new TokenBucket(30, 0.5);  // 30 burst, 0.5/s
```

> In-process buckets only protect a single Node instance. On Vercel/serverless or
> multi-replica deployments, back the limiter with Redis/Upstash for a shared budget.

### 8.6 HMAC-SHA256 action tokens — **interoperable with Python `tokens`**

Same wire format as `vibey_bootstrap.tokens` / the Service-Bus resubmit token:
`base64url(json).base64url(hmac_sha256)`, payload sorted-keys with `exp` (unix
seconds) and `act`. A token minted here verifies in Python and vice-versa — so a
Next.js admin UI can issue a `dlq_resubmit` token the Python consumer accepts.

```ts
// lib/action-token.ts
import { createHmac, timingSafeEqual } from "node:crypto";

const b64url = (b: Buffer) => b.toString("base64url");
// Python uses json.dumps(sort_keys=True, separators=(",",":")) — match it exactly:
function canonicalJson(obj: Record<string, unknown>): string {
  const keys = Object.keys(obj).sort();
  return `{${keys.map((k) => `${JSON.stringify(k)}:${JSON.stringify(obj[k])}`).join(",")}}`;
}

export function issueActionToken(secret: string, action: string,
    ttlSeconds = 86400, payload: Record<string, unknown> = {}): string {
  const body = { ...payload, exp: Math.floor(Date.now() / 1000) + ttlSeconds, act: action };
  const payloadBytes = Buffer.from(canonicalJson(body), "utf-8");
  const sig = createHmac("sha256", secret).update(payloadBytes).digest();
  return `${b64url(payloadBytes)}.${b64url(sig)}`;
}

export function verifyActionToken(secret: string, token: string, expectedAction: string): Record<string, unknown> {
  const [p, s] = token.split(".");
  if (!p || !s) throw new Error("malformed token");
  const payloadBytes = Buffer.from(p, "base64url");
  const provided = Buffer.from(s, "base64url");
  const expected = createHmac("sha256", secret).update(payloadBytes).digest();
  if (provided.length !== expected.length || !timingSafeEqual(provided, expected)) throw new Error("signature mismatch");
  const body = JSON.parse(payloadBytes.toString("utf-8"));
  if (body.act !== expectedAction) throw new Error("wrong action");
  if (typeof body.exp !== "number" || body.exp < Math.floor(Date.now() / 1000)) throw new Error("expired");
  return body;
}
```

> **Interop caveats.** Byte-compatibility depends on the JSON serialization matching
> Python's `json.dumps(sort_keys=True, separators=(",",":"))`. The helper above
> reproduces sorted keys and compact separators, but keep payload values to JSON
> primitives (strings, ints, bools) — non-ASCII strings and floats can serialize
> differently across runtimes and will break the signature. Use the **same shared
> secret** on both sides (a Key Vault secret).

### 8.7 Constant-time compare (mirrors `compare_secrets`)

```ts
import { timingSafeEqual } from "node:crypto";
export function compareSecrets(a?: string, b?: string): boolean {
  if (!a || !b) return false;
  const ab = Buffer.from(a, "utf-8"), bb = Buffer.from(b, "utf-8");
  return ab.length === bb.length && timingSafeEqual(ab, bb);
}
```
