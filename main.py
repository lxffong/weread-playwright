import asyncio

from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        # Launching with --no-sandbox is often necessary in Docker
        browser = await p.chromium.launch(
            headless=False, args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        page = await browser.new_page()
        print("Navigating to WeChat Read...")
        await page.goto("https://weread.qq.com")
        title = await page.title()
        print(f"Title: {title}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
