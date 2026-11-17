# Meta Ads Library Scraper

Python scripts that scrape ads from the [Meta Ads Library](https://www.facebook.com/ads/library/) with Playwright, store results in MySQL, and optionally email summaries.

This repo is published as a reference / archive. Credentials and private infra were removed; nothing here runs out of the box without your own config.

## What it does

- Read Facebook page IDs from MySQL and scrape their ads (`scrapAdsFromPageIds.py`, `parseAdsFromIds.py`)
- Search advertisers by keyword (`searchForAdvertisers.py`, `parseAdvertisersFromKW.py`)
- Extract keywords / landing-page params (`extractKw.py`, `methods.py`)
- Send HTML email digests (`sendNewFanPages.py`, `sendResume.py`)

Heavy automated traffic against a Facebook login can get the account restricted. Logged-out access avoids that but skips 18+ ads.

## Configuration

Secrets live in environment variables (see `.env.example`). Copy to `.env` locally if you want to experiment — do not commit real values.

Main variables: `DATABASE_URL` (or `DB_*`), `FB_USER` / `FB_PASS`, and for mail scripts `EMAIL_*`, `GMAIL_APP_PASSWORD`, `ADMINER_*_URL_TEMPLATE`.

## Dependencies

Listed in `requirements.txt`:

- playwright (project historically used 1.33.0)
- beautifulsoup4
- pandas
- youtube_dl
- mysql-connector-python
- sqlalchemy
