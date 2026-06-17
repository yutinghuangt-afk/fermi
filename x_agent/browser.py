import asyncio
import logging
import os
import random
from pathlib import Path

from playwright.async_api import async_playwright, Page, BrowserContext
from playwright_stealth import stealth_async

from x_agent import config

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
VIEWPORT = {"width": 1280, "height": 900}


async def _new_context(browser, session_path: str) -> BrowserContext:
    kwargs = {
        "user_agent": USER_AGENT,
        "viewport": VIEWPORT,
        "locale": "zh-TW",
    }
    if Path(session_path).exists():
        kwargs["storage_state"] = session_path
        logger.info("Loaded session from %s", session_path)
    return await browser.new_context(**kwargs)


async def _login(page: Page) -> bool:
    logger.info("Navigating to X login page...")
    await page.goto("https://x.com/i/flow/login", wait_until="networkidle")
    await asyncio.sleep(random.uniform(2, 3))

    # Username step
    username_input = page.get_by_label("Phone, email, or username")
    await username_input.fill(config.X_USERNAME)
    await asyncio.sleep(random.uniform(0.5, 1.0))
    await page.get_by_role("button", name="Next").click()
    await asyncio.sleep(random.uniform(2, 3))

    # X sometimes asks for email verification
    email_verify = page.get_by_label("Phone or email")
    try:
        await email_verify.wait_for(timeout=3000)
        logger.info("Email verification step detected")
        await email_verify.fill(config.X_EMAIL)
        await page.get_by_role("button", name="Next").click()
        await asyncio.sleep(random.uniform(1.5, 2.5))
    except Exception:
        pass

    # Password step
    password_input = page.get_by_label("Password", exact=True)
    await password_input.wait_for(timeout=10000)
    await password_input.fill(config.X_PASSWORD)
    await asyncio.sleep(random.uniform(0.5, 1.0))
    await page.get_by_role("button", name="Log in").click()

    # Handle 2FA if present (ask user interactively on first run)
    try:
        twofa = page.get_by_label("Confirmation code")
        await twofa.wait_for(timeout=8000)
        logger.warning("2FA required! Check your authenticator app.")
        code = input("Enter 2FA code: ").strip()
        await twofa.fill(code)
        await page.get_by_role("button", name="Next").click()
    except Exception:
        pass

    await asyncio.sleep(random.uniform(3, 5))
    return "home" in page.url or "x.com" in page.url


async def _extract_posts(page: Page) -> list[dict]:
    posts = []
    seen_ids = set()

    articles = await page.query_selector_all('article[data-testid="tweet"]')
    for article in articles:
        try:
            post = await _parse_article(article)
            if post and post["text"] and post["id"] not in seen_ids:
                seen_ids.add(post["id"])
                posts.append(post)
        except Exception as e:
            logger.debug("Failed to parse article: %s", e)

    return posts


async def _parse_article(article) -> dict | None:
    try:
        # Author name
        author_el = await article.query_selector('[data-testid="User-Name"]')
        author_text = await author_el.inner_text() if author_el else ""
        parts = author_text.strip().split("\n")
        author = parts[0] if parts else ""
        handle = parts[1] if len(parts) > 1 else ""

        # Tweet text
        text_el = await article.query_selector('[data-testid="tweetText"]')
        text = await text_el.inner_text() if text_el else ""

        # Timestamp + URL
        time_el = await article.query_selector("time")
        timestamp = await time_el.get_attribute("datetime") if time_el else ""
        link_el = await article.query_selector("a[href*='/status/']")
        url = await link_el.get_attribute("href") if link_el else ""
        if url and not url.startswith("http"):
            url = "https://x.com" + url

        # Metrics
        metrics = {}
        for metric in ["reply", "retweet", "like", "bookmark"]:
            el = await article.query_selector(f'[data-testid="{metric}"]')
            if el:
                span = await el.query_selector("span[data-testid='app-text-transition-container']")
                val = await span.inner_text() if span else "0"
                metrics[metric] = val.strip() or "0"

        post_id = url.split("/status/")[-1].split("?")[0] if "/status/" in url else url
        return {
            "id": post_id,
            "author": author,
            "handle": handle,
            "text": text,
            "timestamp": timestamp,
            "url": url,
            "replies": metrics.get("reply", "0"),
            "retweets": metrics.get("retweet", "0"),
            "likes": metrics.get("like", "0"),
            "bookmarks": metrics.get("bookmark", "0"),
        }
    except Exception as e:
        logger.debug("parse_article error: %s", e)
        return None


async def get_timeline_posts() -> list[dict]:
    session_path = config.SESSION_PATH
    max_posts = config.MAX_POSTS

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await _new_context(browser, session_path)
        page = await context.new_page()
        await stealth_async(page)

        # Navigate to home; if redirected to login, do login
        await page.goto("https://x.com/home", wait_until="domcontentloaded")
        await asyncio.sleep(random.uniform(3, 5))

        if "login" in page.url or "i/flow" in page.url:
            logger.info("Not logged in, starting login flow...")
            success = await _login(page)
            if not success:
                logger.error("Login failed")
                await browser.close()
                return []
            await page.goto("https://x.com/home", wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(3, 5))

        logger.info("On home timeline, starting collection...")

        all_posts: list[dict] = []
        scroll_count = 0
        max_scrolls = 20

        while len(all_posts) < max_posts and scroll_count < max_scrolls:
            # Wait for tweets to load
            try:
                await page.wait_for_selector('article[data-testid="tweet"]', timeout=10000)
            except Exception:
                logger.warning("No tweets found on scroll %d", scroll_count)
                break

            batch = await _extract_posts(page)
            new_count = 0
            existing_ids = {p["id"] for p in all_posts}
            for post in batch:
                if post["id"] not in existing_ids:
                    all_posts.append(post)
                    existing_ids.add(post["id"])
                    new_count += 1

            logger.info("Scroll %d: +%d posts (total: %d)", scroll_count, new_count, len(all_posts))

            if new_count == 0:
                break

            # Human-like scroll
            scroll_amount = random.randint(500, 900)
            await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            await asyncio.sleep(random.uniform(1.5, 3.0))
            scroll_count += 1

        # Save session for next run
        await context.storage_state(path=session_path)
        logger.info("Session saved to %s", session_path)

        await browser.close()

    logger.info("Collected %d posts total", len(all_posts))
    return all_posts[:max_posts]
