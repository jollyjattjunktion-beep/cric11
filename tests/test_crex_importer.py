import pytest
from app.services.crex_importer import identify_crex_url, ImportValidationError

def test_accepts_crex_match_url():
    identity = identify_crex_url("https://crex.com/scoreboard/abc123")
    assert identity.provider == "crex"
    assert identity.source_key == "scoreboard/abc123"

@pytest.mark.parametrize("url", [
    "https://example.com/match/1",
    "javascript:alert(1)",
    "not-a-url",
    "https://crex.com",
])
def test_rejects_invalid_or_non_match_urls(url):
    with pytest.raises(ImportValidationError):
        identify_crex_url(url)
