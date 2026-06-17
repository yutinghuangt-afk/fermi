import asyncio
import logging
import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from x_agent import config
from x_agent.browser import get_timeline_posts
from x_agent.agent import generate_report
from x_agent.notifier import send_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_session() -> None:
    logger.info("=== X browsing session started ===")
    try:
        posts = asyncio.run(get_timeline_posts())
        if not posts:
            logger.warning("No posts collected, skipping report")
            return

        report_html = generate_report(posts)
        send_report(report_html, post_count=len(posts))
        logger.info("=== Session complete: %d posts, report sent ===", len(posts))

    except Exception as e:
        logger.error("Session failed: %s", e, exc_info=True)


if __name__ == "__main__":
    logger.info(
        "Starting X browsing agent (schedule: every %dh, max posts: %d)",
        config.SCHEDULE_HOURS,
        config.MAX_POSTS,
    )

    # Run immediately on startup
    run_session()

    # Then schedule every N hours
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_session,
        trigger=IntervalTrigger(hours=config.SCHEDULE_HOURS),
        id="x_browse",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info("Scheduler started — next run in %dh", config.SCHEDULE_HOURS)

    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Agent stopped")
