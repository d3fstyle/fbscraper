# Meta Ads Library Scraper

Automates reading a list of Facebook pages from MySQL and scraping each page's ads from the Meta Ads Library. Scraped ads are stored back in the database.

A Facebook account used for heavy automated traffic may get restricted. Public (logged-out) access avoids that risk but will miss ads gated to 18+.

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
playwright install chromium
```

2. Copy `.env.example` to `.env` and fill in real values (never commit `.env`).

3. Required environment variables:

| Variable | Used by |
|----------|---------|
| `DATABASE_URL` **or** `DB_USER` / `DB_PASS` / `DB_NAME` (+ optional `DB_HOST` / `DB_PORT`) | All DB scripts |
| `FB_USER`, `FB_PASS` | Playwright scrapers / `auth_test.py` |
| `EMAIL_FROM`, `EMAIL_TO`, `GMAIL_APP_PASSWORD` | Email report scripts |
| `EMAIL_BCC` | Optional CC on `sendResume.py` |
| `ADMINER_KW_URL_TEMPLATE` | Deep links in `sendNewFanPages.py` (`{kw}`) |
| `ADMINER_ADS_URL_TEMPLATE` | Deep links in `sendResume.py` (`{date}`) |

## Credential rotation checklist

Before making this repository public (or after any leak), rotate:

- [ ] Meta password for the scraper account (`FB_USER`)
- [ ] Meta password for any other test accounts previously hardcoded
- [ ] MySQL password for the scraper DB user
- [ ] Gmail app password currently in use **and** any previous app passwords that appeared in git history
- [ ] Review Adminer / DB admin access for the scraper database host

## Dependencies

- playwright==1.33.0 (this version helps avoid JavaScript heap memory overload)
- BeautifulSoup4
- Pandas
- Youtube_dl
- SQLAlchemy (mysql-connector-python==8.0.32)
