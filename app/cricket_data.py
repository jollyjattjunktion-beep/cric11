"""Normalized cricket data tables. Imported by app.main before metadata.create_all."""
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.main import Base

class Team(Base):
    __tablename__ = "teams"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    short_name: Mapped[str | None] = mapped_column(String(20), nullable=True)
    country: Mapped[str | None] = mapped_column(String(80), nullable=True)

class Player(Base):
    __tablename__ = "players"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    provider: Mapped[str] = mapped_column(String(40), default="manual")
    provider_player_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    role: Mapped[str | None] = mapped_column(String(60), nullable=True)
    batting_style: Mapped[str | None] = mapped_column(String(80), nullable=True)
    bowling_style: Mapped[str | None] = mapped_column(String(100), nullable=True)
    __table_args__ = (UniqueConstraint("provider", "provider_player_id", name="uq_player_provider_id"),)

class MatchTeam(Base):
    __tablename__ = "match_teams"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), index=True)
    side: Mapped[str] = mapped_column(String(12))
    __table_args__ = (UniqueConstraint("match_id", "team_id", name="uq_match_team"),)

class Innings(Base):
    __tablename__ = "innings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), index=True)
    innings_number: Mapped[int] = mapped_column(Integer)
    batting_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    runs: Mapped[int] = mapped_column(Integer, default=0)
    wickets: Mapped[int] = mapped_column(Integer, default=0)
    overs: Mapped[str] = mapped_column(String(20), default="0")
    extras: Mapped[int] = mapped_column(Integer, default=0)
    declared: Mapped[bool] = mapped_column(default=False)
    __table_args__ = (UniqueConstraint("match_id", "innings_number", name="uq_match_innings"),)

class BattingScore(Base):
    __tablename__ = "batting_scores"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    innings_id: Mapped[int] = mapped_column(ForeignKey("innings.id", ondelete="CASCADE"), index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    runs: Mapped[int] = mapped_column(Integer, default=0)
    balls: Mapped[int] = mapped_column(Integer, default=0)
    fours: Mapped[int] = mapped_column(Integer, default=0)
    sixes: Mapped[int] = mapped_column(Integer, default=0)
    dismissal: Mapped[str | None] = mapped_column(Text, nullable=True)
    batting_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    __table_args__ = (UniqueConstraint("innings_id", "player_id", name="uq_batting_player_innings"),)

class BowlingFigure(Base):
    __tablename__ = "bowling_figures"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    innings_id: Mapped[int] = mapped_column(ForeignKey("innings.id", ondelete="CASCADE"), index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    overs: Mapped[str] = mapped_column(String(20), default="0")
    maidens: Mapped[int] = mapped_column(Integer, default=0)
    runs: Mapped[int] = mapped_column(Integer, default=0)
    wickets: Mapped[int] = mapped_column(Integer, default=0)
    wides: Mapped[int] = mapped_column(Integer, default=0)
    no_balls: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (UniqueConstraint("innings_id", "player_id", name="uq_bowling_player_innings"),)

class BallEvent(Base):
    __tablename__ = "ball_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), index=True)
    innings_number: Mapped[int] = mapped_column(Integer)
    over_number: Mapped[int] = mapped_column(Integer)
    ball_number: Mapped[int] = mapped_column(Integer)
    batter_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"), nullable=True)
    bowler_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"), nullable=True)
    runs_batter: Mapped[int] = mapped_column(Integer, default=0)
    runs_extras: Mapped[int] = mapped_column(Integer, default=0)
    wicket_kind: Mapped[str | None] = mapped_column(String(50), nullable=True)
    commentary: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_event_id: Mapped[str | None] = mapped_column(String(140), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    __table_args__ = (
        UniqueConstraint("match_id", "innings_number", "over_number", "ball_number", name="uq_ball_position"),
        Index("ix_ball_match_sequence", "match_id", "innings_number", "over_number", "ball_number"),
    )

class CommentaryEntry(Base):
    __tablename__ = "commentary_entries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), index=True)
    provider_entry_id: Mapped[str] = mapped_column(String(160))
    innings_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    over_label: Mapped[str | None] = mapped_column(String(24), nullable=True)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    __table_args__ = (UniqueConstraint("match_id", "provider_entry_id", name="uq_commentary_provider_entry"),)

class PitchReport(Base):
    __tablename__ = "pitch_reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), unique=True)
    report: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified: Mapped[bool] = mapped_column(default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class ProviderMatch(Base):
    __tablename__ = "provider_matches"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(40))
    provider_match_id: Mapped[str] = mapped_column(String(160))
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), unique=True)
    source_url: Mapped[str] = mapped_column(Text)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    __table_args__ = (UniqueConstraint("provider", "provider_match_id", name="uq_provider_match"),)
