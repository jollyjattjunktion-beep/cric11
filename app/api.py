"""Public, read-only PreetSports REST API v1."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.main import db_session, Match
from app.cricket_data import (
    Innings, BattingScore, BowlingFigure, Player, BallEvent, CommentaryEntry,
    PitchReport, MatchTeam, Team,
)

router = APIRouter(prefix="/api/v1", tags=["PreetSports API"])

def _match_or_404(db: Session, slug: str) -> Match:
    match = db.scalar(select(Match).where(Match.slug == slug))
    if match is None:
        raise HTTPException(status_code=404, detail="Match not found")
    return match

def _player_name(db: Session, player_id: int | None) -> str | None:
    if player_id is None:
        return None
    player = db.get(Player, player_id)
    return player.name if player else None

def _event_commentary(event: BallEvent, batter: str | None, bowler: str | None) -> str:
    """Create original short copy from score facts, never from source commentary text."""
    over = f"{event.over_number}.{event.ball_number}"
    who = batter or "The batter"
    against = f" against {bowler}" if bowler else ""
    total = event.runs_batter + event.runs_extras
    if event.wicket_kind:
        return f"WICKET at {over}! {who} is dismissed{against}. The batting side loses a wicket."
    if event.runs_batter == 6:
        return f"SIX at {over}! {who} clears the boundary{against}. Six runs from the delivery."
    if event.runs_batter == 4:
        return f"FOUR at {over}! {who} finds the boundary{against}. Four runs added."
    if total == 0:
        return f"Dot ball at {over}. {who} is kept scoreless{against}."
    if total == 1:
        return f"One run at {over}. {who} rotates the strike{against}."
    if total == 2:
        return f"Two runs at {over}. {who} comes back for a second{against}."
    return f"{total} runs from the delivery at {over}. {who} adds to the total{against}."

@router.get("/health")
def api_health():
    return {"api": "PreetSports", "version": "v1", "status": "ok"}

@router.get("/matches")
def list_matches(status: str | None = None, limit: int = Query(30, ge=1, le=100),
                 offset: int = Query(0, ge=0), db: Session = Depends(db_session)):
    stmt = select(Match).order_by(Match.created_at.desc())
    if status:
        stmt = stmt.where(Match.status.ilike(status))
    rows = db.scalars(stmt.offset(offset).limit(limit)).all()
    return {"data": [{
        "id": m.id, "slug": m.slug, "title": m.title, "team1": m.team1,
        "team2": m.team2, "score1": m.score1, "score2": m.score2,
        "status": m.status, "venue": m.venue, "match_date": m.match_date,
        "url": f"/match/{m.slug}"
    } for m in rows], "limit": limit, "offset": offset}

@router.get("/matches/{slug}")
def match_details(slug: str, db: Session = Depends(db_session)):
    m = _match_or_404(db, slug)
    pitch = db.scalar(select(PitchReport).where(PitchReport.match_id == m.id))
    return {"data": {
        "id": m.id, "slug": m.slug, "title": m.title, "team1": m.team1,
        "team2": m.team2, "score1": m.score1, "score2": m.score2,
        "status": m.status, "venue": m.venue, "match_date": m.match_date,
        "description": m.description,
        "pitch_report": {"text": pitch.report, "verified": pitch.verified}
            if pitch else None
    }}

@router.get("/matches/{slug}/innings")
def match_innings(slug: str, db: Session = Depends(db_session)):
    m = _match_or_404(db, slug)
    rows = db.scalars(select(Innings).where(Innings.match_id == m.id)
                      .order_by(Innings.innings_number)).all()
    return {"data": [{
        "innings": x.innings_number,
        "batting_team": db.get(Team, x.batting_team_id).name if x.batting_team_id and db.get(Team, x.batting_team_id) else None,
        "runs": x.runs, "wickets": x.wickets, "overs": x.overs,
        "extras": x.extras, "declared": x.declared
    } for x in rows]}

@router.get("/matches/{slug}/scorecard")
def match_scorecard(slug: str, db: Session = Depends(db_session)):
    m = _match_or_404(db, slug)
    innings_rows = db.scalars(select(Innings).where(Innings.match_id == m.id)
                              .order_by(Innings.innings_number)).all()
    result = []
    for inn in innings_rows:
        batting = db.scalars(select(BattingScore).where(BattingScore.innings_id == inn.id)
                             .order_by(BattingScore.batting_position)).all()
        bowling = db.scalars(select(BowlingFigure).where(BowlingFigure.innings_id == inn.id)).all()
        result.append({
            "innings": inn.innings_number, "runs": inn.runs, "wickets": inn.wickets,
            "overs": inn.overs,
            "batting": [{"player": _player_name(db, x.player_id), "runs": x.runs,
                         "balls": x.balls, "fours": x.fours, "sixes": x.sixes,
                         "dismissal": x.dismissal, "position": x.batting_position} for x in batting],
            "bowling": [{"player": _player_name(db, x.player_id), "overs": x.overs,
                         "maidens": x.maidens, "runs": x.runs, "wickets": x.wickets,
                         "wides": x.wides, "no_balls": x.no_balls} for x in bowling]
        })
    return {"data": result}

@router.get("/matches/{slug}/commentary")
def match_commentary(slug: str, limit: int = Query(100, ge=1, le=500),
                     db: Session = Depends(db_session)):
    """Return newly authored event-based English copy, not copied provider prose."""
    m = _match_or_404(db, slug)
    rows = db.scalars(select(BallEvent).where(BallEvent.match_id == m.id).order_by(
        BallEvent.innings_number.desc(), BallEvent.over_number.desc(), BallEvent.ball_number.desc()
    ).limit(limit)).all()
    rows.reverse()
    return {"data": [{
        "id": f"{x.innings_number}-{x.over_number}-{x.ball_number}",
        "innings": x.innings_number, "over": f"{x.over_number}.{x.ball_number}",
        "text": _event_commentary(x, _player_name(db, x.batter_id), _player_name(db, x.bowler_id)),
        "kind": "original-event-based"
    } for x in rows]}
