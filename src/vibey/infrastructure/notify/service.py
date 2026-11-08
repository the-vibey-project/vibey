# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Composite notification service coordinating desktop alerts and signed webhooks."""

import asyncio
from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from vibey.application.interfaces import EmailPort, MessagingPort, SmsPort
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
        messaging: MessagingPort | None = None,
        messaging_room: str | None = None,
        email: EmailPort | None = None,
        sms: SmsPort | None = None,
        send_messaging: bool = False,
        email_to: Sequence[str] = (),
        sms_to: Sequence[str] = (),
    ) -> None:
        self._desktop = desktop_notifier or DesktopNotifier()
        self._webhook = webhook_publisher or WebhookPublisher()
        self._webhook_configs = list(webhook_configs or [])
        self._enable_desktop = enable_desktop
        self._messaging = messaging
        self._messaging_room = (
            messaging_room.strip() if messaging_room and messaging_room.strip() else None
        )
        self._email = email
        self._sms = sms
        self._send_messaging = send_messaging
        self._email_to = tuple(email_to)
        self._sms_to = tuple(sms_to)

    @staticmethod
    def _recipients(raw: object) -> tuple[str, ...]:
        if not isinstance(raw, Sequence) or isinstance(raw, str | bytes):
            return ()
        recipients: list[str] = []
        for item in raw:
            if isinstance(item, str) and item.strip():
                recipients.append(item.strip())
        return tuple(recipients)

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
            messaging=self._messaging,
            messaging_room=self._messaging_room,
            email=self._email,
            sms=self._sms,
            send_messaging=raw.get("messaging", True) is True,
            email_to=self._recipients(raw.get("email_to", ())),
            sms_to=self._recipients(raw.get("sms_to", ())),
        )

    def has_channels(self) -> bool:
        """Whether any notification channel is configured and enabled."""
        if self._enable_desktop:
            return True
        if bool(self._webhook_configs):
            return True
        if (
            self._send_messaging
            and self._messaging is not None
            and self._messaging_room is not None
        ):
            return True
        if self._email is not None and bool(self._email_to):
            return True
        return bool(self._sms is not None and self._sms_to)

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
        if not service.has_channels():
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

    def _surface_tasks(self, event: NotificationEvent) -> list[tuple[str, asyncio.Task[None]]]:
        tasks: list[tuple[str, asyncio.Task[None]]] = []
        subject = f"[vibey] {event.title}"

        messaging = self._messaging
        messaging_room = self._messaging_room
        if self._send_messaging and messaging is not None and messaging_room is not None:
            tasks.append(
                (
                    "messaging",
                    asyncio.create_task(
                        messaging.send_message(messaging_room, f"{subject}\n{event.message}")
                    ),
                )
            )

        email = self._email
        if email is not None:
            for address in self._email_to:
                tasks.append(
                    (
                        "email",
                        asyncio.create_task(email.send_email(address, subject, event.message)),
                    )
                )

        sms = self._sms
        if sms is not None:
            for number in self._sms_to:
                tasks.append(
                    (
                        "sms",
                        asyncio.create_task(sms.send_sms(number, f"{subject}: {event.message}")),
                    )
                )

        return tasks

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

        surface_tasks = self._surface_tasks(event)
        surface_task_objs: list[asyncio.Task[Any]] = [task for _, task in surface_tasks]
        all_tasks = [*tasks, *webhook_tasks, *surface_task_objs]
        results = await asyncio.gather(*all_tasks, return_exceptions=True) if all_tasks else []
        desktop_res = results[0] if tasks and isinstance(results[0], bool) else False
        webhook_offset = len(tasks)
        webhook_res = results[webhook_offset : webhook_offset + len(webhook_tasks)]

        out: dict[str, Any] = {
            "desktop": desktop_res,
            "webhooks": [result if isinstance(result, bool) else False for result in webhook_res],
        }

        surface_offset = webhook_offset + len(webhook_tasks)
        surface_res = results[surface_offset:]

        messaging_ran = False
        messaging_success = False
        email_res: list[bool] = []
        sms_res: list[bool] = []

        for (label, _), res in zip(surface_tasks, surface_res, strict=True):
            success = not isinstance(res, BaseException)
            if label == "messaging":
                messaging_ran = True
                messaging_success = success
            elif label == "email":
                email_res.append(success)
            else:
                sms_res.append(success)

        if messaging_ran:
            out["messaging"] = messaging_success
        if email_res:
            out["email"] = email_res
        if sms_res:
            out["sms"] = sms_res

        return out
