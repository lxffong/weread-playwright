import unittest
from unittest.mock import AsyncMock, Mock

from main import read_with_reauthentication
from weread.reader import AuthenticationRequiredError


class ReadWithReauthenticationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.page = Mock()
        self.context = Mock()
        self.reader = Mock()
        self.reader.auto_read = AsyncMock()
        self.auth = Mock()
        self.auth.login_with_qr = AsyncMock()
        self.auth.save_cookies = AsyncMock()
        self.config = Mock()
        self.config.get.return_value = 1
        self.logger = Mock()

    async def test_reauthenticates_and_restarts_reading(self):
        expected = {"success": True, "book": "测试书籍", "minutes": 10}
        self.reader.auto_read.side_effect = [
            AuthenticationRequiredError(),
            expected,
        ]
        self.auth.login_with_qr.return_value = True

        result = await read_with_reauthentication(
            self.page,
            self.context,
            self.reader,
            self.auth,
            self.config,
            self.logger,
        )

        self.assertEqual(result, expected)
        self.assertEqual(self.reader.auto_read.await_count, 2)
        self.auth.login_with_qr.assert_awaited_once_with(self.page)
        self.auth.save_cookies.assert_awaited_once_with(self.context)

    async def test_returns_failure_when_reauthentication_fails(self):
        self.reader.auto_read.side_effect = AuthenticationRequiredError()
        self.auth.login_with_qr.return_value = False

        result = await read_with_reauthentication(
            self.page,
            self.context,
            self.reader,
            self.auth,
            self.config,
            self.logger,
        )

        self.assertFalse(result["success"])
        self.assertIn("重新认证未成功", result["message"])
        self.assertEqual(self.reader.auto_read.await_count, 1)
        self.auth.save_cookies.assert_not_awaited()

    async def test_stops_after_configured_retry_limit(self):
        self.reader.auto_read.side_effect = AuthenticationRequiredError()
        self.auth.login_with_qr.return_value = True

        result = await read_with_reauthentication(
            self.page,
            self.context,
            self.reader,
            self.auth,
            self.config,
            self.logger,
        )

        self.assertFalse(result["success"])
        self.assertIn("仍未成功", result["message"])
        self.assertEqual(self.reader.auto_read.await_count, 2)
        self.assertEqual(self.auth.login_with_qr.await_count, 1)


if __name__ == "__main__":
    unittest.main()
