---
id: skill-5-python-v2-tier-2-tier-3-subpackages-opt-in-62e6334ff0
purpose: 5 python v2 tier 2 tier 3 subpackages opt in
source: src/vibey_tools/skills/plugins/vibey-bootstrap/skills/vibey-bootstrap-subpackages/SKILL.md
requires: []
links: ["skill-6-python-end-to-end-recipes-10f02ecb06"]
---

## 5. Python: v2 Tier 2 / Tier 3 subpackages (opt-in)

Concise reference; each is an independent import path. See `examples/` for runnable
demos (the numbers below reference numbered example files).

### `alerts` — tiered dispatcher
```python
from vibey_bootstrap.alerts import (
    register_dispatcher, alert_dev_team, AlertSeverity, install_global_exception_hooks,
)
register_dispatcher(my_email_sender, recipients=["dev-alerts@example.com"])
install_global_exception_hooks()    # uncaught sync/async exceptions auto-alert
alert_dev_team(AlertSeverity.ERROR, subject="x failed", context={...}, dedup_key="x")
```
`register_dispatcher(sender, recipients=None)` wires a sender
(`(recipients, subject, html_body) -> None`); `alert_dev_team(severity, subject,
context=None, dedup_key=None)` fires one. `AlertSeverity` = `WARN | ERROR | CRITICAL`:
**WARN is log-only**, **ERROR** is logged + queued to the digest and may escalate to
CRITICAL, **CRITICAL** sends an email immediately (subject to the kill switch +
rate-limit). `@traced(alert_on_error=...)` and most subpackages emit through this.
Tunables (env): `DEV_ALERTS_ENABLED` (kill switch, default on), `DEV_ALERT_RECIPIENTS`,
`ALERT_DEDUP_WINDOW_SECONDS` (600), `ALERT_MAX_PER_HOUR` (30), `ALERT_ESCALATE_AFTER`
(5), `ALERT_ESCALATE_WINDOW_SECONDS` (900), `ALERT_CRITICAL_SUBJECT_PREFIX`.

### `fastapi_middleware` — request timing + 5xx alerts
```python
from vibey_bootstrap.fastapi_middleware import install_middleware
install_middleware(app, probe_paths=("/health/live","/health/ready"),
                   alert_subject_prefix="[svc] ", fire_alerts=True)
```
Probe paths are **silent**. Non-probes log INFO (`<400`) / WARNING (`>=400`). A `5xx`
fires an ERROR alert (`http_5xx:{path}:{status}`); an uncaught exception fires
`http_crash:{path}:{type}` then re-raises. No headers added; correlation lives in
context vars, not HTTP headers.

### `health` — readiness probes
```python
from vibey_bootstrap.health import (
    check_app_config_health, check_app_insights_health, check_app_insights_logging,
)
```
Each returns `{"status": "ok" | "not_configured" | "error", ...}` (adds `"mock": True`
under `USE_MOCK_BOOTSTRAP`). `check_app_config_health` does a live App Config load;
the App Insights checks are fast readiness checks.

### `auth` — webhook + API-key + HMAC (needs `fastapi` for route helper)
```python
from vibey_bootstrap.auth import (
    install_graph_webhook_route, WebhookDedup, verify_api_key_header,
    verify_webhook_client_state, validation_token_handshake,
    verify_hmac_signature,   # v3 — GitHub/Sumo-style sha256=… bodies
)
install_graph_webhook_route(app, "/api/webhooks/email",
    background_handler=on_message, rate_limit_bucket=webhook_bucket(),
    dedup=WebhookDedup(ttl_seconds=600))
```
HTTP contract is documented in the `vibey-bootstrap-typescript` skill (Part 7).
`verify_api_key_header(x_api_key, *, env_var="API_KEY", fail_open_when_unset=True)` is
an async FastAPI dependency raising `HTTPException(401)` on mismatch.
`verify_hmac_signature(secret, raw_body, header_value)` is constant-time HMAC-SHA256
for generic webhook signature headers.

