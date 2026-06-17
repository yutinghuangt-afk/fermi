import logging
from datetime import datetime

import anthropic

from x_agent import config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是用戶的 X（推特）瀏覽助理。用戶使用你來代替自己滑 X 的首頁動態，\
並希望每2小時收到一份中文摘要報告，了解他追蹤的人在說什麼、有什麼有趣的事情發生。

你的報告應該要：
- 用繁體中文撰寫
- 語氣輕鬆但有深度，像朋友幫你整理消息一樣
- 對有趣的貼文給出你的看法與分析
- 指出你觀察到的趨勢或討論熱點
- 如果有特別有意思或好笑的貼文，要特別點出來

報告格式請嚴格按照以下結構輸出（使用 HTML 標籤，因為要放進 email 裡）：

<section id="highlights">
<h2>🔥 本段最有趣的發現</h2>
<!-- 3-5 個這段時間最值得注意的事情，每點用 <p> 包起來 -->
</section>

<section id="themes">
<h2>📊 熱門主題</h2>
<!-- 2-4 個你觀察到的討論主題或趨勢，每個用 <p> 包起來，說明為什麼大家在討論這個 -->
</section>

<section id="picks">
<h2>💬 精選貼文</h2>
<!-- 5-8 則值得一看的貼文，格式如下：
<div class="post">
  <p class="meta"><strong>[作者名稱] (@handle)</strong> · <a href="貼文URL">查看原文</a></p>
  <blockquote>[貼文原文，可以縮短但保留重點]</blockquote>
  <p class="comment">你的點評：[你對這則貼文的看法或為什麼值得看]</p>
</div>
-->
</section>

<section id="commentary">
<h2>🤔 心得與觀察</h2>
<!-- 2-3 段你對這段時間 X 動態的整體觀察和心得 -->
</section>"""


def _format_posts_for_prompt(posts: list[dict]) -> str:
    lines = [f"以下是從 X 首頁動態抓取的 {len(posts)} 則貼文：\n"]
    for i, p in enumerate(posts, 1):
        lines.append(f"[{i}] {p['author']} ({p['handle']})")
        lines.append(f"時間：{p['timestamp']}")
        lines.append(f"內容：{p['text']}")
        lines.append(
            f"互動：回覆 {p['replies']} | 轉推 {p['retweets']} | 喜歡 {p['likes']}"
        )
        if p["url"]:
            lines.append(f"連結：{p['url']}")
        lines.append("")
    return "\n".join(lines)


def generate_report(posts: list[dict]) -> str:
    if not posts:
        return "<p>這段時間沒有抓取到任何貼文，可能是登入失敗或 X 載入異常。</p>"

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    user_message = _format_posts_for_prompt(posts)

    logger.info("Sending %d posts to Claude for analysis...", len(posts))
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    report_html = message.content[0].text
    logger.info("Report generated (%d chars)", len(report_html))
    return report_html
