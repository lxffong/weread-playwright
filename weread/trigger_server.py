import asyncio
import json
from http import HTTPStatus

from weread.task_manager import ReadingTaskManager


class TriggerServer:
    def __init__(self, manager: ReadingTaskManager, host: str, port: int, logger):
        self.manager = manager
        self.host = host
        self.port = port
        self.logger = logger
        self._server: asyncio.Server | None = None

    async def start(self) -> None:
        self._server = await asyncio.start_server(
            self._handle_request, self.host, self.port
        )
        self.logger.info(f"主动触发服务已启动: http://{self.host}:{self.port}")

    async def close(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def _handle_request(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            request_line = await asyncio.wait_for(reader.readline(), timeout=5)
            method, path, _ = request_line.decode("ascii").strip().split(" ", 2)

            while True:
                line = await asyncio.wait_for(reader.readline(), timeout=5)
                if line in (b"\r\n", b"\n", b""):
                    break

            if method == "POST" and path == "/trigger":
                state = self.manager.trigger()
                messages = {
                    "started": "阅读任务已启动",
                    "queued": "任务正在执行，已登记一次待执行任务",
                    "already_pending": "任务正在执行，待执行任务已登记",
                }
                await self._respond(
                    writer, HTTPStatus.ACCEPTED, {"state": state, "message": messages[state]}
                )
            elif method == "GET" and path == "/status":
                await self._respond(writer, HTTPStatus.OK, self.manager.status())
            else:
                await self._respond(
                    writer, HTTPStatus.NOT_FOUND, {"message": "Not Found"}
                )
        except (asyncio.TimeoutError, UnicodeDecodeError, ValueError):
            await self._respond(
                writer, HTTPStatus.BAD_REQUEST, {"message": "Bad Request"}
            )
        finally:
            writer.close()
            await writer.wait_closed()

    async def _respond(self, writer, status: HTTPStatus, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = (
            f"HTTP/1.1 {status.value} {status.phrase}\r\n"
            "Content-Type: application/json; charset=utf-8\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Connection: close\r\n\r\n"
        )
        writer.write(headers.encode("ascii") + body)
        await writer.drain()
