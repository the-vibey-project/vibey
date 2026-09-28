---
id: skill-7-typescript-next-js-a-http-client-integration-2452dfb35c
purpose: 7 typescript next js a http client integration
source: src/vibey_tools/skills/plugins/vibey-bootstrap/skills/vibey-bootstrap-typescript/SKILL.md
requires: []
links: ["skill-8-typescript-next-js-b-porting-the-patterns-to-typescript-2ee86b186b"]
---

## 7. TypeScript/Next.js — A: HTTP client integration

This documents the **exact HTTP contract** a Python backend exposes when it wires up
`vibey_bootstrap.auth`, `health`, `metrics`, and `fastapi_middleware`, then gives typed
Next.js (App Router) client code to consume it.

> Conventions assumed below: backend base URL in `process.env.BACKEND_URL`; the API
> key in **server-only** `process.env.BACKEND_API_KEY` (never `NEXT_PUBLIC_*`).

### 7.1 API-key-protected endpoints

**Contract:** header `x-api-key` (the backend reads it via FastAPI `Header` and passes
it to `verify_api_key_header`, env `API_KEY`). On mismatch → **`401`** with
`{"detail": "Unauthorized"}`. If the backend env var is unset, the check is **fail-open
by default** (passes) unless the backend opted into strict mode.

Keep the key server-side. Use a Route Handler (or Server Action) as a proxy so the
browser never sees it:

```ts
// app/api/admin/reload/route.ts
import { NextResponse } from "next/server";

export async function POST() {
  const res = await fetch(`${process.env.BACKEND_URL}/api/admin/reload`, {
    method: "POST",
    headers: { "x-api-key": process.env.BACKEND_API_KEY! },
    cache: "no-store",
  });
  if (res.status === 401) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  if (res.status === 429) return NextResponse.json({ error: "rate_limited" }, { status: 429 });
  return NextResponse.json(await res.json(), { status: res.status });
}
```

```ts
// lib/backend.ts — a small typed wrapper, server-side only
export async function callBackend<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${process.env.BACKEND_URL}${path}`, {
    ...init,
    headers: { "x-api-key": process.env.BACKEND_API_KEY!, ...init.headers },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`backend ${path} -> ${res.status}`);
  return res.json() as Promise<T>;
}
```

### 7.2 Graph-style webhook

`install_graph_webhook_route` exposes one `POST` path with two modes:

| Request | Response |
|---|---|
| `POST {path}?validationToken=<t>` (subscription handshake) | `200` + **plaintext** body `<t>` (not JSON) |
| `POST {path}` body `{"value":[{ "clientState", "subscriptionId", "resourceData": { "id" } }]}` | `202` (accepted) |
| clientState missing/mismatch, or endpoint unconfigured | `401` (empty body) |
| rate-limited | `429` (empty body) |
| malformed JSON | `400` |

`clientState` is checked **constant-time** against `GRAPH_WEBHOOK_CLIENT_STATE`;
dedup is keyed on `(subscriptionId, resourceData.id)`. Payload types:

```ts
// lib/webhook-types.ts
export interface GraphNotification {
  clientState?: string;
  subscriptionId?: string;
  resourceData?: { id?: string };
}
export interface GraphNotificationBatch { value: GraphNotification[]; }
```

If you instead want a Next.js Route Handler to *receive* such webhooks (a parallel TS
implementation of the same contract):

```ts
// app/api/webhooks/email/route.ts
import { NextRequest, NextResponse } from "next/server";
import { timingSafeEqual } from "node:crypto";
import type { GraphNotificationBatch } from "@/lib/webhook-types";

function safeEqual(a?: string, b?: string): boolean {
  if (!a || !b) return false;
  const ab = Buffer.from(a), bb = Buffer.from(b);
  return ab.length === bb.length && timingSafeEqual(ab, bb);
}

export async function POST(req: NextRequest) {
  // 1. validation handshake — echo the token as plaintext
  const token = req.nextUrl.searchParams.get("validationToken");
  if (token) return new NextResponse(token, { status: 200, headers: { "content-type": "text/plain" } });

  // 2. live notification
  let batch: GraphNotificationBatch;
  try { batch = await req.json(); } catch { return new NextResponse(null, { status: 400 }); }

  const expected = process.env.GRAPH_WEBHOOK_CLIENT_STATE;
  for (const n of batch.value ?? []) {
    if (!safeEqual(n.clientState, expected)) return new NextResponse(null, { status: 401 });
    const messageId = n.resourceData?.id;
    if (messageId) queueBackgroundWork(messageId); // your dedup + dispatch
  }
  return new NextResponse(null, { status: 202 });
}
```

### 7.3 Health probes

`check_*` helpers each return `{"status": "ok" | "not_configured" | "error", ...}`
(no HTTP 5xx for an unconfigured optional dependency). A typical `/health/ready` body:

```ts
export interface Probe { status: "ok" | "not_configured" | "error"; message?: string; mock?: boolean; }
export interface ReadyResponse {
  status: "ok"; app_config: Probe; app_insights: Probe; app_insights_logging?: Probe;
}
```

```ts
// app/status/page.tsx — server component
export default async function StatusPage() {
  const res = await fetch(`${process.env.BACKEND_URL}/health/ready`, { cache: "no-store" });
  const ready = (await res.json()) as ReadyResponse;
  const healthy = res.ok && Object.values(ready).every(
    (v) => typeof v !== "object" || v.status !== "error");
  return <main>Backend: {healthy ? "✅ healthy" : "⚠️ degraded"}</main>;
}
```

### 7.4 `/api/metrics`

`build_metrics_snapshot()` JSON shape (sections are present only if the backend has
that module wired):

```ts
export interface MetricsSnapshot {
  latency: Record<string, { count: number; errors: number; slow: number;
                            p50: number; p95: number; p99: number; max: number; last_seen?: number }>;
  alert_counters: Record<string, number>;
  ai_usage?: { by_deployment: Record<string, unknown>;
               totals: { calls: number; total_tokens: number; cost_usd: number; rate_limit_events: number } };
  bootstrap_initialized?: boolean;
  last_sb_settle_age_seconds?: number | null;
}
```

### 7.5 Correlation IDs & rate limiting

- The Python middleware does **not** emit an `X-Correlation-ID` response header —
  correlation lives in server-side context vars. If you want end-to-end correlation,
  generate an id in Next.js, send it as a custom header, and have the backend read it
  into `correlation_scope(...)`.
- `429` responses carry **empty bodies** by design. Honor `Retry-After` if present and
  back off; don't parse the body for budget state.
