"""Provider-neutral ingestion pipeline for authorized cricket data adapters.

This module intentionally does not scrape CREX pages or bypass access controls.
A permitted provider adapter must return the normalized payload documented below.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.main import Match
from app.cricket_data import (
    Team, Player, MatchTeam, Innings, BattingScore, BowlingFigure, BallEvent,
    CommentaryEntry, PitchReport, ProviderMatch,
)

class ImportValidationError(ValueError):
    pass

@dataclass(frozen=True)
class SourceIdentity:
    provider: str
    source_url: str
    source_key: str

def identify_crex_url(url: str) -> SourceIdentity:
    parsed = urlparse((url or "").strip())
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or not host:
        raise ImportValidationError("A valid http(s) match URL is required.")
    if host != "crex.com" and not host.endswith(".crex.com"):
        raise ImportValidationError("This importer accepts CREX URLs only.")
    path = "/".join(part for part in parsed.path.split("/") if part)
    if not path:
        raise ImportValidationError("The URL does not contain a match identifier.")
    return SourceIdentity("crex", parsed.geturl(), path[-160:])

def _team(db: Session, name: str) -> Team:
    name = name.strip()
    if not name:
        raise ImportValidationError("Team name cannot be empty.")
    obj = db.scalar(select(Team).where(Team.name == name))
    if obj is None:
        obj = Team(name=name)
        db.add(obj)
        db.flush()
    return obj

def _player(db: Session, data: dict) -> Player:
    name = str(data.get("name", "")).strip()
    if not name:
        raise ImportValidationError("Player name cannot be empty.")
    provider = str(data.get("provider") or "crex")
    provider_id = str(data["provider_id"]) if data.get("provider_id") else None
    obj = None
    if provider_id:
        obj = db.scalar(select(Player).where(
            Player.provider == provider, Player.provider_player_id == provider_id
        ))
    else:
        obj = db.scalar(select(Player).where(Player.provider == provider, Player.name == name))
    if obj is None:
        obj = Player(name=name, provider=provider, provider_player_id=provider_id)
        db.add(obj)
    obj.name = name
    obj.role = data.get("role")
    obj.batting_style = data.get("batting_style")
    obj.bowling_style = data.get("bowling_style")
    db.flush()
    return obj

def ingest_match_payload(db: Session, identity: SourceIdentity, payload: dict) -> Match:
    """Idempotently ingest a normalized provider payload in the caller's transaction.

    Required: title, team1, team2. Optional: slug, status, venue, match_date,
    description, provider_match_id, innings[], commentary[], pitch_report.
    """
    title = str(payload.get("title", "")).strip()
    team1_name = str(payload.get("team1", "")).strip()
    team2_name = str(payload.get("team2", "")).strip()
    if not all((title, team1_name, team2_name)):
        raise ImportValidationError("Payload must include title, team1 and team2.")

    provider_key = str(payload.get("provider_match_id") or identity.source_key)
    link = db.scalar(select(ProviderMatch).where(
        ProviderMatch.provider == identity.provider,
        ProviderMatch.provider_match_id == provider_key
    ))
    match = db.get(Match, link.match_id) if link else None
    if match is None:
        slug = str(payload.get("slug") or title.lower().replace(" ", "-"))[:180]
        existing = db.scalar(select(Match).where(Match.slug == slug))
        if existing:
            slug = f"{slug}-{identity.provider}-{abs(hash(provider_key)) % 1000000}"
        match = Match(slug=slug, title=title, team1=team1_name, team2=team2_name)
        db.add(match)
        db.flush()
        db.add(ProviderMatch(provider=identity.provider, provider_match_id=provider_key,
                             match_id=match.id, source_url=identity.source_url))
    else:
        match.title = title
        match.team1 = team1_name
        match.team2 = team2_name
        link.source_url = identity.source_url
        link.last_synced_at = datetime.now(timezone.utc)

    match.status = str(payload.get("status") or match.status)
    match.venue = str(payload.get("venue") or match.venue)
    match.match_date = str(payload.get("match_date") or match.match_date)
    match.description = str(payload.get("description") or match.description)

    teams = {team1_name: _team(db, team1_name), team2_name: _team(db, team2_name)}
    for side, name in (("team1", team1_name), ("team2", team2_name)):
        assoc = db.scalar(select(MatchTeam).where(
            MatchTeam.match_id == match.id, MatchTeam.side == side
        ))
        if assoc is None:
            db.add(MatchTeam(match_id=match.id, team_id=teams[name].id, side=side))
        else:
            assoc.team_id = teams[name].id

    for item in payload.get("innings", []):
        number = int(item["number"])
        innings = db.scalar(select(Innings).where(
            Innings.match_id == match.id, Innings.innings_number == number
        ))
        batting_team = teams.get(item.get("batting_team"))
        if innings is None:
            innings = Innings(match_id=match.id, innings_number=number)
            db.add(innings)
        innings.batting_team_id = batting_team.id if batting_team else None
        innings.runs = int(item.get("runs", 0))
        innings.wickets = int(item.get("wickets", 0))
        innings.overs = str(item.get("overs", "0"))
        innings.extras = int(item.get("extras", 0))
        db.flush()
        for row in item.get("batting", []):
            player = _player(db, row)
            score = db.scalar(select(BattingScore).where(
                BattingScore.innings_id == innings.id, BattingScore.player_id == player.id
            ))
            if score is None:
                score = BattingScore(innings_id=innings.id, player_id=player.id)
                db.add(score)
            for field in ("runs", "balls", "fours", "sixes"):
                setattr(score, field, int(row.get(field, 0)))
            score.dismissal = row.get("dismissal")
            score.batting_position = row.get("position")
        for row in item.get("bowling", []):
            player = _player(db, row)
            figure = db.scalar(select(BowlingFigure).where(
                BowlingFigure.innings_id == innings.id, BowlingFigure.player_id == player.id
            ))
            if figure is None:
                figure = BowlingFigure(innings_id=innings.id, player_id=player.id)
                db.add(figure)
            for field in ("maidens", "runs", "wickets", "wides", "no_balls"):
                setattr(figure, field, int(row.get(field, 0)))
            figure.overs = str(row.get("overs", "0"))

    for event in payload.get("balls", []):
        exists = db.scalar(select(BallEvent).where(
            BallEvent.match_id == match.id,
            BallEvent.innings_number == int(event["innings"]),
            BallEvent.over_number == int(event["over"]),
            BallEvent.ball_number == int(event["ball"]),
        ))
        batter = _player(db, {"name": event["batter"], "provider": event.get("player_provider", "crex"),
                                "provider_id": event.get("batter_id")}) if event.get("batter") else None
        bowler = _player(db, {"name": event["bowler"], "provider": event.get("player_provider", "crex"),
                                "provider_id": event.get("bowler_id")}) if event.get("bowler") else None
        if exists is None:
            exists = BallEvent(
                match_id=match.id, innings_number=int(event["innings"]),
                over_number=int(event["over"]), ball_number=int(event["ball"]),
            )
            db.add(exists)
        exists.batter_id = batter.id if batter else exists.batter_id
        exists.bowler_id = bowler.id if bowler else exists.bowler_id
        exists.runs_batter = int(event.get("runs_batter", 0))
        exists.runs_extras = int(event.get("runs_extras", 0))
        exists.wicket_kind = event.get("wicket_kind")
        exists.source_event_id = event.get("source_event_id")
        # Provider prose is intentionally not used by the public original-commentary API.

    for entry in payload.get("commentary", []):
        entry_id = str(entry.get("id", "")).strip()
        text = str(entry.get("text", "")).strip()
        if entry_id and text and db.scalar(select(CommentaryEntry).where(
            CommentaryEntry.match_id == match.id,
            CommentaryEntry.provider_entry_id == entry_id
        )) is None:
            db.add(CommentaryEntry(match_id=match.id, provider_entry_id=entry_id,
                innings_number=entry.get("innings"), over_label=entry.get("over"),
                text=text))

    pitch = str(payload.get("pitch_report") or "").strip()
    if pitch:
        report = db.scalar(select(PitchReport).where(PitchReport.match_id == match.id))
        if report is None:
            report = PitchReport(match_id=match.id, report=pitch,
                                  source_url=identity.source_url, verified=False)
            db.add(report)
        else:
            report.report = pitch
            report.source_url = identity.source_url
            report.verified = False
    db.flush()
    return match

class CrexAdapter:
    """Implement only after confirming permitted access or receiving feed credentials."""
    provider = "crex"

    def extract(self, url: str) -> dict:
        identify_crex_url(url)
        raise NotImplementedError(
            "CREX extraction is not enabled. Supply an authorized CREX/API data source "
            "or implement a permitted adapter; this module will not bypass site controls."
        )
