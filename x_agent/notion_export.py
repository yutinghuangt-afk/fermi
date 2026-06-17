"""Export the report to a Notion page."""
from datetime import datetime

from notion_client import Client

from .config import NOTION_DATABASE_ID, NOTION_TOKEN


def export_to_notion(title: str, markdown_content: str) -> str | None:
    """
    Creates a new page in the configured Notion database.
    Returns the page URL on success, None if Notion is not configured.
    """
    if not NOTION_TOKEN or not NOTION_DATABASE_ID:
        return None

    notion = Client(auth=NOTION_TOKEN)

    # Notion blocks — split by lines, convert basic Markdown headings
    blocks = _markdown_to_blocks(markdown_content)

    response = notion.pages.create(
        parent={"database_id": NOTION_DATABASE_ID},
        properties={
            "Name": {"title": [{"text": {"content": title}}]},
            "Date": {"date": {"start": datetime.now().isoformat()}},
        },
        children=blocks[:100],  # Notion API limit per request
    )

    page_id = response["id"]
    page_url = response.get("url", f"https://notion.so/{page_id.replace('-', '')}")

    # If content > 100 blocks, append the rest in chunks
    remaining = blocks[100:]
    while remaining:
        chunk, remaining = remaining[:100], remaining[100:]
        notion.blocks.children.append(page_id, children=chunk)

    return page_url


def _markdown_to_blocks(md: str) -> list[dict]:
    blocks = []
    for line in md.splitlines():
        if line.startswith("# "):
            blocks.append(_heading(line[2:], 1))
        elif line.startswith("## "):
            blocks.append(_heading(line[3:], 2))
        elif line.startswith("### "):
            blocks.append(_heading(line[4:], 3))
        elif line.startswith("---"):
            blocks.append({"object": "block", "type": "divider", "divider": {}})
        elif line.startswith("- "):
            blocks.append(_bullet(line[2:]))
        elif line == "":
            pass  # skip blank lines
        else:
            blocks.append(_paragraph(line))
    return blocks


def _heading(text: str, level: int) -> dict:
    kind = {1: "heading_1", 2: "heading_2", 3: "heading_3"}[level]
    return {
        "object": "block",
        "type": kind,
        kind: {"rich_text": [{"type": "text", "text": {"content": text[:2000]}}]},
    }


def _paragraph(text: str) -> dict:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": text[:2000]}}]
        },
    }


def _bullet(text: str) -> dict:
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [{"type": "text", "text": {"content": text[:2000]}}]
        },
    }
