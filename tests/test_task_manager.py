import asyncio
import unittest
from unittest.mock import AsyncMock, Mock

from weread.task_manager import ReadingTaskManager


class ReadingTaskManagerTests(unittest.IsolatedAsyncioTestCase):
    async def test_starts_task_immediately(self):
        run_task = AsyncMock()
        manager = ReadingTaskManager(run_task, Mock())

        self.assertEqual(manager.trigger(), "started")
        await manager.wait()

        run_task.assert_awaited_once()
        self.assertEqual(manager.status(), {"running": False, "pending": False})

    async def test_coalesces_triggers_while_running(self):
        release_first = asyncio.Event()
        calls = 0

        async def run_task():
            nonlocal calls
            calls += 1
            if calls == 1:
                await release_first.wait()

        manager = ReadingTaskManager(run_task, Mock())
        self.assertEqual(manager.trigger(), "started")
        await asyncio.sleep(0)

        self.assertEqual(manager.trigger(), "queued")
        self.assertEqual(manager.trigger(), "already_pending")
        release_first.set()
        await manager.wait()

        self.assertEqual(calls, 2)

    async def test_does_not_lose_trigger_before_runner_starts(self):
        run_task = AsyncMock()
        manager = ReadingTaskManager(run_task, Mock())

        self.assertEqual(manager.trigger(), "started")
        self.assertEqual(manager.trigger(), "queued")
        await manager.wait()

        self.assertEqual(run_task.await_count, 2)
