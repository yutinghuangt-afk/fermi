"""X (Twitter) login, scrolling, and tweet extraction via Playwright."""
import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from playwright.async_api import Page
from rich.console import Console

console = Console()

SCREENSHOTS_DIR = Path(__file__).parent.parent / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)


@dataclass
class Tweet:
    author: str
    handle: str
    timestamp: str
    text: str
    likes: str
    retweets: str
    replies: str
    url: str
    screenshot_path: str = ""


async def login(page: Page, username: str, password: str) -> bool:
    """Log into X. Returns True on success."""
    console.print("[cyan]Navigating to X login…[/cyan]")
    await page.goto("https://x.com/login", wait_until="domcontentloaded")
    await page.wait_for_timeout(2000)

    # Check if already logged in
    if "home" in page.url or "/home" in page.url:
        console.print("[green]Already logged in (session restored).[/green]")
        return True

    # Enter username / email
    username_input = page.locator('input[autocomplete="username"]')
    await username_input.wait_for(timeout=15000)
    await username_input.fill(username)
    await page.keyboard.press("Enter")
    await page.wait_for_timeout(1500)

    # X sometimes asks for phone/username confirmation step
    unusual_activity = page.locator('input[data-testid="ocfEnterTextTextInput"]')
    if await unusual_activity.is_visible():
        console.print("[yellow]X is asking for username confirmation…[/yellow]")
        await unusual_activity.fill(username)
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(1500)

    # Enter password
    password_input = page.locator('input[name="password"]')
    await password_input.wait_for(timeout=10000)
    await password_input.fill(password)
    await page.keyboard.press("Enter")
    await page.wait_for_timeout(3000)

    # Handle 2FA prompt (TOTP code input)
    totp_input = page.locator('input[data-testid="ocfEnterTextTextInput"]')
    if await totp_input.is_visible():
        code = console.input(
            "[bold yellow]2FA code required — enter your TOTP code: [/bold yellow]"
        )
        await totp_input.fill(code.strip())
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(3000)

    if "home" in page.url or page.url.startswith("https://x.com/home"):
        console.print("[green]Login successful![/green]")
        return True

    # Wait a bit more for redirect
    try:
        await page.wait_for_url("**/home", timeout=10000)
        console.print("[green]Login successful![/green]")
        return True
    except Exception:
        console.print(f"[red]Login may have failed. Current URL: {page.url}[/red]")
        return False


async def _extract_tweets(page: Page) -> list[Tweet]:
    """Extract tweet data from the currently visible DOM."""
    tweets: list[Tweet] = []
    articles = await page.query_selector_all('article[data-testid="tweet"]')

    for article in articles:
        try:
            # Author name
            author_el = await article.query_selector('[data-testid="User-Name"] span')
            author = await author_el.inner_text() if author_el else ""

            # Handle (@username)
            handle_els = await article.query_selector_all(
                '[data-testid="User-Name"] a[href*="/"]'
            )
            handle = ""
            for el in handle_els:
                href = await el.get_attribute("href") or ""
                if href.startswith("/") and "/" not in href[1:]:
                    handle = href.lstrip("/")
                    break

            # Timestamp
            time_el = await article.query_selector("time")
            timestamp = await time_el.get_attribute("datetime") if time_el else ""

            # Tweet text
            text_el = await article.query_selector('[data-testid="tweetText"]')
            text = await text_el.inner_text() if text_el else ""

            # Engagement stats
            async def stat(testid: str) -> str:
                el = await article.query_selector(f'[data-testid="{testid}"]')
                return await el.inner_text() if el else "0"

            likes = await stat("like")
            retweets = await stat("retweet")
            replies = await stat("reply")

            # Tweet URL
            link_el = await article.query_selector("a[href*='/status/']")
            href = await link_el.get_attribute("href") if link_el else ""
            tweet_url = f"https://x.com{href}" if href else ""

            if text:  # skip ads / empty placeholders
                tweets.append(
                    Tweet(
                        author=author,
                        handle=handle,
                        timestamp=timestamp,
                        text=text,
                        likes=likes,
                        retweets=retweets,
                        replies=replies,
                        url=tweet_url,
                    )
                )
        except Exception:
            continue

    return tweets


async def scroll_and_collect(
    page: Page,
    target_url: str,
    scroll_count: int = 20,
    scroll_delay: float = 2.0,
    max_tweets: int = 50,
    take_screenshots: bool = True,
) -> list[Tweet]:
    """Navigate to target_url, scroll, collect tweets, and take screenshots."""
    console.print(f"[cyan]Navigating to {target_url}…[/cyan]")
    await page.goto(target_url, wait_until="domcontentloaded")
    await page.wait_for_timeout(3000)

    seen_urls: set[str] = set()
    all_tweets: list[Tweet] = []
    screenshot_index = 0

    for i in range(scroll_count):
        if len(all_tweets) >= max_tweets:
            break

        # Take a screenshot every 5 scrolls (or first scroll)
        screenshot_path = ""
        if take_screenshots and (i == 0 or (i + 1) % 5 == 0):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = str(
                SCREENSHOTS_DIR / f"scroll_{screenshot_index:03d}_{ts}.png"
            )
            await page.screenshot(path=screenshot_path, full_page=False)
            console.print(f"[dim]Screenshot saved: {screenshot_path}[/dim]")
            screenshot_index += 1

        batch = await _extract_tweets(page)
        new_count = 0
        for t in batch:
            if t.url not in seen_urls and t.text:
                seen_urls.add(t.url)
                if screenshot_path and not t.screenshot_path:
                    t.screenshot_path = screenshot_path
                all_tweets.append(t)
                new_count += 1

        console.print(
            f"[dim]Scroll {i+1}/{scroll_count} — "
            f"+{new_count} new tweets (total: {len(all_tweets)})[/dim]"
        )

        await page.evaluate("window.scrollBy(0, window.innerHeight * 1.5)")
        await page.wait_for_timeout(int(scroll_delay * 1000))

    console.print(f"[green]Collected {len(all_tweets)} unique tweets.[/green]")
    return all_tweets[:max_tweets]
