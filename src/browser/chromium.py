import os
import logging
from playwright.async_api import async_playwright, BrowserContext, Page

logger = logging.getLogger("LANY.Chromium")

class ChromiumManager:
    def __init__(self, user_data_dir: str = "browser_profile", headless: bool = False):
        self.user_data_dir = os.path.abspath(user_data_dir)
        self.headless = headless
        self.playwright = None
        self.context: BrowserContext = None
        self.page: Page = None

    async def start(self) -> Page:
        logger.info(f"Launching Chromium with persistent profile at: {self.user_data_dir}")
        os.makedirs(self.user_data_dir, exist_ok=True)

        self.playwright = await async_playwright().start()

        # Chromium launch arguments for WebRTC and Virtual Audio Routing
        args = [
            "--use-fake-ui-for-media-stream",  # Auto-grant mic/camera permissions
            "--autoplay-policy=no-user-gesture-required",
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox"
        ]

        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=self.headless,
            args=args,
            permissions=["microphone", "notifications"],
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # Use existing page or open a new one
        if len(self.context.pages) > 0:
            self.page = self.context.pages[0]
        else:
            self.page = await self.context.new_page()

        logger.info("Chromium instance launched successfully.")
        return self.page

    async def stop(self):
        logger.info("Closing Chromium context...")
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Chromium stopped.")
