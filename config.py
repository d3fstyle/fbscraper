"""Database and Meta credentials loaded from environment variables."""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine


def _load_dotenv(path: Path | None = None) -> None:
    """Load KEY=VALUE pairs from a local .env file without overriding existing env vars."""
    env_path = path or Path(__file__).resolve().parent / ".env"
    if not env_path.is_file():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)


def require_env(name: str) -> str:
    """Return a required environment variable or raise a clear error."""
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            "Copy .env.example to .env and fill in your values."
        )
    return value


_load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    db_user = require_env("DB_USER")
    db_pass = require_env("DB_PASS")
    db_host = os.environ.get("DB_HOST", "localhost")
    db_port = os.environ.get("DB_PORT", "3306")
    db_name = require_env("DB_NAME")
    DATABASE_URL = f"mysql+mysqlconnector://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

scraper_database = DATABASE_URL
scraperEngine = create_engine(scraper_database)

FB_USER = require_env("FB_USER")
FB_PASS = require_env("FB_PASS")

# Url arguments containing keywords
params1 = ("kw1", "kw2", "kw3", "kw4", "kw5", "kw6", "kw7", "kw8")
params2 = ("KW1", "KW2", "KW3", "KW4", "KW5", "KW6", "KW7", "KW8")
params3 = (
    "atxt",
    "q",
    "rskey",
    "s",
    "sqs",
    "ref_keyword",
    "p",
    "forcekeyA",
    "forcekeyB",
    "forcekeyC",
    "forcekeyD",
    "forcekeyE",
    "forcekeyF",
    "compkey",
)
params4 = ("aff_sub", "aff_sub2", "aff_sub3")

paramsOfInterest = {
    "sedo": params1,
    "iac": params2,
    "others": params3,
    "da": params4,
    "all": params1 + params2 + params3 + params4,
}
param2Remove = ["fbclid", "h", "sub_id", "sub_id2"]
