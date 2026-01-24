import asyncio
import json
from pathlib import Path
from typing import Optional

from playwright.async_api import BrowserContext, Page


class Auth:
    def __init__(self, cookies_file: str, logger, notifier=None):
        self.cookies_file = Path(cookies_file)
        self.logger = logger
        self.notifier = notifier

    async def load_cookies(self, context: BrowserContext) -> bool:
        if not self.cookies_file.exists():
            return False
        try:
            with open(self.cookies_file, "r") as f:
                cookies = json.load(f)
            await context.add_cookies(cookies)
            self.logger.info(f"已加载 cookies: {self.cookies_file}")
            return True
        except Exception as e:
            self.logger.error(f"加载 cookies 失败: {e}")
            return False

    async def save_cookies(self, context: BrowserContext):
        try:
            cookies = await context.cookies()
            with open(self.cookies_file, "w") as f:
                json.dump(cookies, f)
            self.logger.info(f"已保存 cookies: {self.cookies_file}")
        except Exception as e:
            self.logger.error(f"保存 cookies 失败: {e}")

    async def login_with_qr(self, page: Page, timeout: int = 300) -> bool:
        try:
            await page.goto("https://weread.qq.com")

            login_link = page.locator('a:has-text("登录")')
            if await login_link.count() > 0:
                self.logger.info("找到登录链接，点击...")
                await asyncio.sleep(1)
                await login_link.first.click()
                await asyncio.sleep(2)

                # 使用更精确的定位策略查找二维码
                qr_code_found = False

                # 优先查找二维码图片元素
                try:
                    qr_img = page.locator(
                        "xpath=//img[contains(@class, 'qr') or contains(@src, 'qr') or contains(@alt, '二维码')]"
                    )
                    if await qr_img.count() > 0:
                        self.logger.info("找到二维码图片元素")
                        qr_code_found = True
                except:
                    pass

                # 备选方案：查找包含"扫码"或"二维码"文本的元素
                if not qr_code_found:
                    try:
                        qr_text = page.locator(
                            "xpath=//*[contains(text(), '扫码') or contains(text(), '二维码')]"
                        )
                        if await qr_text.count() > 0:
                            self.logger.info("找到包含'扫码'或'二维码'文本的元素")
                            qr_code_found = True
                    except:
                        pass

                if qr_code_found:
                    await asyncio.sleep(1)
                    qr_path = self.cookies_file.parent / "qr_code.png"
                    await page.screenshot(path=str(qr_path))
                    self.logger.info(f"二维码已保存: {qr_path}")

                    # 如果配置了邮件通知，发送二维码到邮箱
                    if self.notifier:
                        self.notifier.send_email_with_attachment(
                            subject="WeRead 登录二维码",
                            body="请使用微信扫描附件中的二维码登录 WeRead。",
                            attachment_path=str(qr_path)
                        )
                else:
                    self.logger.info("未找到二维码相关元素，可能已经登录")

                max_retries = 3
                while max_retries > 0:
                    self.logger.info("等待登录...")

                    try:
                        await page.wait_for_selector(
                            'text="我的书架"', timeout=timeout * 1000
                        )
                        self.logger.info("登录成功")
                        return True
                    except:
                        pass

                    expired = page.locator('text="点击刷新二维码"')
                    if await expired.count() > 0:
                        self.logger.info("二维码已过期，刷新中...")
                        await expired.click()
                        await asyncio.sleep(2)
                        await page.screenshot(path=str(qr_path))
                        self.logger.info("二维码已刷新")
                        max_retries -= 1
                        continue

                    await asyncio.sleep(5)

                self.logger.error("登录超时")
                return False
            else:
                self.logger.info("已登录")
                return True
        except Exception as e:
            self.logger.error(f"登录失败: {e}")
            return False
