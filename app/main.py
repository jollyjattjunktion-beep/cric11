import os
import re
import secrets
from datetime import datetime, timezone
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from itsdangerous import URLSafeSerializer, BadSignature
from sqlalchemy import create_engine, String, Integer, DateTime, Text, ForeignKey, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session, relationship

load_dotenv()
APP_NAME = os.getenv("APP_NAME", "PreetSports")
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-this-before-deploy")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./preetsports.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
serializer = URLSafeSerializer(SECRET_KEY, salt="preetsports-admin")

class Base(DeclarativeBase):
    pass

class Match(Base):
    __tablename__ = "matches"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(220), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(220), index=True)
    team1: Mapped[str] = mapped_column(String(100))
    team2: Mapped[str] = mapped_column(String(100))
    score1: Mapped[str] = mapped_column(String(80), default="Yet to bat")
    score2: Mapped[str] = mapped_column(String(80), default="Yet to bat")
    status: Mapped[str] = mapped_column(String(40), default="Upcoming", index=True)
    venue: Mapped[str] = mapped_column(String(180), default="Venue to be confirmed")
    match_date: Mapped[str] = mapped_column(String(80), default="Date to be confirmed")
    description: Mapped[str] = mapped_column(Text, default="")
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

class ImportJob(Base):
    __tablename__ = "import_jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_url: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(40), default="url-import")
    status: Mapped[str] = mapped_column(String(30), default="queued")
    message: Mapped[str] = mapped_column(Text, default="Awaiting an authorized provider adapter")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

Base.metadata.create_all(engine)
app = FastAPI(title=APP_NAME)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return value[:180] or secrets.token_hex(5)

def is_admin(request: Request) -> bool:
    token = request.cookies.get("ps_admin")
    if not token:
        return False
    try:
        return serializer.loads(token).get("user") == ADMIN_USERNAME
    except (BadSignature, AttributeError):
        return False

def require_admin(request: Request):
    if not is_admin(request):
        raise HTTPException(status_code=401, detail="Admin login required")

def render(request: Request, template: str, **context):
    return templates.TemplateResponse(request=request, name=template, context={
        "app_name": APP_NAME, "base_url": BASE_URL, **context
    })

@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(db_session)):
    matches = db.scalars(select(Match).order_by(Match.created_at.desc()).limit(30)).all()
    return render(request, "home.html", matches=matches, page_title=f"{APP_NAME} - Live Cricket Scores",
                  meta_description="Follow cricket match updates, fixtures, scorecards and match centres on PreetSports.")

@app.get("/match/{slug}", response_class=HTMLResponse)
def match_page(slug: str, request: Request, db: Session = Depends(db_session)):
    match = db.scalar(select(Match).where(Match.slug == slug))
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    title = f"{match.team1} vs {match.team2} - {match.status} | {APP_NAME}"
    desc = (match.description or f"Follow {match.team1} vs {match.team2}, live score, match details and updates.").strip()[:300]
    return render(request, "match.html", match=match, page_title=title, meta_description=desc)

@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request, db: Session = Depends(db_session)):
    if not is_admin(request):
        return render(request, "login.html", page_title="Admin Login", meta_description="PreetSports administration")
    matches = db.scalars(select(Match).order_by(Match.created_at.desc()).limit(100)).all()
    jobs = db.scalars(select(ImportJob).order_by(ImportJob.created_at.desc()).limit(30)).all()
    return render(request, "admin.html", matches=matches, jobs=jobs, page_title="Admin Dashboard",
                  meta_description="Manage PreetSports matches and import jobs.")

@app.post("/admin/login")
def admin_login(username: str = Form(...), password: str = Form(...)):
    if not secrets.compare_digest(username, ADMIN_USERNAME) or not secrets.compare_digest(password, ADMIN_PASSWORD):
        return RedirectResponse("/admin?error=1", status_code=303)
    response = RedirectResponse("/admin", status_code=303)
    response.set_cookie("ps_admin", serializer.dumps({"user": username}), httponly=True, secure=BASE_URL.startswith("https://"), samesite="lax", max_age=8*60*60)
    return response

@app.post("/admin/logout")
def admin_logout():
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("ps_admin")
    return response

@app.post("/admin/matches")
def create_match(request: Request, title: str = Form(...), team1: str = Form(...), team2: str = Form(...),
                 status: str = Form("Upcoming"), venue: str = Form("Venue to be confirmed"),
                 match_date: str = Form("Date to be confirmed"), description: str = Form(""),
                 db: Session = Depends(db_session)):
    require_admin(request)
    slug = slugify(title)
    if db.scalar(select(Match).where(Match.slug == slug)):
        slug = f"{slug}-{secrets.token_hex(3)}"
    db.add(Match(slug=slug, title=title.strip(), team1=team1.strip(), team2=team2.strip(),
                 status=status, venue=venue.strip(), match_date=match_date.strip(), description=description.strip()))
    db.commit()
    return RedirectResponse("/admin", status_code=303)

@app.post("/admin/import")
def queue_import(request: Request, source_url: str = Form(...), db: Session = Depends(db_session)):
    require_admin(request)
    parsed = urlparse(source_url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Enter a valid http(s) match URL")
    host = (parsed.hostname or "").lower()
    provider = "crex" if host.endswith("crex.com") else "external-url"
    db.add(ImportJob(source_url=source_url.strip(), provider=provider,
                     message="Queued. Connect a permitted provider adapter to extract match data."))
    db.commit()
    return RedirectResponse("/admin", status_code=303)

@app.get("/sitemap.xml")
def sitemap(db: Session = Depends(db_session)):
    matches = db.scalars(select(Match).order_by(Match.id)).all()
    urls = [f"<url><loc>{BASE_URL}/</loc></url>"]
    urls += [f"<url><loc>{BASE_URL}/match/{m.slug}</loc><lastmod>{m.created_at.date().isoformat()}</lastmod></url>" for m in matches]
    xml = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + "".join(urls) + "</urlset>"
    return Response(content=xml, media_type="application/xml")

@app.get("/health")
def health():
    return {"status": "ok", "app": APP_NAME}
