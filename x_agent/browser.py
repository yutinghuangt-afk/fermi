"""Playwright browser lifecycle management."""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

STORAGE_STATE_PATH = Path(__file__).parent.parent / ".x_session.json"


async def launch_browser(headless: bool = False) -> tuple[Browser, BrowserContext]:
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(
        headless=headless,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ],
    )
    storage_state = STORAGE_STATE_PATH if STORAGE_STATE_PATH.exists() else None
    context = await browser.new_context(
        viewport={"width": 1280, "height": 900},
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        storage_state=storage_state,
    )
    # Hide webdriver flag
    await context.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return browser, context


async def save_session(context: BrowserContext) -> None:
    await context.storage_state(path=str(STORAGE_STATE_PATH))


async def close_browser(browser: Browser) -> None:
    await browser.close()