### `ratelimit` — token bucket + multi-unit limiter
```python
from vibey_bootstrap.ratelimit import (
    TokenBucket, MultiUnitLimiter, fastapi_rate_limit, webhook_bucket, admin_bucket,
)
bucket = TokenBucket(budget=240, refill_per_second=4.0, name="webhook")
limiter = MultiUnitLimiter()   # v3 — per-tenant / per-IP composite budgets
@app.post("/x", dependencies=[Depends(fastapi_rate_limit(bucket))])
async def x(): ...
```
```
`consume(n=1.0) -> bool`; `snapshot()` for monitoring. Presets:
`webhook_bucket()` = 240 burst / 4 per s; `admin_bucket()` = 30 burst / 0.5 per s.
`fastapi_rate_limit` returns **429 with an empty body** (no budget leak).

### `retry` — tenacity wrappers (needs `tenacity`)
```python
from vibey_bootstrap.retry import build_retry, retry_azure_transient, retry_ai_transient

@retry_azure_transient(operation="blob.download")   # 3 attempts, 2–10s, NetworkError|RateLimitError
def download(): ...

@retry_ai_transient(operation="openai.chat")        # 7 attempts, 2–120s, RateLimitError
def chat(): ...
```

### `ingress` — 4-gate attachment classifier
```python
from vibey_bootstrap.ingress import AttachmentClassifier, ClassifiedKind, enforce_zip_safety_limits

result = AttachmentClassifier().classify(           # gates: extension → MIME → size → magic-byte
    filename=name, content_type=mime, size_bytes=len(data), content=data,
)
if result.allowed:
    handle(result.kind)        # "pdf" | "zip"
```
`classify(...)` is **keyword-only** and returns
`ClassificationResult(allowed, kind, reject_reason, extension_mismatch)`.
`ClassifiedKind` is a **string literal** — `"pdf" | "zip" | "reject"` (the
classifier's `allowed_kinds` defaults to `("pdf", "zip")`). Zip-bomb defense:
`enforce_zip_safety_limits(data)` (defaults 500 MB uncompressed / 1000 entries via
`MAX_ZIP_UNCOMPRESSED_BYTES` and `MAX_ZIP_ENTRIES`).

### `notify` — two-tier notifications
```python
from vibey_bootstrap.notify import (
    build_failure_alert_body, build_unprocessable_notification,
    build_validation_notice_body, should_notify_sender, UnprocessableReason,
)
# Builders are keyword-only:
ops_html = build_failure_alert_body(
    attachment_name=name, correlation_id=cid, sender=addr,
    error_summary=str(exc)[:500], audience="ops",
)
if should_notify_sender(addr):    # per-sender throttle (max_per_hour=3, window_seconds=3600)
    subject, html, text, reason = build_unprocessable_notification(
        failure_reason=UnprocessableReason.VALIDATION_FAILURE,
        sender=addr, attachment_summary=[], correlation_id=cid,
    )
```
Ops get full forensics (`build_failure_alert_body`); senders get a sanitized message
(`build_unprocessable_notification`, which returns a `(subject, html, text, reason)`
tuple). All builders take **keyword-only** args.

### `heartbeat` — pulse + consumer watchdog
```python
from vibey_bootstrap.heartbeat import (
    start_background_monitors, record_consumer_iteration, record_message_settled,
)
monitors = start_background_monitors(stop_event)   # heartbeat + watchdog daemons
```
Call `record_consumer_iteration()` each loop; the watchdog fires an ERROR alert after
silence (default 30 min). Env: `HEARTBEAT_INTERVAL_SECONDS`,
`WATCHDOG_INTERVAL_SECONDS`, `WATCHDOG_SB_SILENCE_SECONDS`.

### `config_refresh` — dynamic log flags (run on a schedule)
```python
from vibey_bootstrap.config_refresh import refresh_log_flags
refresh_log_flags(("DEBUG_LOGGING_ENABLED", "LOG_LEVEL"))   # re-reads App Config; reapplies logging
```

### `subscription` — resource renewal loop
```python
from vibey_bootstrap.subscription import ensure_resource, renewal_loop, SubscriptionGone
```
Idempotent find-or-create + a SIGTERM-responsive renewal thread (sleeps in ≤5 s
slices). Built for Graph webhook subscriptions but generic.

### `servicebus` — consumer + DLQ + async extensions (needs `azure-servicebus`)
```python
from vibey_bootstrap.servicebus import handle_message, run_dlq_digest, issue_resubmit_token
from vibey_bootstrap.servicebus.async_ext import (   # v3
    run_async_consumer, ReplayGuard, service_bus_transport_type,
)
handle_message(receiver, msg, processor, schema=schema,
               correlation_field="correlation_id", source="consumer", counter_namespace="sb")
