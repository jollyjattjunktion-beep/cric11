from app.api import _event_commentary
from app.cricket_data import BallEvent

def event(**kwargs):
    defaults = dict(match_id=1, innings_number=1, over_number=12, ball_number=3,
                    runs_batter=0, runs_extras=0, wicket_kind=None)
    defaults.update(kwargs)
    return BallEvent(**defaults)

def test_original_commentary_for_six():
    line = _event_commentary(event(runs_batter=6), "Batter A", "Bowler B")
    assert "SIX" in line
    assert "Batter A" in line
    assert "Bowler B" in line

def test_original_commentary_for_wicket():
    line = _event_commentary(event(wicket_kind="caught"), "Batter A", "Bowler B")
    assert "WICKET" in line
    assert "dismissed" in line

def test_original_commentary_for_dot_ball():
    line = _event_commentary(event(), "Batter A", "Bowler B")
    assert "Dot ball" in line
