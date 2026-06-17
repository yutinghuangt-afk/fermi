"""Send the report via Gmail using an App Password."""
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .config import GMAIL_APP_PASSWORD, GMAIL_RECIPIENT, GMAIL_SENDER


def send_email_report(subject: str, markdown_content: str) -> bool:
    """
    Sends the report as an HTML email via Gmail SMTP.
    Returns True on success, False if Gmail is not configured or sending fails.
    """
    if not GMAIL_SENDER or not GMAIL_APP_PASSWORD or not GMAIL_RECIPIENT:
        return False

    html_body = _markdown_to_html(markdown_content)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_SENDER
    msg["To"] = GMAIL_RECIPIENT
    msg.attach(MIMEText(markdown_content, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_SENDER, GMAIL_APP_PASSWORD)
            smtp.sendmail(GMAIL_SENDER, GMAIL_RECIPIENT, msg.as_string())
        return True
    except Exception as e:
        print(f"[email] Failed to send: {e}")
        return False


def _markdown_to_html(md: str) -> str:
    """Minimal Markdown → HTML conversion (no external dependency needed)."""
    import re

    lines = md.splitlines()
    html_lines = ["<html><body style='font-family:sans-serif;max-width:800px;margin:auto'>"]
    for line in lines:
        if line.startswith("# "):
            html_lines.append(f"<h1>{_inline(line[2:])}</h1>")
        elif line.startswith("## "):
            html_lines.append(f"<h2>{_inline(line[3:])}</h2>")
        elif line.startswith("### "):
            html_lines.append(f"<h3>{_inline(line[4:])}</h3>")
        elif line.startswith("---"):
            html_lines.append("<hr>")
        elif line.startswith("- "):
            html_lines.append(f"<li>{_inline(line[2:])}</li>")
        elif line == "":
            html_lines.append("<br>")
        else:
            html_lines.append(f"<p>{_inline(line)}</p>")
    html_lines.append("</body></html>")
    return "\n".join(html_lines)


def _inline(text: str) -> str:
    import re
    # Bold **text**
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # Italic *text*
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    # Links [label](url)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', text)
    return text
