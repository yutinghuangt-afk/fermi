"""Build and save the final Markdown report."""
from datetime import datetime
from pathlib import Path

from .scraper import Tweet

REPORTS_DIR = Path(__file__).parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)


def build_report(
    tweets: list[Tweet],
    summary: str,
    target_url: str,
    screenshot_analyses: list[str] | None = None,
) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"# X 滑板機器人報告",
        f"",
        f"**來源：** {target_url}  ",
        f"**產生時間：** {now}  ",
        f"**收集推文數：** {len(tweets)}",
        f"",
        f"---",
        f"",
        f"## AI 分析摘要",
        f"",
        summary,
        f"",
    ]

    if screenshot_analyses:
        lines += [
            "---",
            "",
            "## 截圖視覺分析",
            "",
        ]
        for i, analysis in enumerate(screenshot_analyses, 1):
            lines += [f"### 截圖 {i}", "", analysis, ""]

    lines += [
        "---",
        "",
        "## 原始推文清單",
        "",
    ]
    for i, t in enumerate(tweets, 1):
        lines += [
            f"### {i}. @{t.handle} — {t.author}",
            f"**時間：** {t.timestamp}  ",
            f"**互動：** ♥{t.likes}  🔁{t.retweets}  💬{t.replies}",
            f"",
            t.text,
            f"",
            f"[查看推文]({t.url})",
            f"",
        ]

    return "\n".join(lines)


def save_report(content: str, prefix: str = "x_report") -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = REPORTS_DIR / f"{prefix}_{ts}.md"
    path.write_text(content, encoding="utf-8")
    return path
