import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise EnvironmentError(f"Missing required environment variable: {key}")
    return val


def _get(key: str, default: str = "") -> str:
    return os.getenv(key, default)


# X credentials
@property
def X_USERNAME(self): return _require("X_USERNAME")


class _Config:
    @property
    def X_USERNAME(self): return _require("X_USERNAME")
    @property
    def X_PASSWORD(self): return _require("X_PASSWORD")
    @property
    def X_EMAIL(self): return _get("X_EMAIL")
    @property
    def ANTHROPIC_API_KEY(self): return _require("ANTHROPIC_API_KEY")
    @property
    def SMTP_HOST(self): return _get("SMTP_HOST", "smtp.gmail.com")
    @property
    def SMTP_PORT(self): return int(_get("SMTP_PORT", "587"))
    @property
    def SMTP_USERNAME(self): return _require("SMTP_USERNAME")
    @property
    def SMTP_PASSWORD(self): return _require("SMTP_PASSWORD")
    @property
    def REPORT_EMAIL(self): return _require("REPORT_EMAIL")
    @property
    def SESSION_PATH(self): return _get("SESSION_PATH", "session.json")
    @property
    def MAX_POSTS(self): return int(_get("MAX_POSTS", "50"))
    @property
    def SCHEDULE_HOURS(self): return int(_get("SCHEDULE_HOURS", "2"))


# Module-level singleton — attributes are validated only when accessed
import sys
sys.modules[__name__] = _Config()  # type: ignore[assignment]
