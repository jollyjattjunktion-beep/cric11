import pytest
from app.services.crex_importer import identify_crex_url, ImportValidationError

SAMPLE_MATCH_URL = (
    "https://crex.com/cricket-live-score/"
    "pak-vs-sl-2nd-test-sri-lanka-tour-of-pakistan-2026-match-updates-13LU"
)

def test_accepts_crex_match_url():
    identity = identify_crex_url("https://crex.com/scoreboard/abc123")
    assert identity.provider == "crex"
    assert identity.source_key == "scoreboard/abc123"

def test_accepts_user_supplied_pak_vs_sl_test_match():
    identity = identify_crex_url(SAMPLE_MATCH_URL)
    assert identity.provider == "crex"
    assert identity.source_key.endswith("13LU")
    assert "pak-vs-sl-2nd-test" in identity.source_key

@pytest.mark.parametrize("url", [
    "https://example.com/match/1",
    "javascript:alert(1)",
    "not-a-url",
    "https://crex.com",
])
def test_rejects_invalid_or_non_match_urls(url):
    with pytest.raises(ImportValidationError):
        identify_crex_url(url)
