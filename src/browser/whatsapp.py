import asyncio
import logging
from playwright.async_api import Page
from src.browser import selectors

logger = logging.getLogger("LANY.WhatsApp")

class WhatsAppController:
    def __init__(self, page: Page):
        self.page = page
        self.is_in_call = False

    async def open_whatsapp(self):
        logger.info("Navigating to WhatsApp Web...")
        await self.page.goto("https://web.whatsapp.com", wait_until="domcontentloaded")
        logger.info("Waiting for WhatsApp Web to load...")

        # Wait for either main chat list (logged in) or QR code
        try:
            await self.page.wait_for_selector(selectors.MAIN_CHAT_LIST, timeout=60000)
            logger.info("WhatsApp Web is ready and logged in!")
        except Exception:
            logger.warning("Main chat list not detected yet. QR scan might be required.")

    async def check_incoming_call(self) -> bool:
        # Check specific selectors for the modal or the accept button
        all_selectors = selectors.INCOMING_CALL_MODAL + selectors.ACCEPT_CALL_BUTTON
        for selector in all_selectors:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    logger.info(f"Incoming call detected via selector: {selector}")
                    return True
            except Exception:
                continue
        
        # Fallback check for any button that looks like an accept button
        try:
            buttons = await self.page.query_selector_all("button")
            for btn in buttons:
                text = (await btn.inner_text()).lower()
                aria = (await btn.get_attribute("aria-label") or "").lower()
                if "accept" in text or "jawab" in text or "terima" in text or "accept" in aria or "terima" in aria:
                    logger.info("Incoming call detected via button text fallback!")
                    return True
        except Exception:
            pass

        return False

    async def answer_call(self) -> bool:
        logger.info("Attempting to answer incoming call...")
        for selector in selectors.ACCEPT_CALL_BUTTON:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    await element.click()
                    logger.info(f"Accepted incoming call using selector: {selector}")
                    self.is_in_call = True
                    return True
            except Exception:
                continue
        
        # Fallback click strategy if selector exact match failed
        try:
            buttons = await self.page.query_selector_all("button")
            for btn in buttons:
                text = (await btn.inner_text()).lower()
                aria = (await btn.get_attribute("aria-label") or "").lower()
                if "accept" in text or "jawab" in text or "terima" in text or "accept" in aria or "terima" in aria:
                    await btn.click()
                    logger.info("Accepted incoming call via button text fallback!")
                    self.is_in_call = True
                    return True
        except Exception as e:
            logger.error(f"Fallback answer call error: {e}")

        logger.warning("Could not click Accept button automatically.")
        return False

    async def check_call_active(self) -> bool:
        # Strategy: The End Call button / phone-cross icon is visible DURING an active call.
        # If we can find it, the call is still alive.
        for selector in selectors.END_CALL_BUTTON:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    return True
            except Exception:
                continue

        # Fallback: check ACTIVE_CALL_BAR
        for selector in selectors.ACTIVE_CALL_BAR:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    return True
            except Exception:
                continue

        # Fallback: scan all spans for any call-related icons
        try:
            spans = await self.page.query_selector_all("span[data-icon]")
            for span in spans:
                icon = await span.get_attribute("data-icon")
                if icon and any(k in icon for k in ["phone", "call", "audio"]):
                    if await span.is_visible():
                        return True
        except Exception:
            pass

        return False

    async def end_call(self):
        logger.info("Attempting to end active call...")
        for selector in selectors.END_CALL_BUTTON:
            try:
                element = await self.page.query_selector(selector)
                if element and await element.is_visible():
                    await element.click()
                    logger.info("Call ended.")
                    self.is_in_call = False
                    return
            except Exception:
                continue
        self.is_in_call = False