```
`handle_message(receiver, msg, processor, *, schema=None, correlation_field="correlation_id",
extra_correlation_fields=(), source="consumer", counter_namespace="sb")` parses JSON →
validates → opens `correlation_scope` → calls your processor → classifies failures via
`is_unrecoverable` into **complete / abandon / dead-letter**, and returns
`(processed: bool, failed: bool)`. `processor` is a `MessageProcessor` Protocol
(`process(payload)` + `notify_failure(payload, error)`). The DLQ digest
(`run_dlq_digest`) sends HMAC-signed resubmit tokens —
`issue_resubmit_token(secret, *, ttl_seconds=86400)` /
`verify_resubmit_token(secret, token)`.

v3 async helpers: `run_async_consumer(client, queue_name, handler, stop_event=…)` for
asyncio receive loops; `ReplayGuard` for bounded idempotency; `service_bus_transport_type()`
reads `SERVICE_BUS_TRANSPORT_TYPE` (`amqp` or `websocket`).

### `sb_lock` — message-lock renewal (needs `azure-servicebus`)
```python
from vibey_bootstrap.sb_lock import lock_for_process, ManagedLock
with lock_for_process(receiver, msg, max_lock_renewal_seconds=3600):
    ...   # broker won't redeliver mid-process
```

### `openai` — AI usage tracker
```python
from vibey_bootstrap.openai import record_usage, acquire, usage_snapshot, check_thresholds_and_alert
record_usage("gpt-4o", prompt_tokens=1200, completion_tokens=300)
```
Sliding-window tokens + cost (built-in pricing for GPT-4o & Claude 3 families;
override via `register_pricing`). Soft TPM cap via `acquire`. Env:
`AI_TPM_LIMIT[_<DEPLOYMENT>]`, `AI_COST_ALERT_HOURLY_DOLLARS`,
`AI_COST_ALERT_DAILY_DOLLARS`, `AI_HIGH_USAGE_TOKENS_HOURLY`.

### `tokens` — HMAC-SHA256 action tokens
```python
from vibey_bootstrap.tokens import issue_action_token, verify_action_token, InvalidActionToken
tok = issue_action_token(SECRET, action="dlq_resubmit", ttl_seconds=86400, payload={"id": "m1"})
body = verify_action_token(SECRET, tok, expected_action="dlq_resubmit")   # raises InvalidActionToken
```
Token = `base64url(json_payload).base64url(hmac_sha256)`; payload carries `exp` (unix
seconds) + `act`. **This is the interop point for the TS port** (see the
`vibey-bootstrap-typescript` skill, Part 8).

### `scheduler` — NCRONTAB parser (needs `apscheduler`)
```python
from vibey_bootstrap.scheduler import parse_cron_trigger
trigger = parse_cron_trigger("0 */5 * * * *")   # 5- or 6-field NCRONTAB → APScheduler CronTrigger
```

### `metrics` — aggregate snapshot
```python
from vibey_bootstrap.metrics import build_metrics_snapshot
snap = build_metrics_snapshot()
# {"latency": {...}, "alert_counters": {...}, "ai_usage": {...},
#  "bootstrap_initialized": bool, "last_sb_settle_age_seconds": float|None}
```
Soft-imports contributors — sections for absent modules are simply omitted.

### `pdf_safety` — strip active content (needs `pypdf`)
```python
from vibey_bootstrap.pdf_safety import sanitize_pdf_for_passthrough
reader = sanitize_pdf_for_passthrough(reader)   # removes OpenAction/AA/JavaScript/URI; best-effort
```
