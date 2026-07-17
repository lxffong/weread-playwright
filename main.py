import asyncio
import signal
import sys
import traceback
from pathlib import Path

from playwright.async_api import async_playwright

from weread.auth import Auth
from weread.config import Config
from weread.logger import setup_logger
from weread.notifier import Notifier
from weread.reader import AuthenticationRequiredError, Reader
from weread.scheduler import Scheduler
from weread.stats import Stats
from weread.task_manager import ReadingTaskManager
from weread.trigger_server import TriggerServer


async def read_with_reauthentication(
    page, context, reader: Reader, auth: Auth, config: Config, logger
) -> dict:
    """认证失效时重新登录，并重新发起完整的阅读任务。"""
    retries_remaining = max(0, config.get("reading.auth_retry_count", 1))

    while True:
        try:
            return await reader.auto_read(page)
        except AuthenticationRequiredError:
            if retries_remaining == 0:
                logger.error("阅读认证失效，已达到重新发起次数上限")
                return {"success": False, "message": "阅读认证失败，重新发起仍未成功"}

            retries_remaining -= 1
            logger.warning("阅读认证已失效，正在重新认证并发起阅读任务")
            if not await auth.login_with_qr(page):
                logger.error("重新认证失败")
                return {"success": False, "message": "阅读认证失败，重新认证未成功"}

            await auth.save_cookies(context)
            logger.info("重新认证成功，重新发起阅读任务")


async def run_reading_session(config: Config, logger) -> None:
    """执行一次阅读会话"""
    try:
        logger.info("===== 开始执行阅读任务 =====")
        logger.info(f"当前事件循环: {id(asyncio.get_event_loop())}")
        logger.info(f"配置信息: headless={config.get('browser.headless')}, no_sandbox={config.get('browser.no_sandbox')}")

        notifier = Notifier(config, logger)
        auth = Auth(config.get("cookies_file"), logger, notifier)
        stats = Stats(config.get("stats_file"))
        reader = Reader(config, logger, stats)

        async with async_playwright() as p:
            # 根据配置决定是否使用 no-sandbox 标志（主要用于 Docker 环境）
            browser_args = []
            if config.get("browser.no_sandbox", False):
                browser_args.extend(["--no-sandbox", "--disable-setuid-sandbox"])

            logger.info(f"启动浏览器，参数: {browser_args}")
            browser = await p.chromium.launch(
                headless=config.get("browser.headless", False),
                channel="chrome",
                args=browser_args + ["--remote-debugging-port=9222"],

            )
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
            )
            page = await context.new_page()
            logger.info("浏览器启动成功")

            try:
                await auth.load_cookies(context)

                if not await auth.login_with_qr(page):
                    logger.error("登录失败")
                    notifier.send("WeRead 阅读失败", "登录失败")
                    return

                await auth.save_cookies(context)

                result = await read_with_reauthentication(
                    page, context, reader, auth, config, logger
                )

                # 使用安全的字典访问
                if result.get("success"):
                    book = result.get("book", "未知")
                    minutes = result.get("minutes", 0)
                    message = f"书籍: {book}\n时长: {minutes}分钟\n{stats.get_summary()}"
                    logger.info(f"阅读完成 - {message}")
                    # 阅读结束截屏并随邮件发送（固定文件名，覆盖）
                    screenshot_path = Path("data") / "reading_end.png"
                    try:
                        await page.screenshot(path=str(screenshot_path))
                        notifier.send_with_attachment(
                            "WeRead 阅读完成",
                            message,
                            str(screenshot_path),
                        )
                    except Exception as e:
                        logger.error(f"截屏或邮件发送失败: {e}")
                        notifier.send("WeRead 阅读完成", message)
                else:
                    logger.error(f"阅读失败: {result.get('message', '未知错误')}")
                    notifier.send("WeRead 阅读失败", result.get("message", "未知错误"))

            except Exception as e:
                logger.error(f"运行出错: {e}\n{traceback.format_exc()}")
                notifier.send("WeRead 运行出错", str(e))
            finally:
                await browser.close()
                logger.info("浏览器已关闭")

    except Exception as e:
        logger.error(f"阅读任务顶层异常: {e}\n{traceback.format_exc()}")


async def main():
    Path("data").mkdir(exist_ok=True)

    config = Config()
    logger = setup_logger()

    logger.info("WeRead 自动阅读启动")

    manager = ReadingTaskManager(
        lambda: run_reading_session(config, logger), logger
    )
    schedule_enabled = config.get("schedule.enabled")
    trigger_enabled = config.get("trigger.enabled")
    scheduler = None
    trigger_server = None

    if schedule_enabled:
        scheduler = Scheduler(config, logger)
        scheduler.add_job(
            manager.trigger_async,
            config.get("schedule.cron"),
        )
        scheduler.start()
        logger.info("定时任务模式，等待执行...")

    if trigger_enabled:
        trigger_server = TriggerServer(
            manager,
            config.get("trigger.host"),
            config.get("trigger.port"),
            logger,
        )
        await trigger_server.start()

    if schedule_enabled or trigger_enabled:
        # 保持原有行为：未开启定时模式时，启动后立即阅读一次。
        if not schedule_enabled:
            manager.trigger()

        stop_event = asyncio.Event()
        loop = asyncio.get_running_loop()

        def signal_handler():
            logger.info("收到停止信号，准备退出...")
            stop_event.set()

        if sys.platform != "win32":
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, signal_handler)

        try:
            await stop_event.wait()
        except KeyboardInterrupt:
            logger.info("收到停止信号，准备退出...")
        finally:
            if sys.platform != "win32":
                for sig in (signal.SIGINT, signal.SIGTERM):
                    loop.remove_signal_handler(sig)

            if trigger_server:
                await trigger_server.close()
            if scheduler:
                logger.info("正在关闭调度器...")
                scheduler.shutdown()
            await manager.wait()
    else:
        manager.trigger()
        await manager.wait()

    logger.info("WeRead 自动阅读结束")


async def main_test():
    """测试模式：立即执行一次阅读任务"""
    Path("data").mkdir(exist_ok=True)

    config = Config()
    logger = setup_logger()

    logger.info("WeRead 测试模式 - 立即执行")

    await run_reading_session(config, logger)

    logger.info("测试完成")


if __name__ == "__main__":
    asyncio.run(main())
