import os
from dotenv import load_dotenv

load_dotenv()

X_USERNAME = os.getenv("X_USERNAME", "")
X_PASSWORD = os.getenv("X_PASSWORD", "")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")

GMAIL_SENDER = os.getenv("GMAIL_SENDER", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
GMAIL_RECIPIENT = os.getenv("GMAIL_RECIPIENT", "")

HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"
SCROLL_COUNT = int(os.getenv("SCROLL_COUNT", "20"))
SCROLL_DELAY = float(os.getenv("SCROLL_DELAY", "2.0"))
MAX_TWEETS = int(os.getenv("MAX_TWEETS", "50"))
TARGET_URL = os.getenv("TARGET_URL", "https://x.com/home")
