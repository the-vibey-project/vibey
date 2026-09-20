# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Composite notification service coordinating desktop alerts and signed webhooks."""

import asyncio
from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from vibey.infrastructure.notify.desktop import DesktopNotifier
from vibey.infrastructure.notify.events import NotificationEvent, NotificationKind
from vibey.infrastructure.notify.webhook import WebhookPublisher


class NotificationService:
    def __init__(
        self,
        *,
        desktop_notifier: DesktopNotifier | None = None,
        webhook_publisher: WebhookPublisher | None = None,
        webhook_configs: Sequence[dict[str, Any]] | None = None,
        enable_desktop: bool = True,
    ) -> None:
        self._desktop = desktop_notifier or DesktopNotifier()
        self._webhook = webhook_publisher or WebhookPublisher()
        self._webhook_configs = list(webhook_configs or [])
        self._enable_desktop = enable_desktop

    def for_project_config(self, config: Mapping[str, object] | None) -> "NotificationService":
        """Return the channel policy for one project's stored configuration.

        The composition root owns one service instance, while projects own
        their opt-in policy.  This keeps a multi-project worker from sending a
        project's events to another project's webhooks.
        """
        raw = config.get("notifications") if isinstance(config, Mapping) else None
        if not isinstance(raw, Mapping) or raw.get("enabled") is not True:
            return NotificationService(enable_desktop=False)

        raw_webhooks = raw.get("webhooks", ())
        webhooks: list[dict[str, Any]] = []
        if isinstance(raw_webhooks, Sequence) and not isinstance(raw_webhooks, str | bytes):
            for raw_webhook in raw_webhooks:
                if not isinstance(raw_webhook, Mapping):
                    continue
                url = raw_webhook.get("url")
                if not isinstance(url, str) or not url.strip():
                    continue
                secret = raw_webhook.get("secret")
                webhooks.append(
                    {
                        "url": url.strip(),
                        "secret": secret if isinstance(secret, str) else None,
                    }
                )
        return NotificationService(
            desktop_notifier=self._desktop,
            webhook_publisher=self._webhook,
            webhook_configs=webhooks,
            enable_desktop=raw.get("desktop", True) is True,
        )

    async def notify(
        self,
        *,
        project_id: UUID,
        kind: str,
        title: str,
        message: str,
        payload: Mapping[str, object] | None = None,
        config: Mapping[str, object] | None = None,
    ) -> Mapping[str, object]:
        """Deliver one application notification without becoming a failure path."""
        service = self.for_project_config(config)
        if service._enable_desktop is False and not service._webhook_configs:
            return {"enabled": False, "desktop": False, "webhooks": []}
        try:
            event = NotificationEvent(
                kind=NotificationKind(kind),
                project_id=project_id,
                title=title,
                message=message,
                payload=dict(payload or {}),
            )
            return await service.dispatch(event)
        except Exception as exc:  # noqa: BLE001 - notifications are never queue semantics
            return {"enabled": True, "desktop": False, "webhooks": [], "error": type(exc).__name__}

    async def dispatch(self, event: NotificationEvent) -> dict[str, Any]:
        tasks: list[asyncio.Task[Any]] = []
        if self._enable_desktop:
            tasks.append(asyncio.create_task(self._desktop.notify(event)))

        webhook_tasks: list[asyncio.Task[bool]] = []
        for cfg in self._webhook_configs:
            url = str(cfg.get("url", ""))
            secret = cfg.get("secret")
            if url:
                webhook_tasks.append(
                    asyncio.create_task(self._webhook.publish(event, url=url, secret=secret))
                )

        all_tasks = [*tasks, *webhook_tasks]
        results = await asyncio.gather(*all_tasks, return_exceptions=True) if all_tasks else []
        desktop_res = results[0] if tasks and isinstance(results[0], bool) else False
        webhook_offset = len(tasks)
        webhook_res = results[webhook_offset:]

        return {
            "desktop": desktop_res,
            "webhooks": [result if isinstance(result, bool) else False for result in webhook_res],
        }
