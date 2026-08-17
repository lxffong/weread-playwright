import asyncio
import base64
import hashlib
import hmac
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock

from weread.auth import Auth
from weread.qr_webhook import QrWebhookNotifier


class FakeResponse:
    status = 200

    def close(self):
        pass


class QrWebhookNotifierTests(unittest.IsolatedAsyncioTestCase):
    async def test_sends_qr_as_signed_base64_json(self):
        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "qr_code.png"
            image = b"fake-png-bytes"
            image_path.write_bytes(image)
            captured = {}

            def opener(request, timeout):
                captured["request"] = request
                captured["timeout"] = timeout
                return FakeResponse()

            notifier = QrWebhookNotifier(
                "http://hermes.test/webhooks/weread-login-qr",
                "test-secret",
                Mock(),
                opener=opener,
            )

            self.assertTrue(await notifier.notify(image_path))

            request = captured["request"]
            body = json.loads(request.data)
            self.assertEqual(body["event_type"], "weread_login_qr")
            self.assertEqual(body["trigger"], "http")
            self.assertEqual(base64.b64decode(body["image_base64"]), image)
            self.assertEqual(body["image_sha256"], hashlib.sha256(image).hexdigest())

            timestamp = request.get_header("X-webhook-timestamp")
            signature = request.get_header("X-webhook-signature-v2")
            expected = hmac.new(
                b"test-secret",
                timestamp.encode() + b"." + request.data,
                hashlib.sha256,
            ).hexdigest()
            self.assertEqual(signature, expected)
            self.assertEqual(captured["timeout"], 10)

    async def test_disabled_notifier_does_not_make_request(self):
        opener = Mock()
        notifier = QrWebhookNotifier("", "", Mock(), opener=opener)

        self.assertFalse(await notifier.notify(Path("/does/not/exist.png")))
        opener.assert_not_called()

    async def test_auth_forwards_qr_path_to_webhook(self):
        webhook = AsyncMock()
        auth = Auth("/tmp/cookies.json", Mock(), qr_webhook=webhook)
        qr_path = Path("/tmp/qr_code.png")

        await auth._notify_qr_webhook(qr_path)

        webhook.notify.assert_awaited_once_with(qr_path)
