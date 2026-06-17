"""Use Claude's vision API to interpret screenshots and summarise tweet batches."""
import base64
from pathlib import Path

import anthropic

from .config import ANTHROPIC_API_KEY
from .scraper import Tweet

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SUMMARY_MODEL = "claude-sonnet-4-6"


def _encode_image(path: str) -> str:
    return base64.standard_b64encode(Path(path).read_bytes()).decode("utf-8")


def analyse_screenshot(screenshot_path: str, context: str = "") -> str:
    """Ask Claude to describe what's on a single X timeline screenshot."""
    image_data = _encode_image(screenshot_path)
    prompt = (
        "This is a screenshot of the X (Twitter) timeline. "
        "List the tweets you can see: author, main content, and any notable engagement numbers. "
        "Be concise."
    )
    if context:
        prompt = f"{context}\n\n{prompt}"

    response = client.messages.create(
        model=SUMMARY_MODEL,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_data,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )
    return response.content[0].text


def summarise_tweets(tweets: list[Tweet], focus: str = "") -> str:
    """Ask Claude to produce an editorial summary of all collected tweets."""
    if not tweets:
        return "No tweets were collected."

    tweet_dump = "\n\n".join(
        f"[@{t.handle}] {t.author}  {t.timestamp}\n"
        f"{t.text}\n"
        f"♥{t.likes}  🔁{t.retweets}  💬{t.replies}\n"
        f"{t.url}"
        for t in tweets
    )

    focus_clause = f"\n\nFocus especially on: {focus}" if focus else ""
    prompt = f"""You are a social media analyst. Below are {len(tweets)} tweets scraped from X.

{tweet_dump}

Please write a concise report (in Traditional Chinese — 繁體中文) that includes:
1. **熱門話題摘要** — top 3–5 trending themes or topics
2. **重點推文精選** — 5 most noteworthy tweets with a brief comment each
3. **情緒與輿論傾向** — overall sentiment (positive / negative / mixed)
4. **值得關注帳號** — accounts worth following based on this batch
{focus_clause}

Format the report in clean Markdown."""

    response = client.messages.create(
        model=SUMMARY_MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text
