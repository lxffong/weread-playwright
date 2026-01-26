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
from weread.reader import Reader
from weread.scheduler import Scheduler
from weread.stats import Stats


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
                args=browser_args,
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

                result = await reader.auto_read(page)

                # 使用安全的字典访问
                if result.get("success"):
                    book = result.get("book", "未知")
                    pages = result.get("pages", 0)
                    minutes = result.get("minutes", 0)
                    message = f"书籍: {book}\n页数: {pages}\n时长: {minutes}分钟\n{stats.get_summary()}"
                    logger.info(f"阅读完成 - {message}")
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

    if config.get("schedule.enabled"):
        scheduler = Scheduler(config, logger)
        scheduler.add_job(
            run_reading_session,
            config.get("schedule.cron"),
            args=(config, logger)
        )
        scheduler.start()
        logger.info("定时任务模式，等待执行...")

        # 创建一个 Event 用于优雅退出
        stop_event = asyncio.Event()

        # 获取当前事件循环
        loop = asyncio.get_running_loop()

        # 设置信号处理器（使用 asyncio 的方式）
        def signal_handler():
            logger.info("收到停止信号，准备退出...")
            stop_event.set()

        # 注册信号处理（SIGINT 和 SIGTERM）
        # 注意：Windows 不支持 SIGTERM，add_signal_handler 仅在 Unix 系统可用
        if sys.platform != "win32":
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, signal_handler)

        try:
            # 等待停止信号
            await stop_event.wait()
        except KeyboardInterrupt:
            # Windows 下的 Ctrl+C 处理
            logger.info("收到停止信号，准备退出...")
        finally:
            # 移除信号处理器（仅 Unix）
            if sys.platform != "win32":
                for sig in (signal.SIGINT, signal.SIGTERM):
                    loop.remove_signal_handler(sig)
            # 确保调度器被正确关闭
            logger.info("正在关闭调度器...")
            scheduler.shutdown()
    else:
        try:
            await run_reading_session(config, logger)
        except Exception as e:
            logger.error(f"执行失败: {e}\n{traceback.format_exc()}")

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
