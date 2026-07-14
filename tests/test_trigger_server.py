import asyncio
import json
import unittest
from unittest.mock import AsyncMock, Mock

from weread.task_manager import ReadingTaskManager
from weread.trigger_server import TriggerServer


class TriggerServerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.manager = ReadingTaskManager(AsyncMock(), Mock())
        self.server = TriggerServer(self.manager, "127.0.0.1", 0, Mock())
        await self.server.start()
        self.port = self.server._server.sockets[0].getsockname()[1]

    async def asyncTearDown(self):
        await self.manager.wait()
        await self.server.close()

    async def request(self, request: str):
        reader, writer = await asyncio.open_connection("127.0.0.1", self.port)
        writer.write(request.encode("ascii"))
        await writer.drain()
        response = await reader.read()
        writer.close()
        await writer.wait_closed()
        headers, body = response.split(b"\r\n\r\n", 1)
        return headers, json.loads(body)

    async def test_trigger_endpoint_starts_reading(self):
        headers, body = await self.request(
            "POST /trigger HTTP/1.1\r\nHost: localhost\r\nContent-Length: 0\r\n\r\n"
        )

        self.assertIn(b"202 Accepted", headers)
        self.assertEqual(body["state"], "started")

    async def test_status_endpoint_reports_manager_state(self):
        headers, body = await self.request(
            "GET /status HTTP/1.1\r\nHost: localhost\r\n\r\n"
        )

        self.assertIn(b"200 OK", headers)
        self.assertEqual(body, {"running": False, "pending": False})
