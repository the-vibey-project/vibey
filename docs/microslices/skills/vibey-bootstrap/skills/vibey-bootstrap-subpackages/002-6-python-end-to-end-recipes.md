---
id: skill-6-python-end-to-end-recipes-10f02ecb06
purpose: 6 python end to end recipes
source: src/vibey_tools/skills/plugins/vibey-bootstrap/skills/vibey-bootstrap-subpackages/SKILL.md
requires: ["skill-5-python-v2-tier-2-tier-3-subpackages-opt-in-62e6334ff0"]
links: ["skill-7-python-v4-0-0-runtime-modules-opt-in-820fde5df1"]
---

## 6. Python: end-to-end recipes

These mirror the runnable skeletons in `examples/` — the canonical, tested source. Each
runs offline with `USE_MOCK_BOOTSTRAP=true ... --dry-run`. Start at `examples/README.md`
for the full numbered reading order (`01_quickstart.py` … `46_scaffold_cli.py`; v3:
`39_v3_transports.py`, `44_db_outbox_email.py`, `45_http_client.py`).

### 6.1 Azure Function (`examples/e2e_azure_function.py`)

Lazy idempotent startup, per-request correlation, a fully traced handler, audit lines:

```python
import logging, uuid
from vibey_bootstrap.alerts import install_global_exception_hooks, register_dispatcher
from vibey_bootstrap.audit import build_audit_extra
from vibey_bootstrap.bootstrap import ensure_bootstrap
from vibey_bootstrap.counters import bump_counter
from vibey_bootstrap.logging import configure_logging, correlation_scope
from vibey_bootstrap.tracing import traced

logger = logging.getLogger(__name__)
_started = False

def _startup() -> None:
    global _started
    if _started:
        return
    configure_logging()
    install_global_exception_hooks()
    ensure_bootstrap()
    register_dispatcher(my_email_sender, recipients=["dev-alerts@example.com"])
    _started = True

@traced(operation="example.handle_request", alert_on_error="error")
def handle_request(payload: dict) -> dict:
    bump_counter("example.requests.processed")
    return {"ok": True}

def http_handler(request_id: str | None, body: dict) -> dict:
    _startup()
    cid = request_id or uuid.uuid4().hex[:12]
    with correlation_scope(cid, request_id=cid):
        logger.info("REPORT_AUDIT", extra=build_audit_extra("http_request", method="POST"))
        return handle_request(body)

# In function_app.py:
# @app.route(route="hello", auth_level=func.AuthLevel.FUNCTION)
# def hello(req): return func.HttpResponse(json.dumps(http_handler(req.headers.get("X-Request-Id"), req.get_json())))
```
> Note: stdlib `LogRecord` reserves the key `name` — use a different `extra` key
> (e.g. `payload_name`) when forwarding caller values.

### 6.2 FastAPI pipeline (`examples/e2e_fastapi_pipeline.py`)

Bootstrap + alerts + middleware + webhook + health + API-key admin + `/api/metrics`:

```python
from fastapi import Depends, FastAPI, Header
from vibey_bootstrap.alerts import install_global_exception_hooks, register_dispatcher
from vibey_bootstrap.auth import WebhookDedup, install_graph_webhook_route, verify_api_key_header
from vibey_bootstrap.bootstrap import ensure_bootstrap
from vibey_bootstrap.fastapi_middleware import install_middleware
from vibey_bootstrap.health import check_app_config_health, check_app_insights_health
from vibey_bootstrap.logging import configure_logging
from vibey_bootstrap.metrics import build_metrics_snapshot
from vibey_bootstrap.ratelimit import admin_bucket, fastapi_rate_limit, webhook_bucket

configure_logging(); install_global_exception_hooks(); ensure_bootstrap()
register_dispatcher(my_email_sender, recipients=["dev-alerts@example.com"])

app = FastAPI()
install_middleware(app, probe_paths=("/health/live", "/health/ready"))

install_graph_webhook_route(app, "/api/webhooks/email",
    background_handler=on_message,
    rate_limit_bucket=webhook_bucket(name="email_webhook"),
    dedup=WebhookDedup(ttl_seconds=600))

@app.get("/health/ready")
def ready() -> dict:
    return {"status": "ok",
            "app_config": check_app_config_health(),
            "app_insights": check_app_insights_health()}

admin_bkt = admin_bucket(name="admin_actions")
@app.post("/api/admin/reload", dependencies=[Depends(fastapi_rate_limit(admin_bkt))])
async def admin_reload(x_api_key: str = Header(default=None)) -> dict:
    await verify_api_key_header(x_api_key)
    return {"reloaded": True}

@app.get("/api/metrics")
def metrics() -> dict:
    return build_metrics_snapshot()
```

### 6.3 AKS Service Bus worker (`examples/e2e_aks_sb_worker.py`)

Consumer loop, heartbeat + watchdog, lock-per-message, SIGTERM-clean shutdown. v3 adds
`install_sigterm_handler`, `build_info`, `pod_context_extra`, and optional
`leader_election` for singleton schedulers:

```python
import threading
from vibey_bootstrap.aks import build_info, install_sigterm_handler, pod_context_extra
from vibey_bootstrap.bootstrap import ensure_bootstrap
from vibey_bootstrap.heartbeat import record_consumer_iteration, start_background_monitors
from vibey_bootstrap.identity import build_credential
from vibey_bootstrap.logging import configure_logging
from vibey_bootstrap.sb_lock import lock_for_process
from vibey_bootstrap.servicebus import handle_message
from vibey_bootstrap.validation import queue_message_schema

def main_loop(receiver, processor, stop_event):
    schema = queue_message_schema(required_fields=("correlation_id",),
                                  path_field="blob_path", path_required_prefix="reports/")
    while not stop_event.is_set():
        record_consumer_iteration()
        msg = receiver.receive()
        if msg is None:
            if stop_event.wait(0.1): break
            continue
        with lock_for_process(receiver, msg, max_lock_renewal_seconds=3600):
            handle_message(receiver, msg, processor, schema=schema,
                           correlation_field="correlation_id", source="consumer", counter_namespace="sb")

def main_pod():
    configure_logging(); ensure_bootstrap()
    logger.info("pod starting", extra={**pod_context_extra(), **build_info()})
    credential = build_credential()   # WorkloadIdentity in-cluster
    stop_event = threading.Event()
    install_sigterm_handler(stop_event)   # v3 — replaces manual signal.signal
    monitors = start_background_monitors(stop_event)
    try:
        main_loop(real_receiver, real_processor, stop_event)
    finally:
        stop_event.set()
        for t in monitors: t.join(timeout=5)
```
