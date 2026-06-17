#!/usr/bin/env python3
"""
X 滑板機器人 — 自動滑 X、截圖、AI 解讀、輸出報告
"""
import asyncio
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from x_agent import config
from x_agent.browser import close_browser, launch_browser, save_session
from x_agent.email_export import send_email_report
from x_agent.notion_export import export_to_notion
from x_agent.report import build_report, save_report
from x_agent.scraper import login, scroll_and_collect
from x_agent.vision import analyse_screenshot, summarise_tweets

app = typer.Typer(help="自動滑 X 並產生 AI 摘要報告")
console = Console()


@app.command()
def run(
    url: str = typer.Option(config.TARGET_URL, help="目標 X 頁面 URL (home / 搜尋 / 個人頁面)"),
    scrolls: int = typer.Option(config.SCROLL_COUNT, help="滾動次數"),
    max_tweets: int = typer.Option(config.MAX_TWEETS, help="最多收集幾則推文"),
    focus: str = typer.Option("", help="希望 AI 特別關注的主題（可留空）"),
    headless: bool = typer.Option(config.HEADLESS, help="是否用無頭瀏覽器"),
    vision: bool = typer.Option(True, help="是否對截圖進行視覺分析"),
    notion: bool = typer.Option(bool(config.NOTION_TOKEN), help="是否匯出至 Notion"),
    email: bool = typer.Option(bool(config.GMAIL_SENDER), help="是否寄送 Email 報告"),
    no_login: bool = typer.Option(False, help="跳過登入 (使用已存的 session)"),
):
    asyncio.run(
        _run(
            url=url,
            scrolls=scrolls,
            max_tweets=max_tweets,
            focus=focus,
            headless=headless,
            use_vision=vision,
            export_notion=notion,
            export_email=email,
            skip_login=no_login,
        )
    )


async def _run(
    url: str,
    scrolls: int,
    max_tweets: int,
    focus: str,
    headless: bool,
    use_vision: bool,
    export_notion: bool,
    export_email: bool,
    skip_login: bool,
) -> None:
    console.print(
        Panel.fit(
            "[bold cyan]X 滑板機器人[/bold cyan]\n"
            f"目標：{url}\n"
            f"滾動次數：{scrolls}  |  最大推文數：{max_tweets}\n"
            f"Headless：{headless}  |  視覺分析：{use_vision}",
            title="啟動",
        )
    )

    browser, context = await launch_browser(headless=headless)
    page = await context.new_page()

    try:
        # ── 1. Login ─────────────────────────────────────────────────────────
        if not skip_login:
            if not config.X_USERNAME or not config.X_PASSWORD:
                console.print(
                    "[red]請在 .env 設定 X_USERNAME 和 X_PASSWORD！[/red]"
                )
                return
            success = await login(page, config.X_USERNAME, config.X_PASSWORD)
            if not success:
                console.print("[red]登入失敗，請檢查帳號密碼。[/red]")
                return
            await save_session(context)
        else:
            console.print("[yellow]跳過登入，使用已存 session。[/yellow]")
            await page.goto("https://x.com/home", wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)

        # ── 2. Scroll & collect ──────────────────────────────────────────────
        tweets = await scroll_and_collect(
            page,
            target_url=url,
            scroll_count=scrolls,
            scroll_delay=config.SCROLL_DELAY,
            max_tweets=max_tweets,
            take_screenshots=use_vision,
        )

        if not tweets:
            console.print("[yellow]沒有收集到任何推文，請確認登入狀態與目標 URL。[/yellow]")
            return

        # ── 3. Vision analysis on screenshots ───────────────────────────────
        screenshot_analyses: list[str] = []
        if use_vision:
            seen_paths: set[str] = set()
            screenshot_paths = [
                t.screenshot_path
                for t in tweets
                if t.screenshot_path and t.screenshot_path not in seen_paths
                and not seen_paths.add(t.screenshot_path)  # type: ignore[func-returns-value]
            ]
            if screenshot_paths:
                console.print(
                    f"[cyan]對 {len(screenshot_paths)} 張截圖進行視覺分析…[/cyan]"
                )
                for path in screenshot_paths:
                    analysis = analyse_screenshot(path, context=f"Focus: {focus}" if focus else "")
                    screenshot_analyses.append(analysis)
                    console.print("[dim]✓ 截圖分析完成[/dim]")

        # ── 4. AI summary ────────────────────────────────────────────────────
        console.print("[cyan]AI 彙整推文摘要中…[/cyan]")
        summary = summarise_tweets(tweets, focus=focus)
        console.print("[green]摘要完成！[/green]")

        # ── 5. Build report ──────────────────────────────────────────────────
        report_md = build_report(
            tweets=tweets,
            summary=summary,
            target_url=url,
            screenshot_analyses=screenshot_analyses if screenshot_analyses else None,
        )
        report_path = save_report(report_md)
        console.print(f"[green]報告已儲存：{report_path}[/green]")

        # ── 6. Notion export ─────────────────────────────────────────────────
        if export_notion:
            title = f"X 報告 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            console.print("[cyan]匯出至 Notion…[/cyan]")
            notion_url = export_to_notion(title, report_md)
            if notion_url:
                console.print(f"[green]Notion 頁面：{notion_url}[/green]")
            else:
                console.print("[yellow]Notion 匯出失敗或未設定。[/yellow]")

        # ── 7. Email export ──────────────────────────────────────────────────
        if export_email:
            subject = f"[X 報告] {datetime.now().strftime('%Y-%m-%d %H:%M')} — {url}"
            console.print("[cyan]寄送 Email 報告…[/cyan]")
            ok = send_email_report(subject, report_md)
            if ok:
                console.print(f"[green]Email 已寄至 {config.GMAIL_RECIPIENT}[/green]")
            else:
                console.print("[yellow]Email 寄送失敗或未設定。[/yellow]")

        console.print(
            Panel.fit(
                f"[bold green]完成！[/bold green]\n"
                f"收集 {len(tweets)} 則推文\n"
                f"報告路徑：{report_path}",
                title="結果",
            )
        )

    finally:
        await close_browser(browser)


if __name__ == "__main__":
    app()
