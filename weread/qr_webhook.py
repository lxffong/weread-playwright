import asyncio
import base64
import hashlib
import hmac
import json
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable


class QrWebhookNotifier:
    """Send a WeRead login QR image to a Hermes webhook."""

    def __init__(
        self,
        url: str,
        secret: str,
        logger,
        *,
        timeout: int = 10,
        opener: Callable = urllib.request.urlopen,
    ):
        self.url = url.strip()
        self.secret = secret.strip()
        self.logger = logger
        self.timeout = timeout
        self.opener = opener

    @classmethod
    def from_config(cls, config, logger):
        if not config.get("notifications.webhook.enabled", False):
            return None

        url = config.get("notifications.webhook.url", "")
        secret = config.get("notifications.webhook.secret", "")
        if not url or not secret:
            logger.warning("二维码 Webhook 已启用但 URL 或 Secret 未配置")
            return None

        return cls(
            url,
            secret,
            logger,
            timeout=config.get("notifications.webhook.timeout_seconds", 10),
        )

    async def notify(self, image_path: Path) -> bool:
        if not self.url or not self.secret:
            return False

        try:
            image_data = image_path.read_bytes()
            image_sha256 = hashlib.sha256(image_data).hexdigest()
            body_payload = {
                "event_type": "weread_login_qr",
                "qr_id": f"weread-{image_sha256[:16]}-{int(time.time())}",
                "image_base64": base64.b64encode(image_data).decode("ascii"),
                "mime_type": "image/png",
                "image_sha256": image_sha256,
                "image_size": len(image_data),
                "expires_at": (
                    datetime.now(timezone.utc) + timedelta(minutes=5)
                ).isoformat(),
                "source": "weread-playwright",
                "trigger": "http",
            }
            body = json.dumps(
                body_payload, ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")
            timestamp = str(int(time.time()))
            signature = hmac.new(
                self.secret.encode("utf-8"),
                timestamp.encode("ascii") + b"." + body,
                hashlib.sha256,
            ).hexdigest()
            request = urllib.request.Request(
                self.url,
                data=body,
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "X-Webhook-Timestamp": timestamp,
                    "X-Webhook-Signature-V2": signature,
                    "X-Request-ID": body_payload["qr_id"],
                },
            )

            response = await asyncio.to_thread(
                self.opener, request, timeout=self.timeout
            )
            try:
                status = getattr(response, "status", None)
                if status is None:
                    status = response.getcode()
            finally:
                close = getattr(response, "close", None)
                if close:
                    close()

            if status < 200 or status >= 300:
                raise RuntimeError(f"Webhook returned HTTP {status}")

            self.logger.info(
                "登录二维码已发送到 Hermes Webhook: size=%d sha256=%s",
                len(image_data),
                image_sha256[:16],
            )
            return True
        except Exception as exc:
            self.logger.error("登录二维码发送到 Hermes Webhook 失败: %s", exc)
            return False
