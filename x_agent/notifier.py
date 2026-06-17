import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from x_agent import config

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_jinja = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)), autoescape=False)


def _render_email(report_html: str, post_count: int, generated_at: datetime) -> str:
    template = _jinja.get_template("report.html")
    return template.render(
        report_html=report_html,
        post_count=post_count,
        generated_at=generated_at.strftime("%Y-%m-%d %H:%M"),
    )


def _save_fallback(html: str, generated_at: datetime) -> str:
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    filename = reports_dir / f"{generated_at.strftime('%Y-%m-%d_%H-%M')}.html"
    filename.write_text(html, encoding="utf-8")
    return str(filename)


def send_report(report_html: str, post_count: int) -> None:
    now = datetime.now()
    subject = f"🤖 X 動態摘要｜{now.strftime('%Y-%m-%d %H:%M')}"
    full_html = _render_email(report_html, post_count, now)

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = config.SMTP_USERNAME
        msg["To"] = config.REPORT_EMAIL
        msg.attach(MIMEText(full_html, "html", "utf-8"))

        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
            smtp.sendmail(config.SMTP_USERNAME, config.REPORT_EMAIL, msg.as_string())

        logger.info("Report email sent to %s", config.REPORT_EMAIL)

    except Exception as e:
        logger.error("SMTP failed: %s — saving report locally", e)
        path = _save_fallback(full_html, now)
        logger.info("Report saved to %s", path)
        raise
