# PreetSports Cricket Platform

An original, mobile-first cricket scores and match-centre platform.

## Stack
- FastAPI + server-rendered Jinja HTML
- SQLAlchemy 2.x (PostgreSQL in production; SQLite for local development)
- Responsive CSS, lightweight JavaScript
- SEO-friendly match pages, canonical URLs and XML sitemap
- Admin match creation and source-URL import queue

## Run locally
1. Python 3.11+
2. `python -m venv .venv`
3. Activate the environment
4. `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and set `ADMIN_PASSWORD`
6. `uvicorn app.main:app --reload`
7. Open http://127.0.0.1:8000

The app uses SQLite by default. Set `DATABASE_URL` to a PostgreSQL SQLAlchemy URL for deployment.

## Admin
Open `/admin`. Configure a strong `ADMIN_PASSWORD` and a long random `SECRET_KEY` before deployment. Do not expose the app publicly with the example credentials.

## Cricket database and importer
The normalized schema in `app/cricket_data.py` includes teams, players, match-team links, innings, batting scores, bowling figures, ball events, commentary, pitch reports and provider-match identity. SQLAlchemy creates these tables alongside the base match/job tables at startup.

`app/services/crex_importer.py` provides strict CREX URL validation, source identity extraction, and an idempotent ingestion function for normalized provider payloads. Duplicate protection covers provider matches, innings, batting/bowling rows, ball positions and commentary entries.

**CREX page extraction is not connected yet.** A match URL is not itself a data licence or API. The adapter deliberately refuses to pretend extraction is active. Connect an authorized feed or implement a permitted provider adapter before importing real match data. No scraping bypass, fabricated score or unverified pitch report is included.

The normalized ingestion payload requires `title`, `team1` and `team2`. Optional data includes `provider_match_id`, `status`, `venue`, `match_date`, `innings`, `balls`, `commentary` and `pitch_report`.

Run tests with `pip install -r requirements-dev.txt` followed by `pytest`.


### CREX permissions and source rights
CREX's published Terms of Use state that platform materials are protected, prohibit copying/reproducing/distributing materials without prior written permission, and grant users a limited personal, non-commercial access licence. The terms also prohibit scraping or extracting personal data. Do not build a commercial automated content-copying pipeline from CREX without written authorization and any required data licence. Prefer a licensed cricket-data API/feed for production scorecards, ball events and commentary. See https://crex.com/terms-and-conditions.

## Production next steps
Add a durable background worker, provider rate-limit handling, retries, database migrations, audit logs and monitoring. Configure refresh intervals to match the data provider's terms and limits. Live synchronization is not enabled.

## SEO
Match pages use stable slugs, unique title/description, canonical links, crawlable HTML and sitemap entries. Add Search Console and verify structured-data output before launch.

## Current stage
Database schema and normalized ingestion pipeline scaffold are on the `feature/cricket-database-importer` branch. Real CREX extraction and live feed credentials are not configured.
