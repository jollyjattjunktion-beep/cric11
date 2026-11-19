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

## Importer and live data
The admin importer accepts a match source URL and stores an import job for processing. A URL is not itself a data licence or API. The CREX adapter is deliberately an integration boundary: connect an authorized/licensed feed or a permitted source adapter before importing scorecards, commentary, player statistics or pitch reports. No scraping bypass, fabricated data or unverified live score is included.

For production, add a durable worker (Celery/RQ/Arq), provider rate-limit handling, retries, idempotent ball-event ingestion, audit logs and monitoring. Configure refresh intervals to match the data provider's terms and limits.

## SEO
Match pages use stable slugs, unique title/description, canonical links, crawlable HTML and sitemap entries. Add Search Console and verify structured-data output before launch.

## Current stage
Foundation/MVP scaffold. Real external live-score provider credentials and authorized CREX extraction are not configured yet.
