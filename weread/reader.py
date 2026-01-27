import asyncio
import random
from datetime import datetime
from typing import Optional

from playwright.async_api import Page


class Reader:
    def __init__(self, config, logger, stats):
        self.config = config
        self.logger = logger
        self.stats = stats
        self.speed_map = {"slow": (5, 10), "medium": (3, 8), "fast": (1, 5)}

    async def select_book(self, page: Page) -> Optional[str]:
        try:
            book_ids = self.config.get("reading.book_ids", [])

            if not book_ids:
                self.logger.error("未配置书籍 ID")
                return None

            book_id = random.choice(book_ids)
            book_url = f"https://weread.qq.com/web/reader/{book_id}"
            self.logger.info(f"从配置的书籍中随机选择: {book_id}")
            await page.goto(book_url)
            await asyncio.sleep(2)

            title = await page.title()
            self.logger.info(f"已打开书籍: {title}")

            return title
        except Exception as e:
            self.logger.error(f"选择书籍失败: {e}")
            return None

    async def read(self, page: Page, duration_minutes: float) -> int:
        start_time = datetime.now()

        try:
            while (datetime.now() - start_time).total_seconds() < duration_minutes * 60:
                await asyncio.sleep(random.uniform(5, 15))

                # 检查是否需要跳回第一章
                title = await page.title()
                need_jump = "已读完" in title

                if not need_jump:
                    texts_to_check = ["开通后即可阅读", "全 书 完"]
                    for text in texts_to_check:
                        locator = page.locator(f'text="{text}"')
                        if await locator.count() > 0 and await locator.is_visible():
                            need_jump = True
                            self.logger.info(f"检测到: {text}")
                            break

                if need_jump:
                    self.logger.info("跳回第一章")
                    catalog_btn = page.locator('button[title="目录"]')
                    if await catalog_btn.count() > 0:
                        await catalog_btn.click()
                        await asyncio.sleep(1)
                        first_chapter = page.locator(".readerCatalog_list_item").nth(1)
                        if await first_chapter.count() > 0:
                            await first_chapter.click()
                            await asyncio.sleep(1)
                    continue

                # 检查重试按钮
                retry_btn = page.locator('text="点击重试"')
                if await retry_btn.count() > 0:
                    self.logger.info("点击重试")
                    await retry_btn.click()
                    continue

                # 查找并点击下一章/下一页按钮
                next_btn = page.locator(
                    'button[title="下一章"], button[title="下一页"]'
                )
                if await next_btn.count() > 0 and await next_btn.is_visible():
                    await next_btn.click()
                    continue

                # 按下箭头键翻页
                await page.keyboard.press("ArrowDown")

        except Exception as e:
            self.logger.error(f"阅读过程出错: {e}")
            await page.reload()

        actual_minutes = int((datetime.now() - start_time).total_seconds() / 60)
        return actual_minutes

    async def auto_read(self, page: Page) -> dict:
        duration = self.config.get("reading.duration_minutes", 30)

        book_name = await self.select_book(page)
        if not book_name:
            return {"success": False, "message": "未找到书籍"}

        actual_minutes = await self.read(page, duration)
        self.stats.add_session(book_name, actual_minutes)

        return {
            "success": True,
            "book": book_name,
            "minutes": actual_minutes,
        }
