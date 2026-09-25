from playwright.async_api import async_playwright

from playwright.async_api import async_playwright

class BrowserManager:
    def __init__(self, headless=False):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.page = None

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def start(self):
        if not self.page:
            self.page = await self.browser.new_page(
                viewport={
                    "width": 1366,
                    "height": 900
                }
            )
        return self.page

    async def navigate(self, url):
        if not self.page:
            await self.start()
        try:
            response = await self.page.goto(url, wait_until="domcontentloaded")
            return response.ok if response else False
        except Exception as e:
            print(f"Navigation error: {e}")
            return False