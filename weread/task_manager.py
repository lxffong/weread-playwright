import asyncio
from collections.abc import Awaitable, Callable


class ReadingTaskManager:
    """串行执行阅读任务，并将执行期间的多次触发合并为一次。"""

    def __init__(self, run_task: Callable[[bool], Awaitable[None]], logger):
        self.run_task = run_task
        self.logger = logger
        self.running = False
        self.pending = False
        self._current_http_triggered = False
        self._pending_http_triggered = False
        self._runner: asyncio.Task | None = None

    def trigger(self, http_triggered: bool = False) -> str:
        if self.running:
            already_pending = self.pending
            self.pending = True
            self._pending_http_triggered = (
                self._pending_http_triggered or http_triggered
            )
            if not already_pending:
                self.logger.info("阅读任务正在执行，已登记一次待执行任务")
            return "already_pending" if already_pending else "queued"

        self.running = True
        self._current_http_triggered = http_triggered
        self._runner = asyncio.create_task(self._run())
        return "started"

    async def trigger_async(self, http_triggered: bool = False) -> str:
        """从异步调度器触发任务，确保在其事件循环中创建 Task。"""
        return self.trigger(http_triggered=http_triggered)

    async def _run(self) -> None:
        try:
            while True:
                try:
                    await self.run_task(self._current_http_triggered)
                except Exception:
                    self.logger.exception("阅读任务出现未处理异常")

                if not self.pending:
                    break
                self.pending = False
                self._current_http_triggered = self._pending_http_triggered
                self._pending_http_triggered = False
                self.logger.info("开始执行已登记的阅读任务")
        finally:
            self.running = False
            self._current_http_triggered = False
            self._pending_http_triggered = False
            self._runner = None

    async def wait(self) -> None:
        if self._runner:
            await self._runner

    def status(self) -> dict:
        return {"running": self.running, "pending": self.pending}
