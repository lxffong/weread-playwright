import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

from weread.auth import Auth
from weread.config import Config
from weread.logger import setup_logger
from weread.notifier import Notifier
from weread.reader import Reader
from weread.scheduler import Scheduler
from weread.stats import Stats


async def run_reading_session(config, logger):
    """执行一次阅读会话"""
    notifier = Notifier(config, logger)
    auth = Auth(config.get("cookies_file"), logger, notifier)
    stats = Stats(config.get("stats_file"))
    reader = Reader(config, logger, stats)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=config.get("browser.headless", False),
            channel="chrome",
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        context = await browser.new_context()
        page = await context.new_page()

        try:
            await auth.load_cookies(context)

            if not await auth.login_with_qr(page):
                logger.error("登录失败")
                notifier.send("WeRead 阅读失败", "登录失败")
                return

            await auth.save_cookies(context)

            result = await reader.auto_read(page)

            if result["success"]:
                message = f"书籍: {result['book']}\n页数: {result['pages']}\n时长: {result['minutes']}分钟\n{stats.get_summary()}"
                logger.info(f"阅读完成 - {message}")
                notifier.send("WeRead 阅读完成", message)
            else:
                logger.error(f"阅读失败: {result.get('message', '未知错误')}")
                notifier.send("WeRead 阅读失败", result.get("message", "未知错误"))

        except Exception as e:
            logger.error(f"运行出错: {e}")
            notifier.send("WeRead 运行出错", str(e))
            await page.reload()
        finally:
            await browser.close()


async def main():
    Path("data").mkdir(exist_ok=True)

    config = Config()
    logger = setup_logger()

    logger.info("WeRead 自动阅读启动")

    if config.get("schedule.enabled"):
        scheduler = Scheduler(config, logger)
        scheduler.add_job(
            lambda: asyncio.create_task(run_reading_session(config, logger)),
            config.get("schedule.cron"),
        )
        scheduler.start()
        logger.info("定时任务模式，等待执行...")

        try:
            while True:
                await asyncio.sleep(60)
        except KeyboardInterrupt:
            logger.info("收到停止信号")
            scheduler.shutdown()
    else:
        await run_reading_session(config, logger)

    logger.info("WeRead 自动阅读结束")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序已停止")
        sys.exit(0)
